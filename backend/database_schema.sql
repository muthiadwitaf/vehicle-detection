-- ============================================================================
-- PostgreSQL Database Schema for Vehicle Detection Dashboard
-- ============================================================================
-- Database: postgres (or create a new one if preferred)
-- Purpose: Store vehicle detection counters per camera for persistence
-- ============================================================================

-- Create detection_counts table
CREATE TABLE IF NOT EXISTS detection_counts (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NOT NULL UNIQUE,
    camera_name VARCHAR(200),
    car_count INTEGER DEFAULT 0,
    motorcycle_count INTEGER DEFAULT 0,
    bus_count INTEGER DEFAULT 0,
    truck_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index on camera_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_camera_id ON detection_counts(camera_id);

-- ============================================================================
-- Optional: Insert sample data for testing
-- ============================================================================
-- Uncomment the lines below if you want to test with sample data

-- INSERT INTO detection_counts (camera_id, camera_name, car_count, motorcycle_count, bus_count, truck_count)
-- VALUES 
--     ('cp_arcamanik', 'CP ARCAMANIK', 150, 320, 12, 45),
--     ('cp_cibiru_2', 'CP CIBIRU 2', 98, 210, 8, 23),
--     ('cp_cibiru_3', 'CP CIBIRU 3', 112, 189, 5, 18)
-- ON CONFLICT (camera_id) DO NOTHING;

-- ============================================================================
-- Useful queries for monitoring
-- ============================================================================

-- View all camera counts
-- SELECT camera_id, camera_name, car_count, motorcycle_count, bus_count, truck_count, 
--        (car_count + motorcycle_count + bus_count + truck_count) as total,
--        last_updated
-- FROM detection_counts
-- ORDER BY last_updated DESC;

-- View total vehicles detected across all cameras
-- SELECT 
--     SUM(car_count) as total_cars,
--     SUM(motorcycle_count) as total_motorcycles,
--     SUM(bus_count) as total_buses,
--     SUM(truck_count) as total_trucks,
--     SUM(car_count + motorcycle_count + bus_count + truck_count) as grand_total
-- FROM detection_counts;

-- Reset counts for a specific camera
-- UPDATE detection_counts 
-- SET car_count = 0, motorcycle_count = 0, bus_count = 0, truck_count = 0, last_updated = NOW()
-- WHERE camera_id = 'cp_arcamanik';

-- Delete all data (use with caution!)
-- TRUNCATE TABLE detection_counts RESTART IDENTITY;

-- Drop table (use with caution!)
-- DROP TABLE IF EXISTS detection_counts;
