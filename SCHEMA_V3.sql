-- ═══════════════════════════════════════════════════════════════
-- FACULTY PERFORMANCE SYSTEM v3.0 — DATABASE SCHEMA UPDATE
-- Run this in Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- ── 1. USERS TABLE (with email_verified field) ──────────────────
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'faculty')),
    faculty_id TEXT,
    full_name TEXT,
    department TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- If users table already exists, add the email_verified column:
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Make existing users verified so they can still login:
UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL OR email_verified = FALSE;

-- ── 2. FACULTY TABLE ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS faculty (
    id BIGSERIAL PRIMARY KEY,
    faculty_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    designation TEXT,
    email TEXT,
    phone TEXT,
    hire_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── 3. PERFORMANCE TABLE ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS performance (
    id BIGSERIAL PRIMARY KEY,
    faculty_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    teaching_hours NUMERIC(5,2),
    student_feedback NUMERIC(3,2),
    teaching_rating NUMERIC(3,2),
    publications INTEGER DEFAULT 0,
    citations INTEGER DEFAULT 0,
    research_score NUMERIC(3,2),
    projects_completed INTEGER DEFAULT 0,
    experience_years INTEGER,
    students_mentored INTEGER DEFAULT 0,
    administration_score NUMERIC(3,2),
    overall_score NUMERIC(3,2),
    performance_category TEXT CHECK (
        performance_category IN ('Excellent', 'Good', 'Average', 'Needs Improvement')
    ),
    certifications JSONB,
    workshops JSONB,
    institutional_activities JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE,
    CONSTRAINT unique_faculty_year UNIQUE (faculty_id, year)
);

-- ── 4. INDEXES ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_faculty_faculty_id ON faculty(faculty_id);
CREATE INDEX IF NOT EXISTS idx_faculty_department ON faculty(department);
CREATE INDEX IF NOT EXISTS idx_performance_faculty_id ON performance(faculty_id);
CREATE INDEX IF NOT EXISTS idx_performance_year ON performance(year);

-- ── 5. AUTO-UPDATE TRIGGER ───────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_performance_updated_at ON performance;
CREATE TRIGGER update_performance_updated_at BEFORE UPDATE ON performance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── 6. USEFUL VIEWS ─────────────────────────────────────────
CREATE OR REPLACE VIEW faculty_summary AS
SELECT
    f.faculty_id, f.name, f.department, f.designation,
    COUNT(p.id) as total_records,
    ROUND(AVG(p.overall_score)::numeric, 2) as avg_overall_score,
    ROUND(AVG(p.teaching_rating)::numeric, 2) as avg_teaching_rating,
    ROUND(AVG(p.research_score)::numeric, 2) as avg_research_score,
    SUM(p.publications) as total_publications,
    SUM(p.citations) as total_citations
FROM faculty f
LEFT JOIN performance p ON f.faculty_id = p.faculty_id
GROUP BY f.faculty_id, f.name, f.department, f.designation;

-- ── 7. VERIFY ─────────────────────────────────────────────
SELECT 'Setup complete!' as message;
SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;
