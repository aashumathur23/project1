-- MySQL schema for the landing page (run this on your RDS instance).
CREATE DATABASE IF NOT EXISTS landingpage
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE landingpage;

CREATE TABLE IF NOT EXISTS leads (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  email      VARCHAR(150) NOT NULL,
  message    TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_leads_email (email)
);
