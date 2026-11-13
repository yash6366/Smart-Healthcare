-- ====================================================================
-- VakCare Healthcare Platform - Local MySQL Setup Script
--
-- Instructions:
-- 1. Open MySQL Workbench (or mysql command-line client) connected as root.
-- 2. Open and execute this SQL script.
-- 3. Replace 'VakCareDev2026!' with your chosen local development password if desired.
-- 4. Update the DB_PASSWORD in your .env or .env.local file to match.
-- ====================================================================

-- Step 1: Ensure local development database 'vakcare_db' exists with utf8mb4 charset
CREATE DATABASE IF NOT EXISTS `vakcare_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Step 2: Create dedicated local development user 'vakcare_dev' for 127.0.0.1 and localhost
CREATE USER IF NOT EXISTS 'vakcare_dev'@'127.0.0.1' IDENTIFIED BY 'VakCareDev2026!';
CREATE USER IF NOT EXISTS 'vakcare_dev'@'localhost' IDENTIFIED BY 'VakCareDev2026!';

-- Update password in case user already exists
ALTER USER 'vakcare_dev'@'127.0.0.1' IDENTIFIED BY 'VakCareDev2026!';
ALTER USER 'vakcare_dev'@'localhost' IDENTIFIED BY 'VakCareDev2026!';

-- Step 3: Grant all privileges on 'vakcare_db' to 'vakcare_dev' (least-privilege for local dev)
GRANT ALL PRIVILEGES ON `vakcare_db`.* TO 'vakcare_dev'@'127.0.0.1';
GRANT ALL PRIVILEGES ON `vakcare_db`.* TO 'vakcare_dev'@'localhost';

-- Step 4: Flush privileges to apply changes immediately
FLUSH PRIVILEGES;

-- Step 5: Verification queries
SELECT user, host, plugin FROM mysql.user WHERE user = 'vakcare_dev';
SHOW GRANTS FOR 'vakcare_dev'@'127.0.0.1';

