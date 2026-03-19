-- =============================================================
-- Vintality Demo — Database Schema
-- PostgreSQL 16 + PostGIS + pgvector
-- =============================================================

-- Extensions
-- Note: PostGIS would be used in production for block polygons and spatial queries.
-- For this demo, we use simple lat/lon columns instead.
CREATE EXTENSION IF NOT EXISTS vector;          -- embeddings for knowledge base RAG

-- =============================================================
-- CORE TABLES: Farm structure
-- =============================================================

-- A farm is the top-level entity. One customer = one farm.
CREATE TABLE farms (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    latitude        NUMERIC(9,6),                -- GPS latitude
    longitude       NUMERIC(10,6),               -- GPS longitude
    elevation_m     NUMERIC(6,1),
    region          TEXT NOT NULL,                -- e.g. 'Naramata Bench'
    timezone        TEXT DEFAULT 'America/Vancouver',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- A block is a contiguous planted area within a farm.
-- This is the primary unit supervisors think about.
CREATE TABLE blocks (
    id              SERIAL PRIMARY KEY,
    farm_id         INTEGER REFERENCES farms(id),
    code            TEXT NOT NULL,                -- e.g. 'B5'
    name            TEXT,                         -- e.g. 'Cab Franc South'
    varietal        TEXT NOT NULL,                -- e.g. 'Cabernet Franc'
    area_ha         NUMERIC(4,2),
    aspect          TEXT,                         -- 'south-facing', 'north-facing'
    slope_pct       NUMERIC(4,1),
    soil_type       TEXT,                         -- 'sandy-loam', 'clay-loam'
    row_orientation TEXT,                         -- 'NE-SW', 'N-S'
    plant_year      INTEGER,
    polygon_geojson TEXT,                        -- GeoJSON string (PostGIS in production)
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(farm_id, code)
);

-- =============================================================
-- SENSORS: Physical devices deployed in vineyard
-- =============================================================

-- Each sensor node is a physical device in a block.
CREATE TABLE sensors (
    id              SERIAL PRIMARY KEY,
    block_id        INTEGER REFERENCES blocks(id),
    code            TEXT NOT NULL,                -- e.g. 'SM-B5a', 'TH-B3b'
    sensor_type     TEXT NOT NULL,                -- 'soil_moisture', 'temp_humidity', 'weather_station', 'rain_gauge'
    position        TEXT,                         -- 'lower_slope', 'upper_slope', 'mid_row'
    depth_cm        INTEGER,                     -- for soil sensors: 30, 60, 90
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(10,6),
    installed_at    TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ,                 -- connectivity tracking
    status          TEXT DEFAULT 'active',        -- 'active', 'offline', 'maintenance'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(code)
);

-- =============================================================
-- TIME-SERIES: Sensor readings (the big table)
-- =============================================================

-- Raw sensor readings. In production this would be partitioned
-- by time (e.g. monthly) for performance. For the demo, a
-- simple table with an index on (sensor_id, recorded_at).
CREATE TABLE sensor_readings (
    id              BIGSERIAL PRIMARY KEY,
    sensor_id       INTEGER REFERENCES sensors(id),
    recorded_at     TIMESTAMPTZ NOT NULL,

    -- Soil moisture sensors
    vwc_percent     NUMERIC(5,2),       -- Volumetric Water Content (%)
    soil_temp_c     NUMERIC(5,2),       -- Soil temperature
    ec_dsm          NUMERIC(6,3),       -- Electrical conductivity (dS/m)

    -- Temperature/humidity sensors
    air_temp_c      NUMERIC(5,2),
    humidity_pct    NUMERIC(5,2),
    vpd_kpa         NUMERIC(5,3),       -- Vapour Pressure Deficit (calculated)

    -- Weather station (farm-level)
    wind_speed_kmh  NUMERIC(5,2),
    wind_dir_deg    NUMERIC(5,1),
    solar_rad_wm2   NUMERIC(7,2),       -- Solar radiation W/m²
    rain_mm         NUMERIC(5,2),
    pressure_hpa    NUMERIC(7,2),

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_readings_sensor_time
    ON sensor_readings(sensor_id, recorded_at DESC);

CREATE INDEX idx_readings_time
    ON sensor_readings(recorded_at DESC);

-- =============================================================
-- AGRONOMIC MODELS: Computed outputs from Lambda functions
-- =============================================================

-- Disease risk scores (PM, Botrytis) per block.
-- These are computed hourly by existing Lambda functions.
CREATE TABLE disease_risk (
    id              BIGSERIAL PRIMARY KEY,
    block_id        INTEGER REFERENCES blocks(id),
    computed_at     TIMESTAMPTZ NOT NULL,

    pm_risk_score   NUMERIC(5,1),       -- Powdery Mildew risk 0-100
    botrytis_score  NUMERIC(5,1),       -- Botrytis risk 0-100

    -- Driving conditions (inputs to the model)
    driving_temp_c  NUMERIC(5,2),       -- Canopy temp driving PM
    driving_rh_pct  NUMERIC(5,2),       -- Humidity driving PM
    leaf_wetness_h  NUMERIC(5,1),       -- Hours of leaf wetness

    -- Spray tracking
    last_spray_date DATE,
    days_since_spray INTEGER,
    spray_efficacy_pct NUMERIC(5,1),    -- Decay of last spray

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_disease_block_time
    ON disease_risk(block_id, computed_at DESC);

-- Evapotranspiration and irrigation deficit per block.
-- ETref is the reference evapotranspiration (Penman-Monteith).
CREATE TABLE irrigation_status (
    id              BIGSERIAL PRIMARY KEY,
    block_id        INTEGER REFERENCES blocks(id),
    computed_at     TIMESTAMPTZ NOT NULL,

    etref_mm        NUMERIC(5,2),       -- Daily ET reference (mm)
    etc_mm          NUMERIC(5,2),       -- Crop ET (ETref × Kc)
    deficit_mm      NUMERIC(6,2),       -- Cumulative irrigation deficit
    field_cap_pct   NUMERIC(5,1),       -- Current % of field capacity
    pwp_proximity   NUMERIC(5,1),       -- Closeness to permanent wilting point

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_irrigation_block_time
    ON irrigation_status(block_id, computed_at DESC);

-- GDD (Growing Degree Days) accumulation tracking.
CREATE TABLE gdd_tracking (
    id              SERIAL PRIMARY KEY,
    farm_id         INTEGER REFERENCES farms(id),
    date            DATE NOT NULL,
    gdd_daily       NUMERIC(5,2),       -- GDD for this day
    gdd_cumulative  NUMERIC(7,2),       -- Season total
    gdd_5yr_avg     NUMERIC(7,2),       -- 5-year average for comparison
    phenological_stage TEXT,             -- 'dormant','budbreak','flowering','fruit_set','veraison','harvest'

    UNIQUE(farm_id, date)
);

-- =============================================================
-- IRRIGATION EVENTS: From Lumo integration
-- =============================================================

CREATE TABLE irrigation_events (
    id              SERIAL PRIMARY KEY,
    block_id        INTEGER REFERENCES blocks(id),
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_min    INTEGER,
    volume_mm       NUMERIC(5,2),       -- mm of water applied
    source          TEXT DEFAULT 'lumo', -- 'lumo', 'manual'
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_irrigation_events_block
    ON irrigation_events(block_id, started_at DESC);

-- =============================================================
-- WEATHER FORECAST: Cached from Visual Crossing
-- =============================================================

CREATE TABLE weather_forecast (
    id              SERIAL PRIMARY KEY,
    farm_id         INTEGER REFERENCES farms(id),
    forecast_for    TIMESTAMPTZ NOT NULL,    -- the hour being forecast
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),

    temp_c          NUMERIC(5,2),
    humidity_pct    NUMERIC(5,2),
    wind_speed_kmh  NUMERIC(5,2),
    rain_prob_pct   NUMERIC(5,1),
    rain_mm         NUMERIC(5,2),
    solar_rad_wm2   NUMERIC(7,2),
    frost_risk      BOOLEAN DEFAULT FALSE,

    UNIQUE(farm_id, forecast_for)
);

-- =============================================================
-- KNOWLEDGE BASE: For sensor troubleshooting RAG (Phase 4)
-- pgvector stores embeddings of documentation chunks
-- =============================================================

CREATE TABLE knowledge_base (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    source          TEXT,                -- 'sensor_manual', 'installation_sop', 'lorawan_guide'
    category        TEXT,                -- 'calibration', 'troubleshooting', 'installation', 'connectivity'
    content         TEXT NOT NULL,        -- the actual text chunk
    embedding       vector(1536),        -- OpenAI ada-002 or similar embedding
    metadata        JSONB,               -- additional structured metadata
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kb_embedding
    ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- =============================================================
-- VIEWS: Convenient latest-value views for tool functions
-- =============================================================

-- Latest sensor reading per sensor (most recent only)
CREATE VIEW sensor_readings_latest AS
SELECT DISTINCT ON (sensor_id)
    sr.*,
    s.code AS sensor_code,
    s.sensor_type,
    s.block_id,
    b.code AS block_code,
    b.varietal,
    b.farm_id
FROM sensor_readings sr
JOIN sensors s ON s.id = sr.sensor_id
JOIN blocks b ON b.id = s.block_id
ORDER BY sensor_id, recorded_at DESC;

-- Latest disease risk per block
CREATE VIEW disease_risk_latest AS
SELECT DISTINCT ON (block_id)
    dr.*,
    b.code AS block_code,
    b.varietal
FROM disease_risk dr
JOIN blocks b ON b.id = dr.block_id
ORDER BY block_id, computed_at DESC;

-- Latest irrigation status per block
CREATE VIEW irrigation_status_latest AS
SELECT DISTINCT ON (block_id)
    ist.*,
    b.code AS block_code,
    b.varietal
FROM irrigation_status ist
JOIN blocks b ON b.id = ist.block_id
ORDER BY block_id, computed_at DESC;
