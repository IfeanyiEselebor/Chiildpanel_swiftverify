-- ============================================================
-- Child Panel migration: order-event webhook receiver
-- ============================================================
-- Adds the dedupe ledger used by /webhook/order-event so the parent
-- can retry deliveries without double-applying state.
-- ============================================================

CREATE TABLE IF NOT EXISTS `webhook_order_events` (
  `event_id`    VARCHAR(64) NOT NULL,
  `event_type`  VARCHAR(32) NOT NULL,
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `idx_received_at` (`received_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
