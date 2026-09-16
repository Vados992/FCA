PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS objects(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, version INTEGER NOT NULL,
  payload TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL, actor TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS objects_kind ON objects(kind, created_at, id);
CREATE TABLE IF NOT EXISTS object_refs(
  object_id TEXT NOT NULL REFERENCES objects(id), target_id TEXT NOT NULL REFERENCES objects(id),
  PRIMARY KEY(object_id,target_id)
);
CREATE INDEX IF NOT EXISTS refs_target ON object_refs(target_id);
CREATE TABLE IF NOT EXISTS audit_events(
  sequence INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT NOT NULL, details TEXT NOT NULL,
  previous_hash TEXT NOT NULL, hash TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS immutable_objects_update BEFORE UPDATE ON objects
BEGIN SELECT RAISE(ABORT,'immutable object: create a new version'); END;
CREATE TRIGGER IF NOT EXISTS immutable_objects_delete BEFORE DELETE ON objects
BEGIN SELECT RAISE(ABORT,'immutable object: deletion prohibited'); END;
CREATE TRIGGER IF NOT EXISTS immutable_refs_update BEFORE UPDATE ON object_refs
BEGIN SELECT RAISE(ABORT,'immutable reference'); END;
CREATE TRIGGER IF NOT EXISTS immutable_refs_delete BEFORE DELETE ON object_refs
BEGIN SELECT RAISE(ABORT,'immutable reference'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT,'immutable audit event'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT,'immutable audit event'); END;
