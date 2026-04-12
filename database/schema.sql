CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    llm_provider TEXT,
    guardian_reason TEXT,
    -- Senior-level feature: Forensic Chain Hashing (HMAC-SHA256)
    prev_hash TEXT,
    row_hash TEXT,
    -- Explicitly track if the command was actually executed or just simulated
    simulated INTEGER DEFAULT 0
);

CREATE INDEX idx_timestamp ON command_log(timestamp);
CREATE INDEX idx_status ON command_log(status);
CREATE INDEX idx_row_hash ON command_log(row_hash);
