#!/usr/bin/env node
/**
 * Handshake MCP explicito contra el server filesystem oficial de Anthropic.
 *
 * Existe para que la evidencia de docs/skills-mcp/evidencias/mcp-filesystem-verificacion.txt
 * sea reproducible por cualquier persona con `node`: el cliente del repo
 * (docs/skills-mcp/tools/mcp-fs.js) llama a initialize y a tools/list pero
 * NO imprime sus respuestas, por lo que no puede mostrar ni el nombre/version
 * del server ni la cantidad de herramientas.
 *
 * Habla JSON-RPC 2.0 por stdio directamente contra el entry point del server
 * (sin shim npx.cmd de Windows, que parte los argumentos si el path tiene
 * espacios).
 *
 * Uso:
 *   node mcp-handshake.js <raiz-del-proyecto>
 *
 * Salida (tres lineas estables):
 *   INIT <serverInfo.name> <serverInfo.version>
 *   <N> tools: <nombres>
 *   READ <archivo> -> <N> chars
 */
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");
const os = require("node:os");

const RAIZ = process.argv[2];
if (!RAIZ) {
  console.error("uso: node mcp-handshake.js <raiz-del-proyecto>");
  process.exit(2);
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

const proc = spawn("node", [SERVER_ENTRY, RAIZ], {
  stdio: ["pipe", "pipe", "pipe"],
});
proc.stderr.on("data", () => {}); // el banner del server va a stderr

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

function enviar(id, method, params) {
  return new Promise((resolve, reject) => {
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

(async () => {
  const init = await enviar(1, "initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "mcp-handshake-client", version: "1.0.0" },
  });
  const info = (init.result && init.result.serverInfo) || {};
  console.log(`INIT ${info.name} ${info.version}`);

  const lista = await enviar(2, "tools/list", {});
  const tools = (lista.result && lista.result.tools) || [];
  console.log(`${tools.length} tools: ${tools.map((t) => t.name).join(", ")}`);

  const archivo = "CHANGES.md";
  const ruta = `${RAIZ.replace(/\\/g, "/")}/${archivo}`;
  const respuesta = await enviar(3, "tools/call", {
    name: "read_text_file",
    arguments: { path: ruta },
  });
  if (respuesta.error) {
    console.error("READ error:", JSON.stringify(respuesta.error));
    proc.kill();
    process.exit(1);
  }
  const texto = (respuesta.result.content || [])
    .map((bloque) => bloque.text || "")
    .join("");
  console.log(`READ ${archivo} -> ${texto.length} chars`);
  console.log(`primera linea: ${texto.split(/\r?\n/)[0]}`);

  proc.kill();
  process.exit(0);
})().catch((error) => {
  console.error("fallo:", error.message);
  proc.kill();
  process.exit(1);
});
