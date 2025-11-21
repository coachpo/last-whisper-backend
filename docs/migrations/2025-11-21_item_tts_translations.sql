-- Migration: decouple TTS from items and add item-bound translations cache
-- Assumes current schema has items.tts_status and no item_tts/translations tables.
-- Tested on data/dictation.db (SQLite).

PRAGMA foreign_keys=off;
BEGIN;

-- 1) Create item_tts table
CREATE TABLE IF NOT EXISTS item_tts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    task_id VARCHAR NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    audio_path TEXT NULL,
    last_error TEXT NULL,
    metadata TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_itemtts_status ON item_tts(status);
CREATE INDEX IF NOT EXISTS idx_itemtts_item ON item_tts(item_id);

-- Backfill item_tts from existing items table
INSERT OR IGNORE INTO item_tts (item_id, task_id, status, created_at, updated_at)
SELECT id, task_id, tts_status, created_at, updated_at FROM items;

-- 2) Create translations table (item-bound translations cache)
CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    target_lang VARCHAR(10) NOT NULL,
    source_lang VARCHAR(10) NOT NULL,
    text_hash VARCHAR(32) NOT NULL,
    translated_text TEXT NULL,
    provider VARCHAR(32) NOT NULL DEFAULT 'google',
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    error TEXT NULL,
    metadata TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    last_refreshed_at DATETIME NULL,
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
    UNIQUE (item_id, target_lang)
);
CREATE INDEX IF NOT EXISTS idx_translations_item_status ON translations(item_id, status);
CREATE INDEX IF NOT EXISTS idx_translations_target ON translations(target_lang);
CREATE INDEX IF NOT EXISTS idx_translations_text_hash ON translations(text_hash);

-- 3) Rebuild items table without tts_status
ALTER TABLE items RENAME TO items_old;

CREATE TABLE items (
    id INTEGER NOT NULL, 
    locale VARCHAR(10) NOT NULL, 
    text TEXT NOT NULL, 
    difficulty INTEGER, 
    tags_json TEXT, 
    task_id VARCHAR, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(task_id) REFERENCES tasks (task_id) ON DELETE SET NULL
);

INSERT INTO items (id, locale, text, difficulty, tags_json, task_id, created_at, updated_at)
SELECT id, locale, text, difficulty, tags_json, task_id, created_at, updated_at FROM items_old;

DROP TABLE items_old;

-- Recreate indexes for items
CREATE INDEX IF NOT EXISTS ix_items_task_id ON items (task_id);
CREATE INDEX IF NOT EXISTS idx_items_created_at_asc ON items (created_at ASC);
CREATE INDEX IF NOT EXISTS idx_items_created_at_desc ON items (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_locale_difficulty ON items (locale, difficulty);
CREATE INDEX IF NOT EXISTS ix_items_locale ON items (locale);
CREATE INDEX IF NOT EXISTS ix_items_difficulty ON items (difficulty);
CREATE INDEX IF NOT EXISTS ix_items_created_at ON items (created_at);

COMMIT;
PRAGMA foreign_keys=on;
