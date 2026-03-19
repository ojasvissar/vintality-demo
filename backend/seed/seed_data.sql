-- =============================================================
-- Vintality Demo — Seed Data
-- Realistic Okanagan vineyard: Naramata Bench
--
-- This data creates specific scenarios that demonstrate
-- the agent's capabilities:
--   1. Block B5 (Cab Franc) — critically dry, needs irrigation
--   2. Block B3 (Pinot Noir) — PM risk spiking
--   3. Block B7 (Chardonnay) — healthy, for contrast
--   4. Block B9 (Merlot) — sensor anomaly on one node
-- =============================================================

-- ===================== FARM =====================

INSERT INTO farms (name, slug, latitude, longitude, elevation_m, region) VALUES
(
    'Naramata Hills Vineyard',
    'naramata-hills',
    49.5935,
    -119.5903,
    420,
    'Naramata Bench'
);

-- ===================== BLOCKS =====================

INSERT INTO blocks (farm_id, code, name, varietal, area_ha, aspect, slope_pct, soil_type, row_orientation, plant_year) VALUES
(1, 'B3', 'Pinot Noir North',    'Pinot Noir',       1.8, 'north-facing',  8.5,  'clay-loam',  'NE-SW', 2012),
(1, 'B5', 'Cab Franc South',     'Cabernet Franc',   2.1, 'south-facing',  12.0, 'sandy-loam', 'N-S',   2015),
(1, 'B7', 'Chardonnay East',     'Chardonnay',       1.4, 'east-facing',   5.2,  'silt-loam',  'E-W',   2010),
(1, 'B9', 'Merlot Ridge',        'Merlot',           1.9, 'south-facing',  15.0, 'sandy-loam', 'N-S',   2014);

-- ===================== SENSORS =====================

-- Block B3: Pinot Noir — 2 soil moisture, 2 temp/humidity
INSERT INTO sensors (block_id, code, sensor_type, position, depth_cm, installed_at, last_seen, status) VALUES
(1, 'SM-B3a', 'soil_moisture',  'lower_slope', 30,  '2024-03-15', NOW() - INTERVAL '10 minutes', 'active'),
(1, 'SM-B3b', 'soil_moisture',  'upper_slope', 30,  '2024-03-15', NOW() - INTERVAL '12 minutes', 'active'),
(1, 'TH-B3a', 'temp_humidity',  'lower_slope', NULL,'2024-03-15', NOW() - INTERVAL '10 minutes', 'active'),
(1, 'TH-B3b', 'temp_humidity',  'upper_slope', NULL,'2024-03-15', NOW() - INTERVAL '10 minutes', 'active');

-- Block B5: Cab Franc — 1 soil moisture, 2 temp/humidity
INSERT INTO sensors (block_id, code, sensor_type, position, depth_cm, installed_at, last_seen, status) VALUES
(2, 'SM-B5a', 'soil_moisture',  'mid_row',     30,  '2024-03-15', NOW() - INTERVAL '8 minutes',  'active'),
(2, 'TH-B5a', 'temp_humidity',  'lower_slope', NULL,'2024-03-15', NOW() - INTERVAL '8 minutes',  'active'),
(2, 'TH-B5b', 'temp_humidity',  'upper_slope', NULL,'2024-03-15', NOW() - INTERVAL '9 minutes',  'active');

-- Block B7: Chardonnay — 1 soil moisture, 1 temp/humidity
INSERT INTO sensors (block_id, code, sensor_type, position, depth_cm, installed_at, last_seen, status) VALUES
(3, 'SM-B7a', 'soil_moisture',  'mid_row',     30,  '2024-03-15', NOW() - INTERVAL '15 minutes', 'active'),
(3, 'TH-B7a', 'temp_humidity',  'mid_row',     NULL,'2024-03-15', NOW() - INTERVAL '15 minutes', 'active');

