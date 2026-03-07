CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    llm_provider TEXT,
    guardian_reason TEXT,
    intent_source TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON command_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_status ON command_log(status);
