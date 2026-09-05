-- AetherVoice control plane + call observability
CREATE TABLE IF NOT EXISTS companies (
  id VARCHAR(64) PRIMARY KEY,
  payload JSON NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS deployments (
  id VARCHAR(64) PRIMARY KEY,
  company_id VARCHAR(64) NOT NULL,
  payload JSON NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_deployments_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per phone / WebRTC session
CREATE TABLE IF NOT EXISTS calls (
  id VARCHAR(64) PRIMARY KEY,
  company_id VARCHAR(64) NULL,
  deployment_id VARCHAR(64) NULL,
  direction VARCHAR(16) NOT NULL DEFAULT 'inbound',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  pipeline_mode VARCHAR(32) NULL,
  entry_agent_id VARCHAR(64) NULL,
  from_number VARCHAR(64) NULL,
  to_number VARCHAR(64) NULL,
  metadata JSON NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP NULL,
  INDEX idx_calls_company (company_id),
  INDEX idx_calls_deployment (deployment_id),
  INDEX idx_calls_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Caller / agent utterances (critical for debugging)
CREATE TABLE IF NOT EXISTS call_turns (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  call_id VARCHAR(64) NOT NULL,
  seq INT NOT NULL,
  role VARCHAR(32) NOT NULL,
  content MEDIUMTEXT NOT NULL,
  agent_id VARCHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_turns_call (call_id, seq),
  CONSTRAINT fk_turns_call FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tool request / response payloads
CREATE TABLE IF NOT EXISTS call_tool_io (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  call_id VARCHAR(64) NOT NULL,
  seq INT NOT NULL,
  tool_name VARCHAR(128) NOT NULL,
  arguments JSON NULL,
  result JSON NULL,
  ok TINYINT(1) NOT NULL DEFAULT 0,
  error_code VARCHAR(64) NULL,
  latency_ms DOUBLE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_tools_call (call_id, seq),
  INDEX idx_tools_name (tool_name),
  CONSTRAINT fk_tools_call FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Handoffs, errors, pipeline events
CREATE TABLE IF NOT EXISTS call_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  call_id VARCHAR(64) NOT NULL,
  seq INT NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_events_call (call_id, seq),
  INDEX idx_events_type (event_type),
  CONSTRAINT fk_events_call FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
