-- ============================================================
-- Child Panel migration: key-rotation webhook receiver
-- ============================================================
-- Adds the dedupe ledger used by /webhook/rotate-api-key so that
-- retries (whether from network jitter or a half-completed
-- previous run) don't double-apply.
--
-- Also adds an optional last-rotated timestamp on site_settings
-- for human audit. Both statements are idempotent — safe to re-run.
-- ============================================================

CREATE TABLE IF NOT EXISTS `api_key_rotations` (
  `rotation_id`   VARCHAR(64) NOT NULL,
  `applied_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `new_key_hint`  VARCHAR(8) DEFAULT NULL,
  PRIMARY KEY (`rotation_id`),
  KEY `idx_applied_at` (`applied_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- site_settings.api_key_rotated_at — optional, for the admin UI to show
-- "last rotated: <date>" next to the key field.
SET @_c = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME   = 'site_settings'
             AND COLUMN_NAME  = 'api_key_rotated_at');
SET @_s = IF(@_c = 0,
  'ALTER TABLE `site_settings` ADD COLUMN `api_key_rotated_at` DATETIME DEFAULT NULL',
  'SELECT 1');
PREPARE _st FROM @_s; EXECUTE _st; DEALLOCATE PREPARE _st;
