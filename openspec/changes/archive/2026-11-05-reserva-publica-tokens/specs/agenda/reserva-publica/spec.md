# Spec Delta

## Purpose

Permite que pacientes sin cuenta consulten disponibilidad real y gestionen sus
reservas mediante enlaces públicos seguros, sin exponer datos de otros
consultorios ni depender del horario de recepción.

## ADDED Requirements

### Requirement: Public tenant booking shows real availability

The system SHALL expose a public booking view identified by a tenant slug and
MUST return only active professionals, active services, schedules, blocks and
available slots belonging to that tenant. Availability MUST apply the service
duration, existing active appointments and the tenant booking lead time.

#### Scenario: Public visitor loads a tenant booking page

- **WHEN** a visitor requests a valid tenant slug and an availability window
- **THEN** the system returns the tenant's public booking configuration and slots ordered chronologically without requiring authentication

#### Scenario: Unknown or inactive tenant

- **WHEN** a visitor requests an unknown or unavailable tenant slug
- **THEN** the system returns a generic not-found response without revealing whether another tenant exists

#### Scenario: Slot blocked or already occupied

- **WHEN** a requested service would overlap a block or active appointment, or would not fit within the professional schedule
- **THEN** the slot is not returned and cannot be booked

### Requirement: Public reservation creates a pending appointment safely

The system SHALL allow a visitor to submit the minimum patient contact data,
selected tenant, professional, service and slot, and MUST create the
appointment as `pendiente_confirmacion` with origin `reserva_publica`.
Creation MUST be tenant-scoped, idempotent and subject to the same collision
rules as internal appointments.

#### Scenario: Successful public reservation

- **WHEN** a visitor submits valid contact data and an available slot with a new idempotency key
- **THEN** the system creates or associates the patient in the requested tenant, creates one pending appointment, and returns a public action link without exposing persistence models

#### Scenario: Equivalent retry

- **WHEN** the same tenant repeats the reservation with the same idempotency key and equivalent payload
- **THEN** the system returns the original reservation result without creating another patient, appointment or token

#### Scenario: Idempotency key reused with different payload

- **WHEN** an existing idempotency key is submitted with different reservation data
- **THEN** the system rejects the request with a conflict and leaves the original reservation unchanged

#### Scenario: Concurrent booking of one slot

- **WHEN** two visitors concurrently submit the same available slot
- **THEN** at most one reservation succeeds and the other receives a conflict with refreshed alternatives

### Requirement: Public patient data and WhatsApp consent are validated

The system SHALL validate public contact data before creating a reservation.
When WhatsApp consent is requested, the phone MUST be valid E.164 and the
consent MUST be stored explicitly; without consent the system MUST NOT enable
WhatsApp actions for that patient.

#### Scenario: WhatsApp opt-in with valid phone

- **WHEN** a visitor requests WhatsApp communication and submits an E.164 phone number
- **THEN** the reservation stores the active WhatsApp opt-in and returns the allowed action link

#### Scenario: WhatsApp opt-in without valid phone

- **WHEN** a visitor requests WhatsApp communication without a valid E.164 phone number
- **THEN** the system rejects the reservation with a traceable validation error and creates no appointment

#### Scenario: Reservation without WhatsApp opt-in

- **WHEN** a visitor does not grant WhatsApp consent
- **THEN** the reservation may be created, but no WhatsApp action or message is enabled for it

### Requirement: Public action tokens are opaque, scoped and expirable

The system SHALL issue an opaque public action token through a separate token
record linked to one appointment. The persisted record MUST contain only a
non-reversible token representation, purpose, expiry, creation metadata and
optional revocation metadata. A token MUST be single-purpose, usable only for
its linked appointment and tenant, and valid until the earlier of its expiry or
revocation.

#### Scenario: Valid token performs its permitted action

- **WHEN** a visitor submits an unexpired, unrevoked token for its linked appointment and matching action
- **THEN** the system applies the action's normal appointment transition and returns the resulting public appointment state

#### Scenario: Expired token is rejected

