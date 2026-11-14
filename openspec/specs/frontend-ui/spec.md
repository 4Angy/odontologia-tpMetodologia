# frontend-ui Specification

## Purpose
Define el sistema visual global del frontend: tokens de diseño, shell de navegación, estilos base de controles y tablas, formato de montos en moneda y los requisitos mínimos de legibilidad y accesibilidad que toda ruta (autenticada, login y reserva pública) debe cumplir sin frameworks adicionales.

## Requirements

### Requirement: Tokens y hoja de estilos globales

El sistema SHALL proveer una hoja de estilos global única (`global.css`) con tokens de diseño (colores, radios, sombras, espaciado) alineados con la paleta de la agenda, importada una sola vez desde el entrypoint de la aplicación, sin depender de frameworks de CSS.

#### Scenario: Toda ruta comparte la base visual

- **WHEN** el usuario navega a cualquier ruta de la aplicación (shell autenticado, login, reserva pública)
- **THEN** los tokens globales (fuentes, colores, radios) están definidos y las pantallas sin CSS propio se ven consistentes

### Requirement: Shell de navegación consistente

El sistema SHALL renderizar el shell autenticado con header superior que incluye marca, navegación con estado activo visible y acción de logout, con layout centrado y usable en viewport móvil.

#### Scenario: Usuario autenticado navega entre secciones

- **WHEN** el usuario con sesión iniciada cambia de sección desde la navegación
- **THEN** el enlace de la sección actual se muestra como activo y el contenido principal queda dentro de un contenedor centrado con padding responsive

### Requirement: Controles y tablas legibles

El sistema SHALL aplicar estilos base accesibles a botones, inputs, selects, textareas, tablas, alerts y diálogos: estados hover/disabled, focus visible, submit como acción primaria y utilidades de solo-lector para lectores de pantalla.

#### Scenario: Usuario completa un formulario

- **WHEN** el usuario navega un formulario con teclado
- **THEN** el foco es visible en cada control y el botón de envío se distingue visualmente como acción primaria

### Requirement: Montos en moneda en caja

El sistema SHALL permitir ingresar montos de cobro en pesos con decimales y SHALL mostrar todos los montos de caja (deudas, cobros, cierre del día) formateados como moneda `es-AR`, enviando al backend siempre centavos enteros.

#### Scenario: Recepción registra un cobro de $1.500,50

- **WHEN** el usuario ingresa `1500,50` en el campo Monto y confirma
- **THEN** el sistema envía `monto_cents: 150050` al endpoint de cobros y el cobro se muestra como `$ 1.500,50`

#### Scenario: Monto inválido

- **WHEN** el usuario ingresa un texto no numérico o un valor menor o igual a cero
- **THEN** el sistema no envía la solicitud y muestra un mensaje de error en español

### Requirement: Proxy de desarrollo completo

El sistema SHALL configurar el proxy de Vite para reenviar al backend todos los prefijos de API que consume el frontend, de modo que ninguna pantalla autenticada o pública falle en desarrollo por ruta no proxied.

#### Scenario: Pantalla consume un endpoint de API en dev

- **WHEN** el frontend ejecuta `fetch` a cualquier prefijo de API definido (incluidos `/lista-espera` y `/export`)
- **THEN** la solicitud llega al backend en `localhost:8000` y no recibe la SPA ni un 404

### Requirement: Lanzamiento reproducible documentado

El sistema SHALL incluir en el README instrucciones completas para levantar el entorno local completo (variables de entorno, Docker Compose, seed demo, credenciales y frontend), verificadas contra el repositorio.

#### Scenario: Nuevo integrante levanta el proyecto

- **WHEN** una persona sigue las instrucciones del README desde un clone limpio
- **THEN** puede levantar backend + frontend y autenticarse con los usuarios demo documentados