-- Block B9: Merlot — 2 soil moisture, 2 temp/humidity (one anomalous)
INSERT INTO sensors (block_id, code, sensor_type, position, depth_cm, installed_at, last_seen, status) VALUES
(4, 'SM-B9a', 'soil_moisture',  'lower_slope', 30,  '2024-03-15', NOW() - INTERVAL '11 minutes', 'active'),
(4, 'SM-B9b', 'soil_moisture',  'upper_slope', 30,  '2024-03-15', NOW() - INTERVAL '11 minutes', 'active'),
(4, 'TH-B9a', 'temp_humidity',  'lower_slope', NULL,'2024-03-15', NOW() - INTERVAL '11 minutes', 'active'),
(4, 'TH-B9b', 'temp_humidity',  'upper_slope', NULL,'2024-03-15', NOW() - INTERVAL '6 days',     'active');  -- anomaly: reading high

-- Weather station (farm-level)
INSERT INTO sensors (block_id, code, sensor_type, position, depth_cm, installed_at, last_seen, status) VALUES
(1, 'WS-01', 'weather_station', 'hilltop', NULL, '2024-03-01', NOW() - INTERVAL '5 minutes', 'active');

-- ===================== SENSOR READINGS =====================
-- Generate 7 days of hourly data using generate_series.
-- Each block tells a different story.

-- Helper: generate timestamps for the last 7 days, hourly
-- We'll use NOW() - interval for realistic "current" data

-- === B5 Cab Franc: Drying out (VWC declining from 35 → 28) ===
INSERT INTO sensor_readings (sensor_id, recorded_at, vwc_percent, soil_temp_c)
SELECT
    5,  -- SM-B5a
    ts,
    -- VWC declining steadily from 35 to 28 over 7 days
    35.0 - (EXTRACT(EPOCH FROM (NOW() - ts)) / EXTRACT(EPOCH FROM INTERVAL '7 days')) * 7.0
        + (random() * 0.6 - 0.3),  -- small noise
    -- Soil temp follows daily cycle: 16-24°C
    20.0 + 4.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 0.5)
FROM generate_series(
    NOW() - INTERVAL '7 days',
    NOW(),
    INTERVAL '1 hour'
) AS ts;

-- === B5 Cab Franc: Temp/humidity (warm, moderate humidity) ===
INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, vpd_kpa)
SELECT
    6,  -- TH-B5a
    ts,
    -- Air temp: daily cycle 14-31°C (hot afternoons)
    22.5 + 8.5 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 1.0),
    -- Humidity: inverse of temp, 45-72%
    58.0 - 13.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 3.0),
    -- VPD calculated: higher when hot and dry
    1.2 + 0.8 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 0.1)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- === B3 Pinot Noir: Humid, PM-friendly conditions ===
INSERT INTO sensor_readings (sensor_id, recorded_at, vwc_percent, soil_temp_c)
SELECT
    1,  -- SM-B3a
    ts,
    -- VWC moderate and stable (irrigated recently): 38-42%
    40.0 + 2.0 * sin(EXTRACT(EPOCH FROM ts)::float / 86400.0) + (random() * 1.0),
    18.0 + 3.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.5)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, vpd_kpa)
SELECT
    3,  -- TH-B3a
    ts,
    -- Cooler (north-facing): 12-25°C
    18.5 + 6.5 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 0.8),
    -- HIGH humidity (PM territory): 65-85%
    75.0 - 10.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 3.0),
    -- Low VPD (humid)
    0.5 + 0.4 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + (random() * 0.05)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- === B7 Chardonnay: Healthy baseline ===
INSERT INTO sensor_readings (sensor_id, recorded_at, vwc_percent, soil_temp_c)
SELECT
    8,  -- SM-B7a
    ts,
    -- Good VWC range: 42-48% (well irrigated)
    45.0 + 3.0 * sin(EXTRACT(EPOCH FROM ts)::float / 86400.0) + (random() * 0.8),
    19.0 + 3.5 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.4)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, vpd_kpa)
SELECT
    9,  -- TH-B7a
    ts,
    20.0 + 7.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.8),
    55.0 - 8.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 2.5),
    1.0 + 0.6 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.08)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- === B9 Merlot: Normal + anomalous sensor ===
