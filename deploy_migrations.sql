-- ============================================================
-- DiberrySMS Child Panel — Full Deployment Migration Script
-- ============================================================
-- Creates the full schema needed by the child panel from scratch,
-- applies every migration on top, and seeds the placeholder
-- site_settings row so the app can boot. Run on a fresh empty
-- database OR on an existing one — every statement uses IF NOT EXISTS,
-- INSERT IGNORE, or INFORMATION_SCHEMA guards so re-runs are no-ops.
--
-- ── Fresh-install workflow ──
--   1. mysql ... < deploy_migrations.sql   (creates schema, seeds settings)
--   2. cp config.example.json config.json  (SITE_INSTALLED=0)
--   3. Start the app. Visit /install in a browser.
--   4. Fill the form — the install handler creates the first admin row,
--      updates site_settings.current_profit, and flips SITE_INSTALLED to "1"
--      in config.json. Re-running deploy_migrations.sql after install is
--      still safe — INSERT IGNORE on site_settings preserves your settings.
--   5. Log in at /admin/login, then paste the parent API key into
--      site_settings.api_key via the admin Settings page.
--
-- Compatible with MySQL 5.7+ / 8.0+.
-- ============================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- SECTION 1: Base schema
-- ============================================================

-- active_sessions — one-session-per-user enforcement.
CREATE TABLE IF NOT EXISTS `active_sessions` (
  `id`         INT NOT NULL AUTO_INCREMENT,
  `user_id`    VARCHAR(255) NOT NULL,
  `session_id` VARCHAR(255) NOT NULL,
  `login_time` DATETIME NOT NULL DEFAULT '1970-01-01 01:00:00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- admin — back-office accounts.
CREATE TABLE IF NOT EXISTS `admin` (
  `id`         INT NOT NULL AUTO_INCREMENT,
  `username`   VARCHAR(50) NOT NULL,
  `email`      VARCHAR(50) NOT NULL,
  `password`   VARCHAR(255) NOT NULL,
  `admin_type` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- admin_tokens — remember-me tokens for admin sessions.
CREATE TABLE IF NOT EXISTS `admin_tokens` (
  `id`       INT NOT NULL AUTO_INCREMENT,
  `token`    VARCHAR(255) NOT NULL,
  `expiry`   DATETIME NOT NULL,
  `admin_id` INT NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- history — every order placed via the child panel. `activation_id`
-- stores the parent's history.id so order-event webhooks can locate
-- the local row.
CREATE TABLE IF NOT EXISTS `history` (
  `id`              INT NOT NULL AUTO_INCREMENT,
  `date`            DATETIME DEFAULT NULL,
  `service`         VARCHAR(255) DEFAULT NULL,
  `country`         VARCHAR(255) DEFAULT NULL,
  `price`           DECIMAL(10,2) DEFAULT NULL,
  `Number`          VARCHAR(255) DEFAULT NULL,
  `code`            TEXT,
  `status`          VARCHAR(50) DEFAULT NULL,
  `user_id`         INT DEFAULT NULL,
  `activation_id`   VARCHAR(50) DEFAULT NULL,
  `expiration_time` DATETIME DEFAULT NULL,
  `duration`        INT DEFAULT NULL,
  `source`          VARCHAR(50) DEFAULT NULL,
  `check_status`    VARCHAR(20) DEFAULT NULL,
  `repeatable`      TINYINT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_activation_id` (`activation_id`),
  KEY `idx_user_status`   (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- site_settings — single-row config table (id=1). `api_key` is the
-- reseller's parent-side API key. Add the api_key_rotated_at column
-- below in SECTION 2.
CREATE TABLE IF NOT EXISTS `site_settings` (
  `id`                          INT NOT NULL AUTO_INCREMENT,
  `current_profit`              VARCHAR(1024) DEFAULT NULL,
  `vpay_access_token`           VARCHAR(1024) DEFAULT NULL,
  `vpay_merchant_email`         VARCHAR(1024) DEFAULT NULL,
  `vpay_merchant_password`      VARCHAR(1024) DEFAULT NULL,
  `korapay_secret_key`          VARCHAR(1024) DEFAULT NULL,
  `manual_payment_account`      VARCHAR(250) DEFAULT NULL,
  `manual_payment_account_name` VARCHAR(250) DEFAULT NULL,
  `manual_payment_bank`         VARCHAR(250) DEFAULT NULL,
  `manual_payment`              TINYINT DEFAULT NULL,
  `vpay`                        TINYINT DEFAULT NULL,
  `korapay`                     TINYINT DEFAULT NULL,
  `api_key`                     VARCHAR(255) NOT NULL DEFAULT '',
  `vpay_public_key`             VARCHAR(225) DEFAULT NULL,
  `korapay_public_key`          VARCHAR(225) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- transactions — wallet deposits and refunds.
CREATE TABLE IF NOT EXISTS `transactions` (
  `transaction_id` VARCHAR(255) NOT NULL,
  `date`           DATETIME DEFAULT NULL,
  `amount`         DECIMAL(10,2) DEFAULT NULL,
  `user_id`        INT DEFAULT NULL,
  `status`         VARCHAR(50) DEFAULT NULL,
  `type`           VARCHAR(255) DEFAULT NULL,
  `image`          VARCHAR(255) DEFAULT NULL,
  `reason`         TEXT,
  `sender_name`    VARCHAR(255) DEFAULT NULL,
  `processor`      VARCHAR(250) DEFAULT NULL,
  PRIMARY KEY (`transaction_id`),
  KEY `idx_user_status` (`user_id`, `status`),
  KEY `idx_date`        (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- users — child panel customer accounts.
CREATE TABLE IF NOT EXISTS `users` (
  `user_id`              INT NOT NULL AUTO_INCREMENT,
  `username`             VARCHAR(255) DEFAULT NULL,
  `email`                VARCHAR(255) DEFAULT NULL,
  `password`             TEXT,
  `wallet_balance`       DECIMAL(10,2) DEFAULT NULL,
  `usertype`             VARCHAR(50) DEFAULT 'user',
  `user_status`          TINYINT DEFAULT '1',
  `reason`               TEXT,
  `api_key`              VARCHAR(100) NOT NULL,
  `temp_password_status` TINYINT NOT NULL DEFAULT '0',
  PRIMARY KEY (`user_id`),
  KEY `idx_api_key`  (`api_key`),
  KEY `idx_username` (`username`),
  KEY `idx_email`    (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- user_tokens — remember-me tokens for user sessions.
CREATE TABLE IF NOT EXISTS `user_tokens` (
  `id`      INT NOT NULL AUTO_INCREMENT,
  `token`   VARCHAR(255) NOT NULL,
  `expiry`  DATETIME NOT NULL,
  `user_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SECTION 2: Key-rotation webhook receiver
-- Source: migrations/api_key_rotations.sql
-- ============================================================
-- Idempotency ledger for /webhook/rotate-api-key — stops the same
-- rotation_id from being applied twice when the parent retries on
-- a lost response. Adds an optional last-rotated timestamp on
-- site_settings for the admin UI.

CREATE TABLE IF NOT EXISTS `api_key_rotations` (
  `rotation_id`  VARCHAR(64) NOT NULL,
  `applied_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `new_key_hint` VARCHAR(8) DEFAULT NULL,
  PRIMARY KEY (`rotation_id`),
  KEY `idx_applied_at` (`applied_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- site_settings.api_key_rotated_at — nullable DATETIME.
SET @_c = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME   = 'site_settings'
             AND COLUMN_NAME  = 'api_key_rotated_at');
SET @_s = IF(@_c = 0,
  'ALTER TABLE `site_settings` ADD COLUMN `api_key_rotated_at` DATETIME DEFAULT NULL',
  'SELECT 1');
PREPARE _st FROM @_s; EXECUTE _st; DEALLOCATE PREPARE _st;

-- ============================================================
-- SECTION 3: Order-event webhook receiver
-- Source: migrations/order_event_webhook.sql
-- ============================================================
-- Idempotency ledger for /webhook/order-event so the parent's
-- delivery worker can safely retry without double-applying state
-- to local history rows.

CREATE TABLE IF NOT EXISTS `webhook_order_events` (
  `event_id`    VARCHAR(64) NOT NULL,
  `event_type`  VARCHAR(32) NOT NULL,
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `idx_received_at` (`received_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SECTION 4: Pool labels (operator-facing pool customization)
-- ============================================================
-- The parent platform exposes its providers under codenames (Alpha,
-- Bravo, Charlie, Delta, Echo, Foxtrot). Each child panel can
-- rename them for their own branding, hide pools they don't want
-- to offer, and control display order — all without affecting
-- the underlying API call (which always uses the canonical codename).

CREATE TABLE IF NOT EXISTS `pool_labels` (
  `codename`     VARCHAR(16) NOT NULL,
  `display_name` VARCHAR(100) NOT NULL,
  `enabled`      TINYINT NOT NULL DEFAULT 1,
  `sort_order`   INT NOT NULL DEFAULT 0,
  `updated_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`codename`),
  KEY `idx_enabled_order` (`enabled`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed the 6 parent codenames with default display names matching the
-- codenames themselves. The admin can rename, toggle, or reorder via
-- Admin → Pool Labels. INSERT IGNORE so re-runs preserve operator edits.
INSERT IGNORE INTO `pool_labels` (`codename`, `display_name`, `sort_order`) VALUES
  ('Alpha',   'Alpha',   1),
  ('Bravo',   'Bravo',   2),
  ('Charlie', 'Charlie', 3),
  ('Delta',   'Delta',   4),
  ('Echo',    'Echo',    5),
  ('Foxtrot', 'Foxtrot', 6);

-- ============================================================
-- SECTION 5: Required seed data
-- ============================================================
-- The app reads `SELECT * FROM site_settings WHERE id = 1` on almost
-- every page — without this row, the panel 500s on boot. INSERT IGNORE
-- so a re-run on an existing DB doesn't clobber the operator's edits.
--
-- After running this script, set the real values from the admin UI
-- (Settings → Payment / Verification) or with an UPDATE statement.

INSERT IGNORE INTO `site_settings`
  (`id`, `current_profit`, `manual_payment`, `vpay`, `korapay`, `api_key`)
VALUES
  (1, '0', 0, 0, 0, '');

-- ============================================================
-- Done.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 1;
