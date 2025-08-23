"""SQL query constants for TTS task management."""

SQL_CREATE_TASKS_TABLE = """
                         CREATE TABLE IF NOT EXISTS tasks
                         (
                             id               INTEGER PRIMARY KEY AUTOINCREMENT,
                             task_id          TEXT UNIQUE NOT NULL,
                             original_text    TEXT        NOT NULL,
                             text_hash        TEXT        NOT NULL,
                             status           TEXT        NOT NULL DEFAULT 'pending',
                             output_file_path TEXT,
                             custom_filename  TEXT,
                             created_at       TEXT                 DEFAULT (datetime('now')),
                             submitted_at     TEXT,
                             started_at       TEXT,
                             completed_at     TEXT,
                             failed_at        TEXT,
                             error_message    TEXT,
                             file_size        INTEGER,
                             sampling_rate    INTEGER,
                             device           TEXT,
                             metadata         TEXT
                         ) \
                         """

SQL_CREATE_INDEX_TASK_ID = "CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)"
SQL_CREATE_INDEX_TEXT_HASH = "CREATE INDEX IF NOT EXISTS idx_text_hash ON tasks(text_hash)"
SQL_CREATE_INDEX_STATUS = "CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)"

SQL_INSERT_TASK = """
                  INSERT INTO tasks (task_id, original_text, text_hash, status,
                                     custom_filename, submitted_at)
                  VALUES (?, ?, ?, ?, ?, ?) \
 \
                  """

SQL_SELECT_COMPLETED_BY_HASH = """
                               SELECT *
                               FROM tasks
                               WHERE text_hash = ?
                                 AND status = 'completed'
                               ORDER BY completed_at DESC
                               LIMIT 1 \
                               """

SQL_SELECT_TASK_BY_ID = "SELECT * FROM tasks WHERE task_id = ?"

SQL_SELECT_ALL_TASKS = "SELECT * FROM tasks ORDER BY created_at DESC"

SQL_SELECT_TASKS_BY_STATUS = """
                             SELECT *
                             FROM tasks
                             WHERE status = ?
                             ORDER BY created_at DESC \
                             """

SQL_SELECT_TASKS_BY_HASH = """
                           SELECT *
                           FROM tasks
                           WHERE text_hash = ?
                           ORDER BY created_at DESC \
                           """

SQL_UPDATE_TASK_BASE = "UPDATE tasks SET {columns} WHERE task_id = ?"

SQL_STATS_STATUS_COUNTS = """
                          SELECT status, COUNT(*) as count
                          FROM tasks
                          GROUP BY status \
                          """

SQL_STATS_TOTAL_TASKS = "SELECT COUNT(*) FROM tasks"

SQL_STATS_AVG_FILE_SIZE = """
                          SELECT AVG(file_size)
                          FROM tasks
                          WHERE status = 'completed'
                            AND file_size IS NOT NULL \
                          """

SQL_STATS_DUPLICATE_HASHES = """
                             SELECT text_hash, COUNT(*) as count
                             FROM tasks
                             GROUP BY text_hash
                             HAVING COUNT(*) > 1 \
                             """

SQL_CLEANUP_FAILED_TASKS = """
                           DELETE
                           FROM tasks
                           WHERE status = 'failed'
                             AND failed_at < datetime('now', '-7 days') \
                           """

SQL_CHECK_TASK_EXISTS = "SELECT task_id FROM tasks WHERE task_id = ?"

SQL_SELECT_EXISTING_BY_HASH = """
                              SELECT *
                              FROM tasks
                              WHERE text_hash = ?
                                AND status != 'failed'
                              ORDER BY CASE status
                                           WHEN 'completed' THEN 1
                                           WHEN 'processing' THEN 2
                                           WHEN 'queued' THEN 3
                                           ELSE 4
                                           END,
                                       created_at DESC
                              LIMIT 1 \
                              """