- **WHEN** a visitor submits a token after its configured expiry
- **THEN** the system rejects the action without revealing appointment details or changing the appointment

#### Scenario: Revoked token is rejected

- **WHEN** a visitor submits a token revoked after a phone change, replacement token or security event
- **THEN** the system rejects the action without changing the appointment

#### Scenario: Token does not cross tenants or purposes

- **WHEN** a token is presented for a different tenant, appointment or action purpose
- **THEN** the system returns a generic unauthorized response and performs no mutation

### Requirement: Public actions preserve appointment state rules

The system SHALL expose confirm, cancel and reschedule actions without login
only through a valid action token and MUST reuse the appointment state machine,
cancellation lead-time rule and availability validation. Public actions MUST
not permit arbitrary state updates or unauthorized overrides.

#### Scenario: Patient confirms a pending appointment

- **WHEN** a valid confirmation token is used for a `pendiente_confirmacion` appointment that does not require an unpaid deposit
- **THEN** the appointment transitions to `confirmado`

#### Scenario: Cancellation outside the allowed window

- **WHEN** a valid cancellation token is used inside the tenant's cancellation lead-time window
- **THEN** the system rejects the cancellation with `RN-AG-01` and leaves the appointment unchanged

#### Scenario: Patient reschedules to an available slot

- **WHEN** a valid reschedule token selects an available slot and the appointment is reschedulable
- **THEN** the original appointment becomes `reprogramado` and the replacement appointment remains subject to public confirmation rules

#### Scenario: Patient reschedules to an occupied slot

- **WHEN** a valid reschedule token selects a slot that is no longer available
- **THEN** the system rejects the operation, leaves the original appointment unchanged and returns available alternatives

### Requirement: Deposit-required reservations expose a checkout handoff

The system SHALL respect the tenant/service deposit configuration. When a
deposit is required, the public reservation MUST remain pending until an
accreditation event confirms it, and the response MUST expose a checkout
handoff for the payment integration without processing or trusting payment
status in this capability.

#### Scenario: Required deposit creates checkout handoff

- **WHEN** a visitor books a service requiring a deposit
- **THEN** the system creates a pending reservation and returns a checkout URL or an explicit payment-pending response

#### Scenario: Deposit is not accredited before timeout

- **WHEN** the configured payment timeout elapses without accreditation
- **THEN** the system releases the appointment slot, revokes its pending action tokens and records the release reason

#### Scenario: Accredited deposit confirms reservation

- **WHEN** the payment capability reports an idempotently identified accredited deposit
- **THEN** the reservation can transition to `confirmado` without requiring a second public booking

### Requirement: Public routes resist abuse and avoid information leakage

The system SHALL rate-limit public reads, booking attempts and token actions by
tenant and client characteristics, return retry information when a limit is
exceeded, and avoid returning patient, tenant-existence or appointment details
in generic public errors. Repeated failed or suspicious attempts MUST NOT
create appointments.

#### Scenario: Booking rate limit exceeded

- **WHEN** a client exceeds the configured public booking limit
- **THEN** the system returns `429` with a retry interval and creates no reservation

#### Scenario: Repeated invalid token attempts

- **WHEN** a client repeatedly submits invalid, expired or revoked tokens
- **THEN** the system throttles further attempts and returns a generic response

#### Scenario: Public request contains unknown fields

- **WHEN** a public request includes fields outside the declared contract
- **THEN** the system rejects it before any state change

### Requirement: Public reservation operations are auditable

The system SHALL record the tenant, appointment, action, result and UTC
timestamp for public reservation creation and token actions, without storing
raw tokens or unnecessary clinical data. Owners MUST be able to distinguish
successful, rejected and expired public operations in the audit trail.

#### Scenario: Successful public action is audited

- **WHEN** a public reservation or token action succeeds
- **THEN** an audit entry records the action and outcome without the raw token

#### Scenario: Rejected public action is audited

- **WHEN** a public request is rejected after rate, token or business validation
- **THEN** the system records the rejection category without exposing sensitive details to the visitor
