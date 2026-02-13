CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    llm_provider TEXT,
    guardian_reason TEXT
);

CREATE INDEX idx_timestamp ON command_log(timestamp);
CREATE INDEX idx_status ON command_log(status);
