"""Shared SQLite CAS contract, independent of task-choice policy.

Enforces atomic ownership, one active task per agent, arrival/dependency guards
and bounded outcomes. It does NOT authenticate verifier results or eliminate
the shared-store failure domain. Candidate containers must never mount it.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid


@contextmanager
def _connection(path):
    """Commit/rollback AND close: sqlite3's context alone does not close."""
    db = sqlite3.connect(path, timeout=10)
    try:
        with db:
            yield db
    finally:
        db.close()


class ClaimStore:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError("Existing nonsymlink claim database required")

    @staticmethod
    def create(path, agents, tasks, *, max_attempts=2):
        path = Path(path)
        if path.exists() or not 1 <= len(agents) <= 4 or len(set(agents)) != len(agents) or max_attempts < 1:
            raise ValueError("New store, unique team <=4 and positive attempt bound required")
        if not tasks or len({t['task_id'] for t in tasks}) != len(tasks):
            raise ValueError("Unique nonempty task population required")
        ids = {t['task_id'] for t in tasks}
        for task in tasks:
            if (not set(task.get('dependencies', [])).issubset(ids)
                    or task['task_id'] in task.get('dependencies', [])
                    or task.get('release_ns', 0) < 0):
                raise ValueError("Invalid store dependency/arrival")
        parents = {t['task_id']: set(t.get('dependencies', [])) for t in tasks}
        visited, active = set(), set()

        def visit(task_id):
            if task_id in active:
                raise ValueError("Cyclic store dependencies")
            if task_id not in visited:
                active.add(task_id)
                for parent in parents[task_id]:
                    visit(parent)
                active.remove(task_id)
                visited.add(task_id)

        for task_id in ids:
            visit(task_id)
        with _connection(path) as db:
            db.executescript("""
                CREATE TABLE agents(id TEXT PRIMARY KEY, busy_task TEXT UNIQUE);
                CREATE TABLE tasks(id TEXT PRIMARY KEY, state TEXT NOT NULL, owner TEXT,
                    token TEXT UNIQUE, attempts INTEGER NOT NULL, release_ns INTEGER NOT NULL);
                CREATE TABLE dependencies(task TEXT NOT NULL, parent TEXT NOT NULL, PRIMARY KEY(task,parent));
                CREATE TABLE settings(max_attempts INTEGER NOT NULL);
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT, monotonic_ns INTEGER NOT NULL,
                    event TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TRIGGER no_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
                CREATE TRIGGER no_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
            """)
            db.executemany("INSERT INTO agents VALUES (?,NULL)", [(a,) for a in agents])
            db.executemany("INSERT INTO tasks VALUES (?,'READY',NULL,NULL,0,?)",
                           [(t['task_id'], t.get('release_ns', 0)) for t in tasks])
            db.executemany("INSERT INTO dependencies VALUES (?,?)",
                           [(t['task_id'], p) for t in tasks for p in t.get('dependencies', [])])
            db.execute("INSERT INTO settings VALUES (?)", (max_attempts,))
        return ClaimStore(path)

    @staticmethod
    def event(db, name, **fields):
        db.execute("INSERT INTO events(monotonic_ns,event,payload) VALUES (?,?,?)",
                   (time.monotonic_ns(), name, json.dumps(fields, sort_keys=True)))

    def claim(self, task_id, agent_id):
        with _connection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            agent = db.execute("SELECT busy_task FROM agents WHERE id=?", (agent_id,)).fetchone()
            task = db.execute("SELECT state,attempts,release_ns FROM tasks WHERE id=?", (task_id,)).fetchone()
            if agent is None or task is None:
                raise ValueError("Unknown task/agent")
            blocked = db.execute("""SELECT COUNT(*) FROM dependencies d JOIN tasks t ON d.parent=t.id
                                    WHERE d.task=? AND t.state!='VERIFIED'""", (task_id,)).fetchone()[0]
            reason = ("agent_busy" if agent[0] else "task_unavailable" if task[0] != "READY"
                      else "not_arrived" if time.monotonic_ns() < task[2]
                      else "dependencies_unverified" if blocked else None)
            if reason:
                self.event(db, "claim_rejected", task_id=task_id, agent_id=agent_id, reason=reason)
                return {"won": False, "reason": reason}
            token = uuid.uuid4().hex
            changed = db.execute("""UPDATE tasks SET state='CLAIMED',owner=?,token=?,attempts=attempts+1
                                    WHERE id=? AND state='READY'""", (agent_id, token, task_id)).rowcount
            if changed != 1:
                raise AssertionError("CAS lost within transaction")
            db.execute("UPDATE agents SET busy_task=? WHERE id=?", (task_id, agent_id))
            self.event(db, "claim_win", task_id=task_id, agent_id=agent_id, attempt=task[1]+1)
            return {"won": True, "task_id": task_id, "agent_id": agent_id, "token": token, "attempt": task[1]+1}

    def complete(self, claim, outcome, *, artifact=None):
        if outcome not in {"VERIFIED", "MODEL_FAILED", "PROVIDER_UNRESOLVED"}:
            raise ValueError("Unknown executor/verifier outcome")
        if outcome == "VERIFIED" and (not isinstance(artifact, str) or len(artifact) != 64
                                      or any(c not in "0123456789abcdef" for c in artifact)):
            raise ValueError("Verified artifact digest required")
        with _connection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state,owner,token,attempts FROM tasks WHERE id=?", (claim["task_id"],)).fetchone()
            if row is None or row[:3] != ("CLAIMED", claim["agent_id"], claim["token"]) or row[3] != claim["attempt"]:
                raise ValueError("Stale or forged completion")
            limit = db.execute("SELECT max_attempts FROM settings").fetchone()[0]
            state = ("VERIFIED" if outcome == "VERIFIED" else "UNSETTLED" if outcome == "PROVIDER_UNRESOLVED"
                     else "DEAD_LETTER" if row[3] >= limit else "READY")
            db.execute("UPDATE tasks SET state=?,owner=NULL,token=NULL WHERE id=?", (state, claim["task_id"]))
            db.execute("UPDATE agents SET busy_task=NULL WHERE id=?", (claim["agent_id"],))
            self.event(db, "execution_result", task_id=claim["task_id"], agent_id=claim["agent_id"],
                       outcome=outcome, task_state=state, artifact=artifact)

    def snapshot(self):
        with _connection(self.path) as db:
            return {"tasks": list(db.execute("SELECT id,state,owner,attempts FROM tasks ORDER BY id")),
                    "agents": list(db.execute("SELECT id,busy_task FROM agents ORDER BY id")),
                    "events": [{"sequence": s, "monotonic_ns": t, "event": e, **json.loads(p)}
                               for s,t,e,p in db.execute("SELECT seq,monotonic_ns,event,payload FROM events ORDER BY seq")]}
