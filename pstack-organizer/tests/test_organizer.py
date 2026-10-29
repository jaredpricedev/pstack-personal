"""Exercise the organizer as a CLI across independent processes and workspaces."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "organizer.py"


class OrganizerCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pstack-organizer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.home = self.directory / "state"
        self.run_cli("init")

    def invoke(self, *arguments, workspace="personal", home=None):
        environment = os.environ.copy()
        environment.pop("PSTACK_ORGANIZER_HOME", None)
        environment.pop("PSTACK_ORGANIZER_WORKSPACE", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(home or self.home),
             "--workspace", workspace, *map(str, arguments)],
            text=True, capture_output=True, env=environment, timeout=30,
        )

    def run_cli(self, *arguments, **options):
        result = self.invoke(*arguments, **options)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def reject(self, *arguments, **options):
        result = self.invoke(*arguments, **options)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertIsInstance(error.get("error"), str)
        self.assertTrue(error["error"].strip())
        return error

    def app(self, identifier="demo", *arguments):
        return self.run_cli("app", "add", identifier, "--name", identifier.title(),
                            "--purpose", "Maintain the demo service", *arguments)

    def task(self, title="Do the next thing", *arguments, **options):
        return self.run_cli("task", "add", title, "--source", "User request", *arguments,
                            **options)

    def write_snapshot(self, snapshot):
        path = self.directory / "snapshot.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    def test_init_is_idempotent_and_read_does_not_create_missing_store(self):
        first = self.run_cli("init")
        second = self.run_cli("init")
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], 1)
        missing_home = self.directory / "missing"
        self.reject("task", "list", home=missing_home)
        self.assertFalse(missing_home.exists())
        self.assertEqual(self.run_cli("app", "list"), [])

    def test_app_updates_preserve_unmentioned_fields_across_processes(self):
        self.app("demo", "--repo", "https://github.com/example/demo",
                 "--constraint", "Use a disposable lab", "--verify", "Run smoke checks",
                 "--maintenance", "Review dependency updates", "--next-action", "Test startup")
        self.run_cli("app", "update", "demo", "--stage", "maintenance")
        app = self.run_cli("app", "show", "demo")
        self.assertEqual(app["stage"], "maintenance")
        self.assertEqual(app["repos"], ["https://github.com/example/demo"])
        self.assertEqual(app["constraints"], ["Use a disposable lab"])
        self.assertEqual(app["verify"], ["Run smoke checks"])
        self.assertEqual(app["maintenance"], ["Review dependency updates"])
        self.assertEqual(app["next_action"], "Test startup")

    def test_workspaces_isolate_projects_and_tasks(self):
        self.app()
        personal = self.task("Personal obligation", "--app", "demo")
        self.run_cli("init", workspace="work")
        work = self.task("Work obligation", workspace="work")
        self.assertEqual(self.run_cli("app", "list", workspace="work"), [])
        self.assertEqual([row["id"] for row in self.run_cli("task", "list")], [personal["id"]])
        self.assertEqual([row["id"] for row in self.run_cli("task", "list", workspace="work")],
                         [work["id"]])
        self.reject("task", "show", personal["id"], workspace="work")

    def test_general_work_tasks_need_no_app_and_filters_do_not_change_records(self):
        standalone = self.task("Ask the architect")
        self.app()
        idea = self.task("Explore a possible improvement", "--app", "demo", "--kind", "idea")
        self.assertIsNone(standalone["app_id"])
        self.assertEqual([t["id"] for t in self.run_cli("task", "list", "--kind", "idea")],
                         [idea["id"]])
        self.assertEqual([t["id"] for t in self.run_cli("task", "list", "--app", "demo")],
                         [idea["id"]])
        self.assertEqual(len(self.run_cli("task", "list")), 2)

    def test_missing_app_and_invalid_inputs_do_not_leave_partial_tasks(self):
        self.reject("task", "add", "A commitment needs its source")
        self.reject("task", "add", "Unlinked task", "--source", "Request", "--app", "unknown")
        for invalid in ("2026-02-30", "tomorrow", "2026-13-01"):
            with self.subTest(due=invalid):
                self.reject("task", "add", "Bad date", "--source", "Request", "--due", invalid)
        self.reject("task", "add", " ", "--source", "Request")
        self.reject("task", "add", "Bad estimate", "--source", "Request", "--estimate", "-1")
        self.assertEqual(self.run_cli("task", "list"), [])

    def test_invalid_ids_and_credential_urls_are_rejected(self):
        for identifier in ("../outside", "a/b", ".."):
            with self.subTest(identifier=identifier):
                self.reject("init", workspace=identifier)
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://secret:token@example.com/repo"):
            with self.subTest(url=url):
                self.reject("app", "add", "bad", "--name", "Bad", "--purpose", "Demo", "--repo", url)
        self.assertEqual(self.run_cli("app", "list"), [])

    def test_capture_retry_deduplicates_without_overwriting_later_progress(self):
        original = self.task("Review the change", "--key", "review-request-1")
        self.assertEqual(original["id"], self.task("Review the change", "--key", "review-request-1")["id"])
        self.run_cli("task", "update", original["id"], "--status", "doing")
        self.task("Review the change", "--key", "review-request-1")
        self.assertEqual(self.run_cli("task", "show", original["id"])["status"], "doing")
        self.reject("task", "add", "A different request", "--source", "User request",
                    "--key", "review-request-1")
        self.assertEqual(len(self.run_cli("task", "list")), 1)

    def test_done_requires_evidence_and_preserves_other_fields(self):
        task = self.task("Verify the lab", "--due", "2026-10-30", "--next-action", "Run smoke checks")
        self.reject("task", "update", task["id"], "--status", "done")
        self.assertEqual(self.run_cli("task", "show", task["id"])["status"], "todo")
        done = self.run_cli("task", "update", task["id"], "--status", "done", "--evidence",
                            "Smoke checks passed in the disposable lab")
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["due"], "2026-10-30")
        self.assertEqual(done["next_action"], "Run smoke checks")
        self.assertIn("Smoke checks passed in the disposable lab", done["evidence"])

    def test_dates_can_be_cleared_without_changing_other_fields(self):
        task = self.task("Follow up", "--due", "2026-10-30", "--follow-up", "2026-10-29")
        updated = self.run_cli("task", "update", task["id"], "--clear-due", "--clear-follow-up")
        self.assertIsNone(updated["due"])
        self.assertIsNone(updated["follow_up"])
        self.assertEqual(updated["source"], "User request")

    def test_dependency_validation_blocks_missing_tasks_and_cycles(self):
        self.reject("task", "add", "Needs a missing task", "--source", "Request",
                    "--depends-on", "task-not-present")
        first = self.task("First dependency")
        second = self.task("Second dependency", "--depends-on", first["id"])
        self.reject("task", "update", first["id"], "--depends-on", second["id"])
        self.reject("task", "update", first["id"], "--depends-on", first["id"])
        self.assertEqual(self.run_cli("task", "show", first["id"])["depends_on"], [])

    def test_checkpoint_resume_preserves_decisions_evidence_and_open_tasks(self):
        self.app()
        open_task = self.task("Finish smoke tests", "--app", "demo")
        closed_task = self.task("Old task", "--app", "demo")
        self.run_cli("task", "update", closed_task["id"], "--status", "cancelled")
        checkpoint = self.run_cli("checkpoint", "add", "demo", "--summary", "Startup fixed",
                                  "--next-action", "Run smoke tests", "--branch", "fix/startup",
                                  "--commit", "abcdef123", "--pr", "https://github.com/example/demo/pull/1",
                                  "--evidence", "Startup test passes", "--decision", "Retain manual deployment",
                                  "--key", "session-1")
        resumed = self.run_cli("resume", "demo")
        self.assertEqual(resumed["app"]["id"], "demo")
        self.assertEqual(resumed["checkpoint"]["id"], checkpoint["id"])
        self.assertEqual(resumed["checkpoint"]["next_action"], "Run smoke tests")
        self.assertEqual(resumed["checkpoint"]["decisions"], ["Retain manual deployment"])
        self.assertEqual([t["id"] for t in resumed["tasks"]], [open_task["id"]])
        self.assertIsNone(resumed["review"])

    def test_checkpoint_retry_does_not_duplicate_and_latest_review_is_returned(self):
        self.app()
        args = ("checkpoint", "add", "demo", "--summary", "Stopped after validation",
                "--next-action", "Review the diff", "--key", "session-2")
        checkpoint = self.run_cli(*args)
        self.assertEqual(self.run_cli(*args)["id"], checkpoint["id"])
        self.run_cli("review", "add", "demo", "--summary", "Initial review", "--finding", "Inspect CI")
        review = self.run_cli("review", "add", "demo", "--summary", "Current review",
                              "--finding", "CI passed", "--evidence", "Build 42")
        self.assertEqual(self.run_cli("resume", "demo")["review"]["id"], review["id"])
        self.assertEqual(len(self.run_cli("export")["checkpoints"]), 1)

    def test_today_only_picks_ready_commitments_and_is_read_only(self):
        self.app("active")
        self.app("paused", "--stage", "paused")
        self.app("archived", "--stage", "archived")
        ready = self.task("Ready commitment", "--app", "active", "--due", "2026-10-27")
        dependency = self.task("Unfinished dependency", "--kind", "idea")
        excluded = [
            self.task("An idea", "--kind", "idea", "--due", "2026-10-26"),
            self.task("Waiting", "--status", "waiting", "--follow-up", "2026-10-28"),
            self.task("Blocked", "--status", "blocked"),
            self.task("Paused app", "--app", "paused"),
            self.task("Archived app", "--app", "archived"),
            self.task("Has an unmet dependency", "--depends-on", dependency["id"]),
        ]
        completed = self.task("Already finished")
        self.run_cli("task", "update", completed["id"], "--status", "done", "--evidence", "Verified")
        before = self.run_cli("task", "list")
        report = self.run_cli("today", "--date", "2026-10-28", "--limit", "10")
        self.assertEqual([t["id"] for t in report["picked"]], [ready["id"]])
        self.assertTrue(all(t["reason"] for t in report["picked"]))
        excluded_ids = {t["id"] for t in excluded} | {dependency["id"], completed["id"]}
        self.assertFalse(excluded_ids & {t["id"] for t in report["picked"]})
        self.assertEqual(report["idea_count"], 2)
        self.assertEqual(before, self.run_cli("task", "list"))

    def test_today_lists_every_overdue_item_even_when_limit_is_small(self):
        overdue = [self.task("Overdue %d" % i, "--due", "2026-10-20") for i in range(5)]
        report = self.run_cli("today", "--date", "2026-10-28", "--limit", "1")
        self.assertEqual(len(report["picked"]), 1)
        self.assertEqual({t["id"] for t in report["overdue"]}, {t["id"] for t in overdue})
        self.assertEqual(len(report["deferred"]), 4)
        self.assertEqual(report, self.run_cli("today", "--date", "2026-10-28", "--limit", "1"))

    def test_followups_surface_without_pretending_waiting_work_is_ready(self):
        due = self.task("Ask for an update", "--status", "waiting", "--waiting-on", "Architecture review",
                        "--follow-up", "2026-10-28")
        future = self.task("Wait until next week", "--status", "waiting", "--follow-up", "2026-11-02")
        blocked = self.task("Escalate blocker", "--status", "blocked", "--follow-up", "2026-10-27")
        report = self.run_cli("today", "--date", "2026-10-28")
        self.assertEqual(report["picked"], [])
        self.assertEqual({t["id"] for t in report["follow_ups"]}, {due["id"], blocked["id"]})
        self.assertNotIn(future["id"], {t["id"] for t in report["follow_ups"]})

    def test_daily_time_budget_is_honored_and_does_not_hide_larger_work(self):
        large = self.task("Large overdue task", "--estimate", "90", "--due", "2026-10-27")
        small = self.task("Small useful task", "--estimate", "15")
        report = self.run_cli("today", "--date", "2026-10-28", "--minutes", "20")
        self.assertEqual([t["id"] for t in report["picked"]], [small["id"]])
        self.assertLessEqual(sum(t["estimate"] for t in report["picked"]), 20)
        self.assertIn(large["id"], {t["id"] for t in report["overdue"]})
        self.assertIn(large["id"], {t["id"] for t in report["deferred"]})

    def test_estimate_defaults_remain_distinguishable_from_user_estimates(self):
        assumed = self.task("An unestimated commitment")
        explicit = self.task("An explicitly estimated commitment", "--estimate", "30")
        self.assertEqual(assumed["estimate"], 30)
        self.assertEqual(assumed["estimate_source"], "default")
        self.assertEqual(explicit["estimate_source"], "user")
        preserved = self.run_cli("task", "update", assumed["id"], "--priority", "high")
        self.assertEqual(preserved["estimate_source"], "default")
        updated = self.run_cli("task", "update", assumed["id"], "--estimate", "20")
        self.assertEqual(updated["estimate_source"], "user")
        self.assertEqual(updated["estimate"], 20)

    def test_completed_dependency_unblocks_selection_without_changing_task_status(self):
        prerequisite = self.task("Prepare environment")
        dependent = self.task("Verify behavior", "--depends-on", prerequisite["id"])
        self.assertNotIn(dependent["id"], {t["id"] for t in self.run_cli("today")["picked"]})
        self.run_cli("task", "update", prerequisite["id"], "--status", "done", "--evidence", "Environment ready")
        report = self.run_cli("today")
        self.assertIn(dependent["id"], {t["id"] for t in report["picked"]})
        self.assertEqual(self.run_cli("task", "show", dependent["id"])["status"], "todo")

    def test_missing_project_evidence_surfaces_as_stale(self):
        self.app("never-reviewed")
        report = self.run_cli("today", "--date", date.today().isoformat())
        self.assertIn("never-reviewed", {app["id"] for app in report["stale_projects"]})
        self.run_cli("review", "add", "never-reviewed", "--summary", "Reviewed current state",
                     "--evidence", "Current branch and CI inspected")
        report = self.run_cli("today", "--date", date.today().isoformat())
        self.assertNotIn("never-reviewed", {app["id"] for app in report["stale_projects"]})

    def test_export_import_roundtrip_keeps_tasks_checkpoints_and_references(self):
        self.app("demo", "--verify", "Exercise startup")
        task = self.task("Finish migration", "--app", "demo", "--key", "migration-1")
        self.run_cli("checkpoint", "add", "demo", "--summary", "Migration started",
                     "--next-action", "Verify data", "--evidence", "Dry run passed")
        self.run_cli("review", "add", "demo", "--summary", "Reviewed migration", "--finding", "Needs final check")
        snapshot = self.run_cli("export")
        path = self.write_snapshot(snapshot)
        self.run_cli("init", workspace="restored")
        result = self.run_cli("import", "--file", path, workspace="restored")
        self.assertEqual(result["imported"], {"apps": 1, "tasks": 1, "checkpoints": 1, "reviews": 1})
        restored = self.run_cli("export", workspace="restored")
        for collection in ("apps", "tasks", "checkpoints", "reviews"):
            self.assertEqual(snapshot[collection], restored[collection], collection)
        self.assertEqual(self.run_cli("task", "show", task["id"], workspace="restored")["app_id"], "demo")

    def test_import_rejects_nonempty_workspace_and_invalid_snapshot_atomically(self):
        self.app()
        self.task("Retain this existing task", "--app", "demo")
        snapshot = self.run_cli("export")
        path = self.write_snapshot(snapshot)
        self.reject("import", "--file", path)
        self.assertEqual(len(self.run_cli("task", "list")), 1)
        self.run_cli("init", workspace="empty")
        broken = json.loads(json.dumps(snapshot))
        broken["tasks"][0]["app_id"] = "does-not-exist"
        self.reject("import", "--file", self.write_snapshot(broken), workspace="empty")
        self.assertEqual(self.run_cli("app", "list", workspace="empty"), [])
        self.assertEqual(self.run_cli("task", "list", workspace="empty"), [])
        broken = json.loads(json.dumps(snapshot))
        broken["schema_version"] = 999
        self.reject("import", "--file", self.write_snapshot(broken), workspace="empty")
        self.assertEqual(self.run_cli("app", "list", workspace="empty"), [])

    def test_capture_retries_after_migration_preserve_progress(self):
        task = self.task("Review a migration", "--key", "migration-review")
        self.run_cli("task", "update", task["id"], "--status", "doing",
                     "--next-action", "Inspect the remaining failure")
        snapshot = self.run_cli("export")
        self.run_cli("init", workspace="migrated")
        self.run_cli("import", "--file", self.write_snapshot(snapshot), workspace="migrated")
        retried = self.task("Review a migration", "--key", "migration-review", workspace="migrated")
        self.assertEqual(retried["id"], task["id"])
        self.assertEqual(retried["status"], "doing")
        self.assertEqual(retried["next_action"], "Inspect the remaining failure")
        self.assertEqual(len(self.run_cli("task", "list", workspace="migrated")), 1)

    def test_import_cannot_bypass_completion_evidence_or_dependency_validation(self):
        first = self.task("Prepare the app")
        second = self.task("Verify the app", "--depends-on", first["id"])
        snapshot = self.run_cli("export")
        self.run_cli("init", workspace="untrusted-import")
        broken = json.loads(json.dumps(snapshot))
        broken["tasks"][0]["status"] = "done"
        broken["tasks"][0]["evidence"] = []
        self.reject("import", "--file", self.write_snapshot(broken), workspace="untrusted-import")
        broken = json.loads(json.dumps(snapshot))
        broken["tasks"][0]["depends_on"] = [second["id"]]
        self.reject("import", "--file", self.write_snapshot(broken), workspace="untrusted-import")
        self.assertEqual(self.run_cli("task", "list", workspace="untrusted-import"), [])

    def test_parallel_captures_and_retries_do_not_lose_tasks(self):
        def capture(index):
            return self.task("Parallel task %d" % index, "--key", "parallel-%d" % index)["id"]
        with ThreadPoolExecutor(max_workers=8) as executor:
            ids = list(executor.map(capture, range(12)))
        self.assertEqual(len(set(ids)), 12)
        with ThreadPoolExecutor(max_workers=8) as executor:
            retries = list(executor.map(capture, [3] * 12))
        self.assertEqual(set(retries), {ids[3]})
        self.assertEqual(len(self.run_cli("task", "list")), 12)


if __name__ == "__main__":
    unittest.main()
