-- Migration: add task_kind to tasks for distinguishing regenerate requests
-- Target: SQLite (data/dictation.db)

ALTER TABLE tasks ADD COLUMN task_kind VARCHAR(16) NOT NULL DEFAULT 'generate';
CREATE INDEX IF NOT EXISTS idx_tasks_task_kind ON tasks(task_kind);
