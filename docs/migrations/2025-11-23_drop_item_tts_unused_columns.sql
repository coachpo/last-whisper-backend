-- Migration: drop unused ItemTTS columns (audio_path, last_error, metadata)
-- Context: columns are never written/read; audio path is derived, errors tracked on tasks.
-- Tested on SQLite (data/dictation.db).

PRAGMA foreign_keys=off;
BEGIN;

-- Rebuild item_tts without unused columns
ALTER TABLE item_tts RENAME TO item_tts_old;

CREATE TABLE item_tts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    task_id VARCHAR NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

INSERT INTO item_tts (id, item_id, task_id, status, created_at, updated_at)
SELECT id, item_id, task_id, status, created_at, updated_at FROM item_tts_old;

DROP TABLE item_tts_old;

CREATE INDEX IF NOT EXISTS idx_itemtts_status ON item_tts(status);
CREATE INDEX IF NOT EXISTS idx_itemtts_item ON item_tts(item_id);

COMMIT;
PRAGMA foreign_keys=on;