INSERT INTO sensor_readings (sensor_id, recorded_at, vwc_percent, soil_temp_c)
SELECT
    10,  -- SM-B9a (normal)
    ts,
    37.0 + 2.5 * sin(EXTRACT(EPOCH FROM ts)::float / 86400.0) + (random() * 0.8),
    20.0 + 4.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.5)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- TH-B9b: reads 3°C ABOVE block average (sensor drift / bad mount)
INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, vpd_kpa)
SELECT
    13,  -- TH-B9b (anomalous — 3°C hot)
    ts,
    23.0 + 7.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)
        + 3.0  -- OFFSET: 3°C above normal
        + (random() * 0.8),
    52.0 - 8.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 2.0),
    1.3 + 0.7 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.08)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- Normal TH-B9a for comparison
INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, vpd_kpa)
SELECT
    12,  -- TH-B9a (normal)
    ts,
    20.0 + 7.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.8),
    55.0 - 8.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 2.5),
    1.0 + 0.6 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 0.08)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- === Weather station data ===
INSERT INTO sensor_readings (sensor_id, recorded_at, air_temp_c, humidity_pct, wind_speed_kmh, wind_dir_deg, solar_rad_wm2, rain_mm, pressure_hpa)
SELECT
    14,  -- WS-01
    ts,
    21.0 + 8.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 1.0),
    58.0 - 10.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 3.0),
    8.0 + 6.0 * random(),
    180.0 + 90.0 * (random() - 0.5),
    GREATEST(0, 600.0 * sin(GREATEST(0, EXTRACT(HOUR FROM ts)::float - 6.0) * 3.14159 / 12.0) + random() * 30.0),
    0.0,  -- no rain in the last 7 days (dry spell)
    1015.0 + (random() * 4.0 - 2.0)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;


-- ===================== DISEASE RISK SCORES =====================
-- Computed "hourly" by agronomic Lambda functions

-- B3 Pinot Noir: PM risk climbing (humid conditions)
INSERT INTO disease_risk (block_id, computed_at, pm_risk_score, botrytis_score, driving_temp_c, driving_rh_pct, leaf_wetness_h, last_spray_date, days_since_spray, spray_efficacy_pct)
SELECT
    1,
    ts,
    -- PM risk climbing from 35 to 72 over 7 days
    35.0 + (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '7 days'))) / EXTRACT(EPOCH FROM INTERVAL '7 days')) * 37.0
        + (random() * 3.0 - 1.5),
    -- Botrytis moderate
    25.0 + (random() * 8.0),
    -- Driving conditions
    21.0 + (random() * 2.0),
    75.0 + (random() * 6.0),
    CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 0 AND 8 THEN 4.0 + random() * 2.0 ELSE 0 END,
    '2024-08-06',
    EXTRACT(DAY FROM (ts - DATE '2024-08-06'))::int,
    GREATEST(10, 95.0 - EXTRACT(DAY FROM (ts - DATE '2024-08-06'))::int * 7.0)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- B5 Cab Franc: PM risk moderate (warm but not too humid)
INSERT INTO disease_risk (block_id, computed_at, pm_risk_score, botrytis_score, driving_temp_c, driving_rh_pct, leaf_wetness_h, last_spray_date, days_since_spray, spray_efficacy_pct)
SELECT
    2,
    ts,
    -- Moderate PM: 40-55 range
    47.0 + 8.0 * sin(EXTRACT(EPOCH FROM ts)::float / 43200.0) + (random() * 3.0),
    15.0 + (random() * 5.0),
    24.0 + (random() * 2.0),
    58.0 + (random() * 5.0),
    CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 0 AND 6 THEN 2.0 + random() * 1.5 ELSE 0 END,
    '2024-08-08',
    EXTRACT(DAY FROM (ts - DATE '2024-08-08'))::int,
    GREATEST(15, 95.0 - EXTRACT(DAY FROM (ts - DATE '2024-08-08'))::int * 6.5)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- B7 Chardonnay: Low PM risk (good airflow, east-facing)
