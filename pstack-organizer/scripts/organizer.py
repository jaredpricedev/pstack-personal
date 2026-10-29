#!/usr/bin/env python3
"""Durable, offline project and task records for the pstack organizer plugin."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from datetime import date, datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4


SCHEMA_VERSION = 2
LEGACY_TABLES = ("apps", "tasks", "checkpoints", "reviews")
TABLES = (*LEGACY_TABLES, "notes")
CAPTURE_TABLES = ("tasks", "checkpoints", "reviews", "notes")
STATUSES = ("todo", "doing", "waiting", "blocked", "done", "cancelled")
KINDS = ("commitment", "idea")
PRIORITIES = ("low", "normal", "high")
NOTE_KINDS = ("fact", "decision", "context")
NOTE_STATUSES = ("current", "superseded", "archived")
FINISHED = ("done", "cancelled")
INACTIVE_STAGES = ("paused", "archived")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class InputError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError(message)


def text(value, label, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{label} must be a nonblank string")
    return value.strip()


def identifier(value, label="identifier"):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise InputError(f"{label} must use lowercase letters, digits, '-' or '_' (1-64 characters)")
    return value


def iso_date(value, label):
    if value is None:
        return None
    if not isinstance(value, str) or not DATE.fullmatch(value):
        raise InputError(f"{label} must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise InputError(f"{label} must be a valid date") from error
    return value


def url(value, label):
    if value is None:
        return None
    value = text(value, label)
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        parsed.port
    except ValueError as error:
        raise InputError(f"{label} must be a valid HTTP or HTTPS URL") from error
    if parsed.scheme not in ("http", "https") or not host:
        raise InputError(f"{label} must be an HTTP or HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise InputError(f"{label} must not contain credentials")
    if any(character.isspace() for character in value):
        raise InputError(f"{label} must not contain whitespace")
    return value


def strings(values, label, validator=None):
    if not isinstance(values, list):
        raise InputError(f"{label} must be a list")
    return [(validator or text)(value, label) for value in values]


def positive(value, label):
    if type(value) is not int or value < 1:
        raise InputError(f"{label} must be a positive integer")
    return value


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def checked_timestamp(value, label):
    value = text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InputError(f"{label} must be an ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError(f"{label} must include a timezone")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode(body, table):
    record = json.loads(body)
    if table == "tasks":
        record.setdefault("estimate_source", "default")
    return record


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def storage_paths(home, workspace):
    identifier(workspace, "workspace")
    home = Path(home).expanduser().resolve()
    code_root = Path(__file__).resolve().parents[1]
    repository = next((p for p in code_root.parents if (p / ".git").exists()), code_root)
    if inside(home, repository):
        raise InputError("Organizer data must be outside the plugin source repository; choose a private --home")
    directory = home / workspace
    if directory.is_symlink():
        raise InputError("Workspace directory must not be a symlink")
    db = directory / "state.sqlite3"
    if db.is_symlink():
        raise InputError("Workspace database must not be a symlink")
    return directory, db


def connect(db, readonly=False):
    if not db.is_file():
        raise InputError("Workspace is not initialized; run init with the same --home and --workspace")
    connection = sqlite3.connect(db.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        connection.close()
        if version == 1:
            raise InputError("Workspace schema 1 needs an upgrade; rerun init with the same --home and --workspace")
        raise InputError(f"Unsupported database schema {version}; expected {SCHEMA_VERSION}")
    return connection


def initialize(directory, db, workspace):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.is_dir():
        raise InputError("Workspace path must be a directory")
    try:
        descriptor = os.open(db, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except FileExistsError:
        pass
    with sqlite3.connect(str(db), timeout=15) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, SCHEMA_VERSION):
            raise InputError(f"Unsupported database schema {version}")
        if version == 0:
            if connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                raise InputError("Refusing to initialize a database containing unrelated tables")
            connection.execute("CREATE TABLE apps (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            connection.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, app_id TEXT REFERENCES apps(id), capture_key TEXT UNIQUE, request TEXT, body TEXT NOT NULL)")
            connection.execute("CREATE TABLE checkpoints (id TEXT PRIMARY KEY, app_id TEXT NOT NULL REFERENCES apps(id), capture_key TEXT UNIQUE, request TEXT, body TEXT NOT NULL)")
            connection.execute("CREATE TABLE reviews (id TEXT PRIMARY KEY, app_id TEXT NOT NULL REFERENCES apps(id), capture_key TEXT UNIQUE, request TEXT, body TEXT NOT NULL)")
        if version in (0, 1):
            connection.execute("CREATE TABLE notes (id TEXT PRIMARY KEY, app_id TEXT REFERENCES apps(id), supersedes TEXT REFERENCES notes(id) DEFERRABLE INITIALLY DEFERRED, capture_key TEXT UNIQUE, request TEXT, body TEXT NOT NULL)")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    if os.name != "nt":
        directory.chmod(0o700)
        db.chmod(0o600)
    return {"workspace": workspace, "path": str(db), "schema_version": SCHEMA_VERSION}


def records(connection, table):
    return [decode(row["body"], table) for row in connection.execute(f"SELECT body FROM {table} ORDER BY rowid")]


def get(connection, table, record_id):
    row = connection.execute(f"SELECT body FROM {table} WHERE id=?", (record_id,)).fetchone()
    if row is None:
        raise InputError(f"Unknown {table.rstrip('s')} {record_id!r}")
    return decode(row["body"], table)


def save(connection, table, record, request=None):
    if table == "apps":
        connection.execute("INSERT INTO apps (id,body) VALUES (?,?)", (record["id"], canonical(record)))
    elif table == "notes":
        connection.execute(
            "INSERT INTO notes (id,app_id,supersedes,capture_key,request,body) VALUES (?,?,?,?,?,?)",
            (record["id"], record["app_id"], record["supersedes"], record.get("key"), canonical(request) if request is not None else None, canonical(record)),
        )
    else:
        connection.execute(
            f"INSERT INTO {table} (id,app_id,capture_key,request,body) VALUES (?,?,?,?,?)",
            (record["id"], record["app_id"], record.get("key"), canonical(request) if request is not None else None, canonical(record)),
        )


def replace(connection, table, record):
    if table == "apps":
        connection.execute("UPDATE apps SET body=? WHERE id=?", (canonical(record), record["id"]))
    else:
        connection.execute(f"UPDATE {table} SET app_id=?,body=? WHERE id=?", (record["app_id"], canonical(record), record["id"]))


def existing_capture(connection, table, payload):
    key = payload.get("key")
    if key is not None:
        row = connection.execute(f"SELECT body,request FROM {table} WHERE capture_key=?", (key,)).fetchone()
        if row:
            if canonical(decode(row["request"], table)) != canonical(payload):
                raise InputError(f"Capture key {key!r} already identifies a different request; use an update or a new key")
            return decode(row["body"], table)
    return None


def keyed_capture(connection, table, payload, prefix):
    existing = existing_capture(connection, table, payload)
    if existing is not None:
        return existing
    current = timestamp()
    record = {"id": f"{prefix}-{uuid4().hex}", **payload, "created_at": current, "updated_at": current}
    save(connection, table, record, payload)
    return record


def validate_app(record):
    identifier(record["id"], "app ID")
    for key in ("name", "purpose", "stage"):
        record[key] = text(record[key], key)
    for key in ("path", "next_action"):
        record[key] = text(record[key], key, optional=True)
    record["repos"] = strings(record["repos"], "repo", url)
    for key in ("constraints", "verify", "maintenance"):
        record[key] = strings(record[key], key)
    return record


def app_payload(args, current=None):
    fields = {"name": None, "purpose": None, "repos": [], "path": None, "stage": "active", "next_action": None, "constraints": [], "verify": [], "maintenance": []}
    if current is not None:
        fields.update({key: current[key] for key in fields})
    mapping = {"repo": "repos", "constraint": "constraints"}
    for key in ("name", "purpose", "repo", "path", "stage", "next_action", "constraint", "verify", "maintenance"):
        value = getattr(args, key, None)
        if value is not None:
            fields[mapping.get(key, key)] = value
    return validate_app({"id": args.id, **fields})


def validate_task(record):
    identifier(record["id"], "task ID")
    if record["app_id"] is not None:
        identifier(record["app_id"], "app ID")
    for key in ("title", "source"):
        record[key] = text(record[key], key)
    for key in ("next_action", "waiting_on", "key"):
        record[key] = text(record[key], key, optional=True)
    if record["kind"] not in KINDS or record["status"] not in STATUSES or record["priority"] not in PRIORITIES:
        raise InputError("Invalid task kind, status or priority")
    record["due"] = iso_date(record["due"], "due")
    record["follow_up"] = iso_date(record["follow_up"], "follow-up")
    record["external"] = url(record["external"], "external")
    record["estimate"] = positive(record["estimate"], "estimate")
    if record["estimate_source"] not in ("default", "user"):
        raise InputError("Invalid estimate_source; expected default or user")
    record["depends_on"] = strings(record["depends_on"], "dependency", lambda value, _: identifier(value, "dependency"))
    if len(set(record["depends_on"])) != len(record["depends_on"]):
        raise InputError("Dependencies must not contain duplicate IDs")
    record["evidence"] = strings(record["evidence"], "evidence")
    if record["status"] == "done" and not record["evidence"]:
        raise InputError("Marking a task done requires --evidence describing the verified result")
    return record


def validate_graph(tasks):
    graph = {task["id"]: task["depends_on"] for task in tasks}
    visited, visiting = set(), set()

    def visit(task_id):
        if task_id in visiting:
            raise InputError("Task dependencies must not contain a cycle")
        if task_id in visited:
            return
        if task_id not in graph:
            raise InputError(f"Unknown dependency {task_id!r}")
        visiting.add(task_id)
        for dependency in graph[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)


def task_payload(args, current=None):
    payload = {"app_id": None, "title": None, "kind": "commitment", "status": "todo", "priority": "normal", "source": None, "next_action": None, "due": None, "follow_up": None, "waiting_on": None, "depends_on": [], "external": None, "key": None, "estimate": 30, "estimate_source": "default", "evidence": []}
    if current is not None:
        payload.update({key: current[key] for key in payload})
    for key in payload:
        value = getattr(args, "app" if key == "app_id" else key, None)
        if value is not None:
            payload[key] = value
    if getattr(args, "estimate", None) is not None:
        payload["estimate_source"] = "user"
    if getattr(args, "clear_due", False):
        if getattr(args, "due", None) is not None:
            raise InputError("Use --due or --clear-due, not both")
        payload["due"] = None
    if getattr(args, "clear_follow_up", False):
        if getattr(args, "follow_up", None) is not None:
            raise InputError("Use --follow-up or --clear-follow-up, not both")
        payload["follow_up"] = None
    probe = validate_task({"id": current["id"] if current else "task-validation", **payload})
    probe.pop("id")
    return probe


def check_app(connection, app_id):
    if app_id is not None:
        get(connection, "apps", app_id)


def validate_note(record, kind):
    identifier(record["id"], f"{kind} ID")
    identifier(record["app_id"], "app ID")
    record["summary"] = text(record["summary"], "summary")
    record["key"] = text(record["key"], "key", optional=True)
    record["evidence"] = strings(record["evidence"], "evidence")
    if kind == "checkpoint":
        record["next_action"] = text(record["next_action"], "next-action")
        for field in ("branch", "commit"):
            record[field] = text(record[field], field, optional=True)
        record["pr"] = url(record["pr"], "PR")
        record["decisions"] = strings(record["decisions"], "decision")
    else:
        record["findings"] = strings(record["findings"], "finding")
    return record


def validate_work_note(record):
    identifier(record["id"], "note ID")
    for field in ("title", "body", "source"):
        record[field] = text(record[field], field)
    if record["app_id"] is not None:
        identifier(record["app_id"], "app ID")
    if record["kind"] not in NOTE_KINDS or record["status"] not in NOTE_STATUSES:
        raise InputError("Invalid note kind or status")
    record["review_on"] = iso_date(record["review_on"], "review-on")
    if record["supersedes"] is not None:
        identifier(record["supersedes"], "superseded note ID")
    record["key"] = text(record["key"], "key", optional=True)
    return record


def validate_corrections(notes):
    by_id = {note["id"]: note for note in notes}
    successors = {}
    for note in notes:
        previous_id = note["supersedes"]
        if previous_id is None:
            continue
        previous = by_id.get(previous_id)
        if previous is None:
            raise InputError("Note correction references an unknown note")
        if previous["app_id"] != note["app_id"]:
            raise InputError("Note corrections must stay within the same app")
        if previous_id in successors:
            raise InputError("A note cannot have more than one correction")
        successors[previous_id] = note["id"]
        if previous["status"] == "current":
            raise InputError("A corrected note must be superseded or archived")
    for note in notes:
        if note["status"] == "superseded" and note["id"] not in successors:
            raise InputError("A superseded note must have a correction")
    visited = set()
    for note in notes:
        cursor = note["id"]
        chain = set()
        while cursor is not None and cursor not in visited:
            if cursor in chain:
                raise InputError("Note corrections must not contain a cycle")
            chain.add(cursor)
            cursor = by_id[cursor]["supersedes"]
        visited.update(chain)


def work_note_payload(args):
    payload = {
        "title": args.title,
        "body": args.body,
        "source": args.source,
        "kind": args.kind,
        "app_id": args.app,
        "review_on": args.review_on,
        "supersedes": args.supersedes,
        "status": "current",
        "key": args.key,
    }
    probe = validate_work_note({"id": "note-validation", **payload})
    probe.pop("id")
    return probe


def handle_work_note(connection, args):
    if args.action == "list":
        if args.app:
            check_app(connection, args.app)
        query = text(args.query, "query").casefold() if args.query is not None else None
        return [
            note for note in records(connection, "notes")
            if note["status"] == args.status
            and (not args.app or note["app_id"] == args.app)
            and (not args.kind or note["kind"] == args.kind)
            and (query is None or query in "\n".join(note[field] for field in ("title", "body", "source")).casefold())
        ]
    if args.action == "show":
        return get(connection, "notes", args.id)
    if args.action == "archive":
        note = get(connection, "notes", args.id)
        if note["status"] != "archived":
            note = {**note, "status": "archived", "updated_at": timestamp()}
            replace(connection, "notes", note)
        return note
    payload = work_note_payload(args)
    check_app(connection, payload["app_id"])
    existing = existing_capture(connection, "notes", payload)
    if existing is not None:
        return existing
    previous = None
    if payload["supersedes"] is not None:
        previous = get(connection, "notes", payload["supersedes"])
        if previous["status"] != "current":
            raise InputError("Only a current note can be superseded; correct its latest current successor")
        if previous["app_id"] != payload["app_id"]:
            raise InputError("Note corrections must stay within the same app")
    note = keyed_capture(connection, "notes", payload, "note")
    if previous is not None:
        replace(connection, "notes", {**previous, "status": "superseded", "updated_at": note["created_at"]})
    return note


def latest(items, app_id):
    candidates = [item for item in items if item["app_id"] == app_id]
    return max(candidates, key=lambda item: (item["created_at"], item["id"]), default=None)


def today(connection, args, workspace):
    day = iso_date(args.date, "date") if args.date else date.today().isoformat()
    limit = positive(args.limit, "limit")
    budget = positive(args.minutes, "minutes") if args.minutes is not None else None
    tasks = records(connection, "tasks")
    apps = records(connection, "apps")
    app_by_id = {app["id"]: app for app in apps}
    task_by_id = {task["id"]: task for task in tasks}
    commitments = [task for task in tasks if task["kind"] == "commitment" and task["status"] not in FINISHED]
    overdue = [task for task in commitments if task["due"] is not None and task["due"] < day]
    follow_ups = [task for task in commitments if task["status"] in ("waiting", "blocked") and task["follow_up"] is not None and task["follow_up"] <= day]
    priority_rank = {"high": 0, "normal": 1, "low": 2}

    def sort_key(task):
        return (0 if task["due"] and task["due"] <= day else 1, task["due"] or "9999-12-31", 0 if task["status"] == "doing" else 1, priority_rank[task["priority"]], task["created_at"], task["id"])

    picked, deferred = [], []
    spent = 0
    for task in sorted(commitments, key=sort_key):
        app = app_by_id.get(task["app_id"])
        reason = None
        if app and app["stage"].lower() in INACTIVE_STAGES:
            reason = f"App is {app['stage']}"
        elif task["status"] in ("waiting", "blocked"):
            reason = f"Task is {task['status']}"
        elif any(task_by_id[dependency]["status"] != "done" for dependency in task["depends_on"]):
            reason = "Unfinished dependencies"
        elif len(picked) >= limit:
            reason = "Daily item limit"
        elif budget is not None and spent + task["estimate"] > budget:
            reason = "Does not fit the remaining time budget"
        if reason:
            deferred.append({**task, "reason": reason})
            continue
        if task["due"] and task["due"] < day:
            reason = f"Overdue since {task['due']}"
        elif task["due"] == day:
            reason = "Due today"
        elif task["status"] == "doing":
            reason = "Already in progress"
        elif task["priority"] == "high":
            reason = "High priority"
        elif task["due"]:
            reason = f"Upcoming deadline {task['due']}"
        else:
            reason = "Oldest ready commitment at this priority"
        picked.append({**task, "reason": reason})
        spent += task["estimate"]

    checkpoints, reviews = records(connection, "checkpoints"), records(connection, "reviews")
    stale = []
    for app in apps:
        if app["stage"].lower() in INACTIVE_STAGES:
            continue
        notes = [item for item in checkpoints + reviews if item["app_id"] == app["id"]]
        last_record = max(notes, key=lambda item: item["created_at"], default=None)
        if last_record is None:
            stale.append({**app, "reason": "No recorded checkpoint or maintenance review"})
        else:
            last_day = datetime.fromisoformat(last_record["created_at"].replace("Z", "+00:00")).date()
            age = (date.fromisoformat(day) - last_day).days
            if age >= 14:
                stale.append({**app, "reason": f"Last checkpoint or review was {age} days ago"})
    return {"date": day, "workspace": workspace, "picked": picked, "overdue": sorted(overdue, key=sort_key), "follow_ups": sorted(follow_ups, key=sort_key), "deferred": deferred, "idea_count": sum(task["kind"] == "idea" and task["status"] not in FINISHED for task in tasks), "stale_projects": stale}


def morning(connection, args):
    plan = today(connection, args, args.workspace)
    tasks = records(connection, "tasks")
    checkpoints = records(connection, "checkpoints")
    reviews = records(connection, "reviews")
    apps = [
        {
            "app": app,
            "checkpoint": latest(checkpoints, app["id"]),
            "review": latest(reviews, app["id"]),
            "open_task_count": sum(task["app_id"] == app["id"] and task["status"] not in FINISHED for task in tasks),
        }
        for app in records(connection, "apps")
    ]
    notes = [note for note in records(connection, "notes") if note["status"] == "current" and note["review_on"] is not None and note["review_on"] <= plan["date"]]
    return {
        "workspace": args.workspace,
        "date": plan["date"],
        "coverage": "ledger-only",
        "plan": plan,
        "apps": apps,
        "notes_to_review": sorted(notes, key=lambda note: (note["review_on"], note["created_at"], note["id"])),
    }


def export_snapshot(connection, workspace):
    captures = {
        table: {
            row["capture_key"]: decode(row["request"], table)
            for row in connection.execute(f"SELECT capture_key,request FROM {table} WHERE capture_key IS NOT NULL")
        }
        for table in CAPTURE_TABLES
    }
    return {"schema_version": SCHEMA_VERSION, "workspace": workspace, "exported_at": timestamp(), **{table: records(connection, table) for table in TABLES}, "capture_requests": captures}


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or type(snapshot.get("schema_version")) is not int or snapshot["schema_version"] not in (1, SCHEMA_VERSION):
        raise InputError("Import must be an organizer export with schema_version 1 or 2")
    importing_v1 = snapshot["schema_version"] == 1
    tables = LEGACY_TABLES if importing_v1 else TABLES
    capture_tables = CAPTURE_TABLES[:-1] if importing_v1 else CAPTURE_TABLES
    expected = {"schema_version", "workspace", "exported_at", "capture_requests", *tables}
    if set(snapshot) != expected:
        raise InputError("Import contains missing or unknown top-level fields")
    identifier(snapshot["workspace"], "export workspace")
    checked_timestamp(snapshot["exported_at"], "exported_at")
    app_fields = {"id", "name", "purpose", "repos", "path", "stage", "next_action", "constraints", "verify", "maintenance", "created_at", "updated_at"}
    task_fields = {"id", "app_id", "title", "kind", "status", "priority", "source", "next_action", "due", "follow_up", "waiting_on", "depends_on", "external", "key", "estimate", "estimate_source", "evidence", "created_at", "updated_at"}
    checkpoint_fields = {"id", "app_id", "summary", "next_action", "branch", "commit", "pr", "evidence", "decisions", "key", "created_at", "updated_at"}
    review_fields = {"id", "app_id", "summary", "findings", "evidence", "key", "created_at", "updated_at"}
    work_note_fields = {"id", "title", "body", "kind", "app_id", "source", "review_on", "supersedes", "status", "key", "created_at", "updated_at"}
    fields = dict(zip(TABLES, (app_fields, task_fields, checkpoint_fields, review_fields, work_note_fields)))
    for table in tables:
        if not isinstance(snapshot[table], list):
            raise InputError(f"Import {table} must be an array")
        seen, keys = set(), set()
        for record in snapshot[table]:
            if not isinstance(record, dict) or set(record) != fields[table]:
                raise InputError(f"Import {table} record contains missing or unknown fields")
            if table == "apps":
                validate_app(record)
            elif table == "tasks":
                validate_task(record)
            elif table == "notes":
                validate_work_note(record)
            else:
                validate_note(record, "checkpoint" if table == "checkpoints" else "review")
            for field in ("created_at", "updated_at"):
                checked_timestamp(record[field], field)
            if datetime.fromisoformat(record["updated_at"].replace("Z", "+00:00")) < datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")):
                raise InputError("Import updated_at must not precede created_at")
            if record["id"] in seen:
                raise InputError(f"Import contains duplicate {table} ID {record['id']!r}")
            seen.add(record["id"])
            if record.get("key") is not None:
                if record["key"] in keys:
                    raise InputError(f"Import contains duplicate {table} capture key")
                keys.add(record["key"])
    app_ids = {record["id"] for record in snapshot["apps"]}
    for table in capture_tables:
        for record in snapshot[table]:
            if record["app_id"] is not None and record["app_id"] not in app_ids:
                raise InputError(f"Import {table} references an unknown app")
    validate_graph(snapshot["tasks"])
    if not importing_v1:
        validate_corrections(snapshot["notes"])
    captures = snapshot["capture_requests"]
    if not isinstance(captures, dict) or set(captures) != set(capture_tables):
        raise InputError("Import capture_requests must match the export schema's record tables")
    for table in capture_tables:
        requests = captures[table]
        expected_keys = {record["key"] for record in snapshot[table] if record["key"] is not None}
        if not isinstance(requests, dict) or set(requests) != expected_keys:
            raise InputError(f"Import capture_requests keys do not match keyed {table}")
        for key, request in requests.items():
            request_fields = fields[table] - {"id", "created_at", "updated_at"}
            if not isinstance(request, dict) or set(request) != request_fields or request["key"] != key:
                raise InputError(f"Invalid original capture request for {table}")
            probe = {"id": "capture-validation", **request}
            if table == "tasks":
                validate_task(probe)
            elif table == "notes":
                validate_work_note(probe)
                captured = next(record for record in snapshot["notes"] if record["key"] == key)
                immutable_fields = request_fields - {"status"}
                if probe["status"] != "current" or any(probe[field] != captured[field] for field in immutable_fields):
                    raise InputError("Original note capture request must preserve its immutable content")
            else:
                validate_note(probe, "checkpoint" if table == "checkpoints" else "review")
            if probe["app_id"] is not None and probe["app_id"] not in app_ids:
                raise InputError("Original capture request references an unknown app")
            if table == "tasks" and any(dependency not in {task["id"] for task in snapshot["tasks"]} for dependency in probe["depends_on"]):
                raise InputError("Original capture request references an unknown task")
    if importing_v1:
        snapshot["notes"] = []
        snapshot["capture_requests"]["notes"] = {}
        snapshot["schema_version"] = SCHEMA_VERSION
    return snapshot


def import_snapshot(connection, args, workspace):
    if any(connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in TABLES):
        raise InputError("Import requires an empty workspace; use a new --workspace rather than overwriting records")
    try:
        with Path(args.file).expanduser().open(encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except (OSError, ValueError) as error:
        raise InputError(f"Cannot read organizer export: {error}") from error
    snapshot = validate_snapshot(snapshot)
    for table in TABLES:
        for record in snapshot[table]:
            payload = {key: value for key, value in record.items() if key not in ("id", "created_at", "updated_at")}
            if table != "apps" and record["key"] is not None:
                payload = snapshot["capture_requests"][table][record["key"]]
            save(connection, table, record, payload)
    return {"workspace": workspace, "imported": {table: len(snapshot[table]) for table in TABLES}}


def handle(connection, args):
    if args.command == "note":
        return handle_work_note(connection, args)
    if args.command == "app":
        if args.action == "list":
            return records(connection, "apps")
        if args.action == "show":
            return get(connection, "apps", args.id)
        if args.action == "add":
            payload = app_payload(args)
            existing = connection.execute("SELECT body FROM apps WHERE id=?", (args.id,)).fetchone()
            if existing:
                current = json.loads(existing["body"])
                if payload != {key: value for key, value in current.items() if key not in ("created_at", "updated_at")}:
                    raise InputError("App ID already exists with different fields; use app update")
                return current
            now = timestamp()
            record = {**payload, "created_at": now, "updated_at": now}
            save(connection, "apps", record)
            return record
        current = get(connection, "apps", args.id)
        record = {**app_payload(args, current), "created_at": current["created_at"], "updated_at": timestamp()}
        replace(connection, "apps", record)
        return record
    if args.command == "task":
        if args.action == "list":
            if args.app:
                check_app(connection, args.app)
            return [task for task in records(connection, "tasks") if (not args.app or task["app_id"] == args.app) and (not args.status or task["status"] == args.status) and (not args.kind or task["kind"] == args.kind)]
        if args.action == "show":
            return get(connection, "tasks", args.id)
        current = get(connection, "tasks", args.id) if args.action == "update" else None
        payload = task_payload(args, current)
        check_app(connection, payload["app_id"])
        if current:
            if payload["key"] != current["key"]:
                raise InputError("Capture keys cannot be changed; omit --key when updating")
            record = {"id": current["id"], **payload, "created_at": current["created_at"], "updated_at": timestamp()}
            tasks = [record if task["id"] == record["id"] else task for task in records(connection, "tasks")]
            validate_graph(tasks)
            replace(connection, "tasks", record)
            return record
        for dependency in payload["depends_on"]:
            get(connection, "tasks", dependency)
        return keyed_capture(connection, "tasks", payload, "task")
    if args.command in ("checkpoint", "review"):
        check_app(connection, args.app)
        payload = {"app_id": args.app, "summary": args.summary, "key": args.key, "evidence": args.evidence or []}
        if args.command == "checkpoint":
            payload.update(next_action=args.next_action, branch=args.branch, commit=args.commit, pr=args.pr, decisions=args.decision or [])
        else:
            payload["findings"] = args.finding or []
        probe = validate_note({"id": f"{args.command}-validation", **payload}, args.command)
        probe.pop("id")
        return keyed_capture(connection, "checkpoints" if args.command == "checkpoint" else "reviews", probe, args.command)
    if args.command == "resume":
        app = get(connection, "apps", args.app)
        return {"app": app, "checkpoint": latest(records(connection, "checkpoints"), args.app), "tasks": [task for task in records(connection, "tasks") if task["app_id"] == args.app and task["status"] not in FINISHED], "review": latest(records(connection, "reviews"), args.app)}
    if args.command == "today":
        return today(connection, args, args.workspace)
    if args.command == "morning":
        return morning(connection, args)
    if args.command == "export":
        return export_snapshot(connection, args.workspace)
    if args.command == "import":
        return import_snapshot(connection, args, args.workspace)
    raise InputError("Unknown command")


def add_app_arguments(parser, required=False):
    parser.add_argument("id")
    parser.add_argument("--name", required=required)
    parser.add_argument("--purpose", required=required)
    for option in ("repo", "constraint", "verify", "maintenance"):
        parser.add_argument(f"--{option}", action="append")
    for option in ("path", "stage", "next-action"):
        parser.add_argument(f"--{option}")


def add_task_arguments(parser, update=False):
    parser.add_argument("id" if update else "title")
    if update:
        parser.add_argument("--title")
    for option in ("app", "source", "next-action", "due", "follow-up", "waiting-on", "external", "key"):
        parser.add_argument(f"--{option}", required=option == "source" and not update)
    parser.add_argument("--kind", choices=KINDS)
    parser.add_argument("--status", choices=STATUSES if update else STATUSES[:4])
    parser.add_argument("--priority", choices=PRIORITIES)
    parser.add_argument("--estimate", type=int)
    parser.add_argument("--depends-on", action="append")
    if update:
        parser.add_argument("--clear-due", action="store_true")
        parser.add_argument("--clear-follow-up", action="store_true")
        parser.add_argument("--evidence", action="append")


def build_parser():
    parser = Parser(description=__doc__, epilog="All state stays in the selected local workspace. No commands execute verification instructions or contact a remote service.")
    parser.add_argument("--home", default=os.environ.get("PSTACK_ORGANIZER_HOME", str(Path.home() / ".local" / "share" / "pstack-organizer")), help="Private state directory; defaults to PSTACK_ORGANIZER_HOME or ~/.local/share/pstack-organizer")
    parser.add_argument("--workspace", default=os.environ.get("PSTACK_ORGANIZER_WORKSPACE", "personal"), help="Isolated workspace ID (default: personal)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize or upgrade a workspace; safe to repeat")
    app = commands.add_parser("app", help="Manage the app registry").add_subparsers(dest="action", required=True)
    add_app_arguments(app.add_parser("add"), required=True)
    add_app_arguments(app.add_parser("update"))
    app.add_parser("list")
    app.add_parser("show").add_argument("id")
    task = commands.add_parser("task", help="Capture and update commitments and ideas").add_subparsers(dest="action", required=True)
    add_task_arguments(task.add_parser("add"))
    add_task_arguments(task.add_parser("update"), update=True)
    task_list = task.add_parser("list")
    task_list.add_argument("--app")
    task_list.add_argument("--status", choices=STATUSES)
    task_list.add_argument("--kind", choices=KINDS)
    task.add_parser("show").add_argument("id")
    note = commands.add_parser("note", help="Keep durable work context and append-only corrections").add_subparsers(dest="action", required=True)
    note_add = note.add_parser("add")
    note_add.add_argument("title")
    note_add.add_argument("--body", required=True)
    note_add.add_argument("--source", required=True)
    note_add.add_argument("--kind", choices=NOTE_KINDS, default="context")
    for option in ("app", "review-on", "supersedes", "key"):
        note_add.add_argument(f"--{option}")
    note_list = note.add_parser("list")
    note_list.add_argument("--app")
    note_list.add_argument("--kind", choices=NOTE_KINDS)
    note_list.add_argument("--query")
    note_list.add_argument("--status", choices=NOTE_STATUSES, default="current")
    note.add_parser("show").add_argument("id")
    note.add_parser("archive").add_argument("id")
    for kind in ("checkpoint", "review"):
        action = commands.add_parser(kind).add_subparsers(dest="action", required=True).add_parser("add")
        action.add_argument("app")
        action.add_argument("--summary", required=True)
        action.add_argument("--key")
        action.add_argument("--evidence", action="append")
        if kind == "checkpoint":
            action.add_argument("--next-action", required=True)
            for option in ("branch", "commit", "pr"):
                action.add_argument(f"--{option}")
            action.add_argument("--decision", action="append")
        else:
            action.add_argument("--finding", action="append")
    commands.add_parser("resume").add_argument("app")
    for command, description in (("today", "Choose a small worklist without changing tasks"), ("morning", "Read the daily worklist, app handoffs and notes needing review")):
        daily = commands.add_parser(command, help=description)
        daily.add_argument("--date")
        daily.add_argument("--limit", type=int, default=3)
        daily.add_argument("--minutes", type=int)
    commands.add_parser("export", help="Write a versioned JSON snapshot to stdout; store it privately")
    commands.add_parser("import", help="Restore a JSON snapshot into an initialized, empty workspace").add_argument("--file", required=True)
    return parser


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
        directory, db = storage_paths(args.home, args.workspace)
        if args.command == "init":
            result = initialize(directory, db, args.workspace)
        else:
            readonly = args.command in ("resume", "today", "morning", "export") or args.command in ("app", "task", "note") and args.action in ("list", "show")
            connection = connect(db, readonly)
            try:
                connection.execute("BEGIN" if readonly else "BEGIN IMMEDIATE")
                result = handle(connection, args)
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (InputError, OSError, sqlite3.Error, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
