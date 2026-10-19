# Audit database

The audit database records authorization decisions and executor reports. It is
not an approval queue: changing a row does not authorize a command, and editing
signed records breaks verification.

## Schema and storage

`database/schema.sql` is the schema source. `database/audit_logger.py` handles
migration, transactional appends and verification. The main table is
`command_log`; task context is stored separately in `task_registry`.

The Compose database lives at `state/audit/audit.db` on the host and
`/var/lib/guardian/audit.db` inside Guardian. SQLite WAL sidecars belong alongside
it. The UI has no database mount.

A validation records `approved` or `rejected`. An approved validation can later
have one terminal outcome: `simulated`, `executed` or `execution_error`. The
validation identity and command digest bind that report to the original decision.
Approval alone does not mean anything ran.

## Reading records

Use the authenticated [GET /audit API](API.md#get-audit) for the latest records
and counts. It returns at most 20 rows and keeps database access in Guardian.
Do not distribute the operator credential to readers.

Direct inspection should use a consistent backup in an authorized maintenance
process. A read-only mount of a live WAL database can fail when its sidecars are
unavailable; it is not a substitute for the API or a proper snapshot.

Do not copy old instructions that manually approved rows, deleted signed history
or shared the live database with agents. Those operations can invalidate the
chain and bypass the intended separation between clients and persisted state.

## Integrity and migration

New records use HMAC-SHA256 over their canonical metadata and predecessor.
`BEGIN IMMEDIATE` keeps concurrent writers from appending to the same predecessor.
Legacy unsigned rows remain unverifiable. A later signature can anchor their
migrated representation, but cannot prove their original authenticity.

Preserve the signing key and database together. The verifier is
`scripts/verify_logs.py`; it must receive the correct key securely and the path to
the database being inspected. Do not print either secret configuration or expanded
environment values when diagnosing a failure.

## Backup and recovery

Use SQLite's backup API for a consistent snapshot, including committed WAL data.
[Install and upgrade](INSTALL.md#existing-configuration-or-data) gives the migration
procedure and preserves the original database. Stop the old writers before an
upgrade and confirm ownership of the destination state directory.

A valid HMAC chain cannot detect deletion of a valid suffix or full rollback on
its own. That requires a trusted external checkpoint. Storage is not encrypted,
and redaction is not a guarantee that task text contains no secrets.