INSERT INTO disease_risk (block_id, computed_at, pm_risk_score, botrytis_score, driving_temp_c, driving_rh_pct, leaf_wetness_h, last_spray_date, days_since_spray, spray_efficacy_pct)
SELECT
    3,
    ts,
    22.0 + (random() * 6.0),
    12.0 + (random() * 5.0),
    20.0 + (random() * 2.0),
    52.0 + (random() * 4.0),
    CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 2 AND 5 THEN 1.0 + random() ELSE 0 END,
    '2024-08-10',
    EXTRACT(DAY FROM (ts - DATE '2024-08-10'))::int,
    GREATEST(20, 95.0 - EXTRACT(DAY FROM (ts - DATE '2024-08-10'))::int * 6.0)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- B9 Merlot: Moderate
INSERT INTO disease_risk (block_id, computed_at, pm_risk_score, botrytis_score, driving_temp_c, driving_rh_pct, leaf_wetness_h, last_spray_date, days_since_spray, spray_efficacy_pct)
SELECT
    4,
    ts,
    38.0 + (random() * 8.0),
    18.0 + (random() * 5.0),
    22.0 + (random() * 2.0),
    55.0 + (random() * 5.0),
    CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 1 AND 6 THEN 2.0 + random() * 1.0 ELSE 0 END,
    '2024-08-09',
    EXTRACT(DAY FROM (ts - DATE '2024-08-09'))::int,
    GREATEST(15, 95.0 - EXTRACT(DAY FROM (ts - DATE '2024-08-09'))::int * 6.0)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;


-- ===================== IRRIGATION STATUS =====================

-- B5: Deficit growing (no irrigation for 5 days)
INSERT INTO irrigation_status (block_id, computed_at, etref_mm, etc_mm, deficit_mm, field_cap_pct, pwp_proximity)
SELECT
    2,
    ts,
    -- ETref: 3.2-4.1 mm/day based on solar + temp
    3.4 + 0.7 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) * CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 8 AND 18 THEN 1 ELSE 0.1 END,
    -- ETc = ETref * Kc (Kc ~0.7 for post-veraison grape)
    (3.4 + 0.7 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)) * 0.7,
    -- Deficit growing from 12 to 34mm
    12.0 + (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '7 days'))) / EXTRACT(EPOCH FROM INTERVAL '7 days')) * 22.0,
    -- Field capacity dropping: 55% → 42%
    55.0 - (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '7 days'))) / EXTRACT(EPOCH FROM INTERVAL '7 days')) * 13.0,
    -- PWP proximity: getting closer
    35.0 - (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '7 days'))) / EXTRACT(EPOCH FROM INTERVAL '7 days')) * 12.0
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- B3: Moderate deficit (irrigated 3 days ago)
INSERT INTO irrigation_status (block_id, computed_at, etref_mm, etc_mm, deficit_mm, field_cap_pct, pwp_proximity)
SELECT
    1, ts,
    2.8 + 0.5 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) * CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 8 AND 18 THEN 1 ELSE 0.1 END,
    (2.8 + 0.5 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)) * 0.7,
    8.0 + (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '3 days'))) / EXTRACT(EPOCH FROM INTERVAL '3 days')) * 6.0,
    62.0 - (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '3 days'))) / EXTRACT(EPOCH FROM INTERVAL '3 days')) * 5.0,
    50.0 - (EXTRACT(EPOCH FROM (ts - (NOW() - INTERVAL '3 days'))) / EXTRACT(EPOCH FROM INTERVAL '3 days')) * 3.0
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;

-- B7: Healthy (irrigated yesterday)
INSERT INTO irrigation_status (block_id, computed_at, etref_mm, etc_mm, deficit_mm, field_cap_pct, pwp_proximity)
SELECT
    3, ts,
    3.0 + 0.6 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) * CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 8 AND 18 THEN 1 ELSE 0.1 END,
    (3.0 + 0.6 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5)) * 0.7,
    3.0 + (random() * 2.0),
    72.0 - (random() * 3.0),
    60.0 - (random() * 2.0)
