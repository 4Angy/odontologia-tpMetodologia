# Spec Delta

## MODIFIED Requirements

### Requirement: Public actions preserve appointment state rules

The system SHALL expose confirm, cancel and reschedule actions without login
only through a valid action token and MUST reuse the appointment state machine,
cancellation lead-time rule and availability validation. Public actions MUST
not permit arbitrary state updates or unauthorized overrides. The confirm action
MUST record the patient acknowledgment when the appointment is already
`confirmado`, storing the acknowledgment instant without changing `estado`; for a
`pendiente_confirmacion` appointment it MUST preserve the transition to
`confirmado`.

#### Scenario: Patient confirms a pending appointment

- **WHEN** a valid confirmation token is used for a `pendiente_confirmacion` appointment that does not require an unpaid deposit
- **THEN** the appointment transitions to `confirmado`

#### Scenario: Patient acknowledges an already confirmed appointment

- **WHEN** a valid confirmation token is used for an appointment that is already `confirmado`
- **THEN** the system records the acknowledgment instant and leaves the appointment state unchanged

#### Scenario: Repeated acknowledgment

- **WHEN** the same confirmation token is used again after the acknowledgment was recorded
- **THEN** the system responds successfully, keeps the first acknowledgment instant and creates no duplicate record

#### Scenario: Cancellation outside the allowed window

- **WHEN** a valid cancellation token is used inside the tenant's cancellation lead-time window
- **THEN** the system rejects the cancellation with `RN-AG-01` and leaves the appointment unchanged

#### Scenario: Patient reschedules to an available slot

- **WHEN** a valid reschedule token selects an available slot and the appointment is reschedulable
- **THEN** the original appointment becomes `reprogramado` and the replacement appointment remains subject to public confirmation rules

#### Scenario: Patient reschedules to an occupied slot

- **WHEN** a valid reschedule token selects a slot that is no longer available
- **THEN** the system rejects the operation, leaves the original appointment unchanged and returns available alternatives
