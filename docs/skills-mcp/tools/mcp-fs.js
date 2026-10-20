#!/usr/bin/env node
/**
 * Cliente MCP stdio mínimo para el servidor oficial de filesystem de Anthropic.
 *
 * Existe porque la instancia del servidor que abre el cliente de OpenCode
 * queda rooteada en el workspace de la sesión, que no es el repositorio del
 * proyecto (y porque el shim `npx.cmd` de Windows parte los argumentos cuando
 * el path tiene espacios). Este script habla JSON-RPC 2.0 por stdio
 * directamente contra el entry point del server, sin shim intermedio.
 *
 * Uso:
 *   node mcp-fs.js <raiz> list_directory  '{"path":"<raiz>\\CHANGES.md"}'
 *   node mcp-fs.js <raiz> read_text_file  '{"path":"<raiz>\\CHANGES.md"}'
 *   node mcp-fs.js <raiz> search_files     '{"path":"<raiz>","pattern":"*.md"}'
 *
 * Si el tercer argumento es "-" o se omite, los argumentos JSON se leen de
 * stdin (evita el quoting hell de PowerShell al pasar argumentos a un exe
 * nativo de Windows).
 *
 * Imprime la respuesta cruda del server por stdout (con el prefijo "MCP> ").
 */
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");
const os = require("node:os");

function leerStdin() {
  return new Promise((resolve, reject) => {
    let datos = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      datos += chunk;
    });
    process.stdin.on("end", () => resolve(datos));
    process.stdin.on("error", reject);
  });
}

const SERVER_ENTRY = path.join(
  os.homedir(),
  "AppData",
  "Roaming",
  "npm",
  "node_modules",
  "@modelcontextprotocol",
  "server-filesystem",
  "dist",
  "index.js",
);

function rpc(proc) {
  let buffer = "";
  const pendientes = new Map();
  proc.stdout.on("data", (chunk) => {
    buffer += chunk.toString();
    let indice;
    while ((indice = buffer.indexOf("\n")) >= 0) {
      const linea = buffer.slice(0, indice).trim();
      buffer = buffer.slice(indice + 1);
      if (!linea) continue;
      let mensaje;
      try {
        mensaje = JSON.parse(linea);
      } catch {
        continue;
      }
      const resolver = pendientes.get(mensaje.id);
      if (resolver) {
        pendientes.delete(mensaje.id);
        resolver(mensaje);
      }
    }
  });
  return (id, method, params) =>
    new Promise((resolve, reject) => {
      pendientes.set(id, resolve);
      const mensaje = { jsonrpc: "2.0", id, method };
      if (params) mensaje.params = params;
      proc.stdin.write(JSON.stringify(mensaje) + "\n");
      setTimeout(() => {
        if (pendientes.has(id)) {
          pendientes.delete(id);
          reject(new Error(`timeout en ${method}`));
        }
      }, 30000);
    });
}

async function main() {
  const [raiz, herramienta, argsJson] = process.argv.slice(2);
  if (!raiz || !herramienta) {
    console.error("uso: node mcp-fs.js <raiz> <herramienta> [args-json]");
    process.exit(2);
  }
  const argumentosCrudos =
    argsJson && argsJson !== "-" ? argsJson : await leerStdin();
  const argumentos = argumentosCrudos.trim() ? JSON.parse(argumentosCrudos) : {};

  const proc = spawn("node", [SERVER_ENTRY, raiz], { stdio: ["pipe", "pipe", "pipe"] });
  const enviar = rpc(proc);
  proc.stderr.on("data", () => {}); // el banner del server va a stderr

  await enviar(1, "initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "mcp-fs-client", version: "1.0.0" },
  });
  await enviar(2, "tools/list", {});

  const respuesta = await enviar(3, "tools/call", {
    name: herramienta,
    arguments: argumentos,
  });

  if (respuesta.error) {
    console.error("MCP error:", JSON.stringify(respuesta.error));
    proc.kill();
    process.exit(1);
  }
  const texto = (respuesta.result?.content || [])
    .map((bloque) => bloque.text || "")
    .join("");
  console.log(texto);
  proc.kill();
  process.exit(0);
}

main().catch((error) => {
  console.error("fallo:", error.message);
  process.exit(1);
});