FROM generate_series(NOW() - INTERVAL '7 days', NOW(), INTERVAL '1 hour') AS ts;


-- ===================== IRRIGATION EVENTS =====================

-- B5: Last irrigated 5 days ago
INSERT INTO irrigation_events (block_id, started_at, ended_at, duration_min, volume_mm, source) VALUES
(2, NOW() - INTERVAL '5 days 6 hours', NOW() - INTERVAL '5 days 3 hours', 180, 18.5, 'lumo'),
(2, NOW() - INTERVAL '9 days 6 hours', NOW() - INTERVAL '9 days 4 hours', 120, 12.0, 'lumo'),
(2, NOW() - INTERVAL '13 days 6 hours', NOW() - INTERVAL '13 days 3 hours 30 minutes', 150, 15.2, 'lumo');

-- B3: Irrigated 3 days ago
INSERT INTO irrigation_events (block_id, started_at, ended_at, duration_min, volume_mm, source) VALUES
(1, NOW() - INTERVAL '3 days 5 hours', NOW() - INTERVAL '3 days 2 hours', 180, 20.0, 'lumo'),
(1, NOW() - INTERVAL '7 days 6 hours', NOW() - INTERVAL '7 days 3 hours', 180, 19.5, 'lumo');

-- B7: Irrigated yesterday
INSERT INTO irrigation_events (block_id, started_at, ended_at, duration_min, volume_mm, source) VALUES
(3, NOW() - INTERVAL '1 day 5 hours', NOW() - INTERVAL '1 day 2 hours', 180, 22.0, 'lumo'),
(3, NOW() - INTERVAL '5 days 6 hours', NOW() - INTERVAL '5 days 3 hours', 180, 21.0, 'lumo');


-- ===================== GDD TRACKING =====================

INSERT INTO gdd_tracking (farm_id, date, gdd_daily, gdd_cumulative, gdd_5yr_avg, phenological_stage)
SELECT
    1,
    d::date,
    -- Daily GDD: ~12-18 in August
    14.5 + (random() * 4.0 - 2.0),
    -- Cumulative: ~1150 at start of range, growing
    1150.0 + (d::date - (NOW() - INTERVAL '30 days')::date) * 14.5,
    -- 5-year avg slightly lower
    1100.0 + (d::date - (NOW() - INTERVAL '30 days')::date) * 13.8,
    'veraison'
FROM generate_series(
    (NOW() - INTERVAL '30 days')::date,
    NOW()::date,
    '1 day'::interval
) AS d;


-- ===================== WEATHER FORECAST =====================
-- Next 48 hours: hot, dry, no rain

INSERT INTO weather_forecast (farm_id, forecast_for, temp_c, humidity_pct, wind_speed_kmh, rain_prob_pct, rain_mm, solar_rad_wm2, frost_risk)
SELECT
    1,
    ts,
    -- Hot days ahead: 28-33°C highs
    22.0 + 10.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 1.0),
    -- Dry: 35-55% humidity
    45.0 - 10.0 * sin(EXTRACT(HOUR FROM ts)::float * 3.14159 / 12.0 - 1.5) + (random() * 3.0),
    8.0 + (random() * 8.0),
    -- Very low rain chance
    5.0 + (random() * 3.0),
    0.0,
    GREATEST(0, 650.0 * sin(GREATEST(0, EXTRACT(HOUR FROM ts)::float - 6.0) * 3.14159 / 12.0)),
    FALSE
FROM generate_series(NOW(), NOW() + INTERVAL '48 hours', INTERVAL '1 hour') AS ts;


-- ===================== KNOWLEDGE BASE (sample docs) =====================
-- These are for the document RAG piece (Phase 4).
-- Embeddings would be generated by an embedding model;
-- for the demo we'll generate them in Python.

