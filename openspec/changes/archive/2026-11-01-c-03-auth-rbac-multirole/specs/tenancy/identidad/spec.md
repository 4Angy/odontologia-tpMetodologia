# Spec Delta — tenancy/identidad

## ADDED Requirements

### Requirement: Gestión de usuarios del tenant restringida al dueño

El sistema SHALL permitir al usuario con rol `dueno` invitar usuarios al tenant (`POST /users/invite`: email, nombre, roles ⊆ matriz vigente) y listar los usuarios del tenant (`GET /users`), y SHALL asignar los roles indicados en la invitación. El sistema SHALL rechazar con `403` (código `RN-AU-04`) toda gestión de usuarios operada por un usuario sin rol `dueno`. Un usuario invitado SHALL ser local al tenant y SHALL poder acumular varios roles (en el borde: los tres).

#### Scenario: El dueño invita un usuario con roles acotados (funcionamiento esperado)

- **GIVEN** el dueño del tenant `A` autenticado
- **WHEN** ejecuta `POST /users/invite` con un email nuevo y el rol `recepcion`
- **THEN** se crea el usuario del tenant `A` con `password_hash` vacío (queda pendiente de definir password vía reset) y el rol `recepcion`, y el nuevo usuario aparece en `GET /users`

#### Scenario: Gestión de usuarios por un no-dueño (borde)

- **GIVEN** un usuario del tenant `A` con roles `recepcion` y `odontologo` (unión sin `dueno`)
- **WHEN** ejecuta `POST /users/invite` o `GET /users`
- **THEN** ambas operaciones responden `403` con código `RN-AU-04` y mensaje en español-AR, sin listado ni creación

#### Scenario: Rol inexistente en la invitación (borde)

- **GIVEN** el dueño del tenant `A`
- **WHEN** invita a un usuario con un rol fuera de `recepcion|odontologo|dueno`
- **THEN** la invitación es rechazada con un error de validación en español-AR y no se crea el usuario

#### Scenario: Invitación de email ya existente en el tenant (borde)

- **GIVEN** el tenant `A` ya tiene un usuario con email `duplicado@correo.com`
- **WHEN** el dueño del tenant `A` invita otro usuario con ese mismo email
- **THEN** la invitación es rechazada con un error en español-AR que indica que el email ya está registrado en el consultorio (unicidad por tenant, sin filtrar existencia en otros tenants)
