"""Database schema — users, orgs, memberships, sessions, audit logs.

Mirrors PostgreSQL design but runs on SQLite for dev. Zero-cost migration path.
All foreign keys use ON DELETE CASCADE for clean referential integrity.
"""

SCHEMA_SQL = """
-- Users: local account linked to GitHub identity
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    login TEXT NOT NULL,
    name TEXT,
    email TEXT,
    avatar_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Organizations (GitHub org or local team)
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github_org_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- User membership in organization with role
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member'
        CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, org_id)
);

-- User sessions (JWT refresh tokens stored server-side)
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- API keys for CI/CD (scoped, revocable)
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    scopes TEXT NOT NULL DEFAULT 'read:review',
    last_used_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    revoked_at TEXT
);

-- Encrypted GitHub OAuth tokens (stored separately from user row for security)
CREATE TABLE IF NOT EXISTS github_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    access_token TEXT NOT NULL,
    token_type TEXT DEFAULT 'bearer',
    scopes TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Audit log: every action recorded for compliance
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    org_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL DEFAULT '',
    details TEXT DEFAULT '',
    ip_address TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Repository configuration per organization
CREATE TABLE IF NOT EXISTS repo_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    auto_review BOOLEAN DEFAULT FALSE,
    min_confidence REAL DEFAULT 0.65,
    max_comments INTEGER DEFAULT 10,
    UNIQUE(org_id, owner, repo)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);
CREATE INDEX IF NOT EXISTS idx_users_login ON users(login);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(org_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_github_tokens_user ON github_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_repo_configs_org ON repo_configs(org_id);
"""

# In-memory cache for frequently accessed data (SQLite-backed, no Redis needed for MVP)
CACHE_TTL_SECONDS = 300