INSERT INTO knowledge_base (title, source, category, content, metadata) VALUES
(
    'Soil Moisture Sensor Calibration — Sandy Loam',
    'sensor_manual',
    'calibration',
    'Calibration procedure for soil moisture sensors in sandy loam soils: 1. Allow sensor to equilibrate for 48 hours after installation. 2. Take gravimetric soil samples at sensor depth (30cm). 3. Oven-dry samples at 105°C for 24 hours. 4. Calculate VWC = (wet weight - dry weight) / volume. 5. Compare sensor reading to gravimetric VWC. 6. If deviation exceeds ±3%, apply linear offset correction. Sandy loam typically shows higher drainage rates, so field capacity readings will stabilize faster (6-12 hours after saturation). Expected VWC range at field capacity: 22-32%. Permanent wilting point: 8-12%.',
    '{"soil_types": ["sandy-loam"], "sensor_model": "Teros-12"}'
),
(
    'Soil Moisture Sensor Calibration — Clay Loam',
    'sensor_manual',
    'calibration',
    'Calibration procedure for soil moisture sensors in clay loam soils: 1. Allow 72 hours equilibration (longer than sandy soils due to slower water movement). 2. Clay soils have higher water retention. 3. Typical field capacity VWC: 35-45%. 4. Permanent wilting point: 18-25%. 5. Clay can cause overestimation of VWC in some dielectric sensors due to bound water. 6. Check EC readings alongside VWC — high EC in clay may indicate salinity issues. 7. Recalibrate seasonally as soil structure changes.',
    '{"soil_types": ["clay-loam"], "sensor_model": "Teros-12"}'
),
(
    'LoRaWAN Connectivity Troubleshooting',
    'lorawan_guide',
    'connectivity',
    'If a sensor node shows as offline or has intermittent connectivity: 1. Check last_seen timestamp — if more than 2 hours, investigate. 2. Check RSSI value: above -100 dBm is acceptable, below -110 dBm needs gateway repositioning. 3. Check SNR: above 0 is good, below -5 indicates severe signal degradation. 4. Common causes of signal loss in vineyards: canopy growth in summer reducing line-of-sight to gateway, metal trellis wire interference, moisture on antenna. 5. Verify gateway is powered and connected to internet. 6. Try repositioning sensor node higher on the post (above canopy height). 7. If multiple nodes in same area drop out, suspect gateway issue.',
    '{"protocols": ["LoRaWAN", "TTN"], "severity": "high"}'
),
(
    'Temperature/Humidity Sensor Anomaly Detection',
    'sensor_manual',
    'troubleshooting',
    'Identifying faulty T/H sensor readings: 1. Compare sensor against block average — deviation of more than 2°C sustained over 24+ hours suggests sensor issue. 2. Common causes: direct sunlight on radiation shield (reads high), blocked ventilation slots (reads high and humid), bird nest on sensor (intermittent spikes), post-spray moisture in housing (reads high humidity for 12-24h). 3. Verification: compare against nearest weather station. 4. If sensor reads consistently 3°C+ above neighbors, check mounting position — south-facing posts receive more radiant heat. Recommend relocating to north side of post or adding secondary radiation shield.',
    '{"sensor_types": ["temp_humidity"], "issue": "anomaly"}'
),
(
    'Sensor Placement Guide — Vineyard Blocks',
    'installation_sop',
    'installation',
    'Optimal sensor placement for vineyard monitoring: 1. SOIL MOISTURE: Install at 30cm depth (primary root zone). Place in the drip line, 30cm from the emitter. For blocks >1.5ha, install two sensors — upper slope and lower slope — to capture drainage patterns. Avoid row ends and headlands. 2. TEMPERATURE/HUMIDITY: Mount at canopy height (1.2-1.5m) on the trellis post. Use radiation shield. Orient shield opening away from prevailing wind. Place in representative mid-block position, not at edges. For slope blocks, place one sensor at lower third and one at upper third. 3. RAIN GAUGE: One per farm is sufficient. Place in open area away from trees and structures. Top of gauge must be level. 4. WEATHER STATION: Mount at 2m height on dedicated post in open area with good fetch (no obstructions within 10× station height).',
    '{"scope": "full_farm", "priority": "essential"}'
);
