-- 众感 Sensemble MVP 数据库初始化（首次启动自动执行）
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ===== 用户 =====
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    email         VARCHAR(128),
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(16)  NOT NULL DEFAULT 'student',   -- student/teacher/admin
    college       VARCHAR(64),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ===== 设备（一机一 Token）=====
CREATE TABLE IF NOT EXISTS devices (
    device_id       VARCHAR(64) PRIMARY KEY,
    owner_id        BIGINT NOT NULL REFERENCES users(id),
    type            VARCHAR(32),
    sensors         JSONB DEFAULT '{}'::jsonb,
    token_hash      VARCHAR(255) NOT NULL,        -- sha256(设备Token)
    location        VARCHAR(64),
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    sample_interval INT DEFAULT 60,               -- 秒，用于完整度/离线判定
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    last_seen       TIMESTAMPTZ,
    offline_alerted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_devices_owner ON devices(owner_id);

-- ===== 时序数据（Timescale 超表）=====
CREATE TABLE IF NOT EXISTS sensor_data (
    id        BIGSERIAL,
    device_id VARCHAR(64) NOT NULL,
    ts        TIMESTAMPTZ NOT NULL,        -- 服务器接收时间（分区键）
    device_ts TIMESTAMPTZ,                 -- 设备本地时间
    metric    VARCHAR(32) NOT NULL,        -- temperature / humidity / co2 ...
    value     DOUBLE PRECISION,
    lat       DOUBLE PRECISION,
    lon       DOUBLE PRECISION,
    raw       JSONB
);
SELECT create_hypertable('sensor_data', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sd_device_ts ON sensor_data(device_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_sd_metric_ts ON sensor_data(metric, ts DESC);
-- 空间热力图/插值（P1）可加：ALTER TABLE sensor_data ADD COLUMN geom geography(Point,4326)
--   GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon,lat),4326)::geography) STORED;  并建 GIST 索引

-- ===== 数据集 =====
CREATE SEQUENCE IF NOT EXISTS dataset_seq START 1;
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id     VARCHAR(32) PRIMARY KEY,       -- SMDP-2026-0001
    name           VARCHAR(128) NOT NULL,
    creator_id     BIGINT NOT NULL REFERENCES users(id),
    description    TEXT,
    meta           JSONB DEFAULT '{}'::jsonb,     -- 元数据：型号/精度/采样率/位置/校准...
    device_id      VARCHAR(64),
    ts_start       TIMESTAMPTZ,
    ts_end         TIMESTAMPTZ,
    dqs            DOUBLE PRECISION,
    grade          CHAR(1),                       -- A/B/C
    visibility     VARCHAR(16) NOT NULL DEFAULT 'private',  -- public/private
    status         VARCHAR(16) NOT NULL DEFAULT 'draft',    -- draft/pending/published/rejected
    tags           TEXT[],
    download_count INT NOT NULL DEFAULT 0,
    archive_path   VARCHAR(256),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
CREATE INDEX IF NOT EXISTS idx_datasets_vis ON datasets(visibility);

-- ===== 数据集元数据版本历史 =====
CREATE TABLE IF NOT EXISTS dataset_versions (
    id          BIGSERIAL PRIMARY KEY,
    dataset_id  VARCHAR(32) NOT NULL REFERENCES datasets(dataset_id),
    version     INT NOT NULL,
    name        VARCHAR(128),
    description TEXT,
    meta        JSONB,
    editor_id   BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dsver_dataset ON dataset_versions(dataset_id);

-- ===== 审核 =====
CREATE TABLE IF NOT EXISTS reviews (
    id          BIGSERIAL PRIMARY KEY,
    dataset_id  VARCHAR(32) NOT NULL REFERENCES datasets(dataset_id),
    reviewer_id BIGINT REFERENCES users(id),
    result      VARCHAR(16) NOT NULL,    -- approved/rejected
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== 审计日志（安全底线）=====
CREATE TABLE IF NOT EXISTS audit_logs (
    id       BIGSERIAL PRIMARY KEY,
    actor_id BIGINT,
    action   VARCHAR(32) NOT NULL,    -- login/register/device_register/upload/download/review/ban...
    target   VARCHAR(64),
    detail   JSONB,
    ts       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== 对外 API Key =====
CREATE TABLE IF NOT EXISTS api_keys (
    id         BIGSERIAL PRIMARY KEY,
    owner_id   BIGINT NOT NULL REFERENCES users(id),
    name       VARCHAR(64) NOT NULL DEFAULT 'default',
    key_hash   VARCHAR(255) NOT NULL,        -- sha256(API Key)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_apikeys_hash ON api_keys(key_hash);

-- ===== 站内通知 =====
CREATE TABLE IF NOT EXISTS notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    ntype      VARCHAR(32) NOT NULL,
    message    TEXT NOT NULL,
    link       VARCHAR(128),
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);
