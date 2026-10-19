CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    llm_provider TEXT,
    guardian_reason TEXT,
    intent_source TEXT,
    prev_hash TEXT,
    row_hash TEXT,
    simulated INTEGER DEFAULT 0,
    validation_id TEXT,
    command_hash TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    hash_version INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_timestamp ON command_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_status ON command_log(status);
CREATE INDEX IF NOT EXISTS idx_row_hash ON command_log(row_hash);
CREATE INDEX IF NOT EXISTS idx_validation_id ON command_log(validation_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outcome_once ON command_log(validation_id)
    WHERE validation_id IS NOT NULL AND status IN ('executed', 'simulated', 'execution_error');
CREATE TABLE IF NOT EXISTS task_context (
    task_id TEXT PRIMARY KEY,
    context TEXT NOT NULL,
    signature TEXT NOT NULL
);
