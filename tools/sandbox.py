"""Explicitly opted-in Circle sandbox checks; never loaded by the offline suite.

Run with ``python -m tools.sandbox check-config`` or see docs/sandbox.md.
No credentials, response bodies, cookies or signed URLs are written to evidence.
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".circlepy-sandbox"
PREFIX = "CIRCLE_SANDBOX_"
REQUIRED = (
    "DEDICATED", "CONTROLLED_ACCOUNTS", "ORIGIN", "COMMUNITY_ID", "COMMUNITY_NAME",
    "SDK_SHA", "ADMIN_V1_TOKEN", "ADMIN_V2_TOKEN", "HEADLESS_TOKEN",
    "MEMBER_ID", "MEMBER_EMAIL", "PEER_ID", "PEER_EMAIL", "SPACE_ID", "SPACE_NAME",
)
WORKFLOWS = ("identity", "invite_access", "content", "uploads", "learning", "quiz", "event", "chat", "notifications")
ID = re.compile(r"[1-9][0-9]*\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
SAFE_ID = re.compile(r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})\Z")


class SandboxError(Exception):
    """Messages contain fixed identifiers only, never provider or secret values."""


def require(condition, code):
    if not condition:
        raise SandboxError(code)


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    """Atomic replacement and fsync preserve the previous complete ledger on exit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


@dataclass(repr=False)
class Config:
    values: dict = field(repr=False)

    @classmethod
    def load(cls, environ=None):
        env = os.environ if environ is None else environ
        missing = [PREFIX + key for key in REQUIRED if not env.get(PREFIX + key)]
        require(not missing, "missing_configuration:" + ",".join(missing))
        values = {key.removeprefix(PREFIX): value for key, value in env.items() if key.startswith(PREFIX)}
        require(values["DEDICATED"] == "YES", "dedicated_sandbox_not_confirmed")
        require(values["CONTROLLED_ACCOUNTS"] == "YES", "controlled_accounts_not_confirmed")
        require(SHA.fullmatch(values["SDK_SHA"]), "invalid_SDK_SHA")
        for key in ("COMMUNITY_ID", "MEMBER_ID", "PEER_ID", "SPACE_ID"):
            require(ID.fullmatch(values[key]), "invalid_" + key)
        for key in ("COURSE_ID", "LESSON_ID", "QUIZ_ID", "EVENT_ID"):
            if values.get(key):
                require(ID.fullmatch(values[key]), "invalid_" + key)
        require(values["MEMBER_ID"] != values["PEER_ID"], "test_identities_must_differ")
        for key in ("MEMBER_EMAIL", "PEER_EMAIL"):
            require(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values[key]), "invalid_" + key)
        require(values["MEMBER_EMAIL"].lower() != values["PEER_EMAIL"].lower(), "test_emails_must_differ")
        parsed = urlsplit(values["ORIGIN"])
        require(parsed.scheme == "https" and parsed.hostname is not None
                and parsed.hostname.endswith(".circle.so") and parsed.port in (None, 443)
                and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
                and parsed.username is None and parsed.password is None
                and not any(c.isspace() for c in values["ORIGIN"]), "invalid_Circle_origin")
        values["ORIGIN"] = values["ORIGIN"].rstrip("/")
        if values.get("CHAT_UUID"):
            require(str(uuid.UUID(values["CHAT_UUID"])) == values["CHAT_UUID"], "invalid_CHAT_UUID")
        return cls(values)

    def __getitem__(self, key):
        return self.values[key]

    def optional(self, key):
        return self.values.get(key)

    def number(self, key):
        return int(self[key])

    def binding(self):
        # IDs/addresses are needed only in memory. Bind a ledger to its exact
        # sandbox and controlled accounts without copying them into the report.
        keys = ("ORIGIN", "COMMUNITY_ID", "COMMUNITY_NAME", "MEMBER_ID", "MEMBER_EMAIL",
                "PEER_ID", "PEER_EMAIL", "SPACE_ID", "SPACE_NAME", "COURSE_ID", "LESSON_ID",
                "QUIZ_ID", "EVENT_ID", "CHAT_UUID")
        return hashlib.sha256(json.dumps([self.optional(key) for key in keys]).encode()).hexdigest()


def verified_version(config):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    sha = git("rev-parse", "HEAD")
    require(sha == config["SDK_SHA"], "SDK_SHA_mismatch")
    require(git("branch", "--show-current") == "main", "main_checkout_required")
    require(git("remote", "get-url", "origin") == "https://github.com/atomimus/CirclePy.git", "remote_mismatch")
    remote = git("ls-remote", "origin", "refs/heads/main").split()[0]
    require(remote == sha, "verified_origin_main_required")
    require(not git("diff", "HEAD", "--", "circlepy", "api/specs", "pyproject.toml",
                    "requirements.txt", "constraints-dev.txt"), "dirty_SDK_inputs")
    require(not git("ls-files", "--others", "--exclude-standard", "--", "circlepy"), "untracked_SDK_inputs")
    return sha


class Ledger:
    def __init__(self, directory, config, sha, *, resume=False):
        self.directory = Path(directory)
        self.path = self.directory / "ledger.json"
        if resume:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            require(self.data["binding"] == config.binding(), "cleanup_sandbox_binding_mismatch")
            require(self.data["sdk_sha"] == sha, "cleanup_SDK_mismatch")
            require(re.fullmatch(r"circlepy30-[0-9a-f]{32}", self.data["run_id"]), "invalid_ledger_run_id")
        else:
            require(not self.path.exists(), "existing_ledger_requires_cleanup")
            self.data = dict(schema_version=1, run_id="circlepy30-" + uuid.uuid4().hex,
                             binding=config.binding(), sdk_sha=sha, created_at=now(), fixtures=[])
            self.save()

    def save(self):
        write_json(self.path, self.data)

    def intent(self, mode, kind, **fields):
        entry = dict(mode=mode, kind=kind, marker=self.data["run_id"] + "-" + mode + "-" + kind,
                     state="intent", created_at=now(), **fields)
        self.data["fixtures"].append(entry)
        self.save()  # Persist BEFORE any request; unknown outcomes are never replayed.
        return entry

    def update(self, entry, state, **fields):
        entry.update(state=state, **fields)
        self.save()

    def unresolved(self):
        return [e for e in self.data["fixtures"] if e["state"] not in ("cleaned", "restored", "archived", "deleted")]


class Report:
    def __init__(self, directory, sha, run_id=None, *, live=False):
        self.path = Path(directory) / "report.json"
        self.data = dict(schema_version=1, sdk_sha=sha, run_id=run_id, started_at=now(),
                         evidence_kind="live_sandbox" if live else "synthetic_harness", completed=False, calls=[], workflows={}, outcomes={}, gaps=[],
                         financial="offline_contract_only_no_live_financial_requests")

    def save(self):
        write_json(self.path, self.data)

    def gap(self, mode, workflow, code, status=None):
        self.data["gaps"].append(dict(mode=mode, workflow=workflow, code=code, status=status,
                                     acceptance="required"))
        self.save()

    def record(self, mode, family, method, path, response=None, error=None):
        # Only our fixed operation paths are accepted by the guard below. No
        # query strings, request/response bodies or arbitrary exception text.
        status = getattr(response, "status_code", None) if response is not None else getattr(error, "status_code", None)
        request_id = None
        if response is not None:
            request_id = next((v for k, v in response.headers.items() if k.lower() == "x-request-id"), None)
        elif error is not None:
            request_id = getattr(error, "request_id", None)
        if not isinstance(request_id, str) or not SAFE_ID.fullmatch(request_id):
            request_id = None
        self.data["calls"].append(dict(mode=mode, family=family, method=method, path=path,
                                       status=status, request_id=request_id, at=now(),
                                       outcome="response" if error is None else "error"))
        self.save()

    def finish(self, ledger):
        workflows = self.data["workflows"]
        outcomes = self.data["outcomes"]
        parity = all(workflows.get("sync", {}).get(w) == workflows.get("async", {}).get(w) == "passed"
                     and w in outcomes.get("sync", {}) and w in outcomes.get("async", {})
                     and outcomes["sync"][w] == outcomes["async"][w]
                     for w in WORKFLOWS)
        observed = all(any(c["mode"] == mode and c["family"] == family
                           and c["status"] is not None and 200 <= c["status"] < 300
                           for c in self.data["calls"])
                       for mode in ("sync", "async") for family in READS)
        self.data.update(finished_at=now(), parity=parity, observed_families=observed, unresolved_cleanup=len(ledger.unresolved()),
                         completed=self.data["evidence_kind"] == "live_sandbox" and parity and observed
                         and not ledger.unresolved() and not self.data["gaps"])
        self.save()
        return self.data["completed"]


# A deliberately small allowlist excludes billing, tax, paywalls, exports,
# arbitrary member creation/deactivation, community changes and external messages.
READS = {
    "admin_v1": (r"/communities/[1-9][0-9]*", r"/community_members/search", r"/community_members/[1-9][0-9]*"),
    "admin_v2": (r"/community", r"/community_members/[1-9][0-9]*", r"/community_members/search",
                 r"/spaces/[1-9][0-9]*", r"/access_groups", r"/invitation_links", r"/posts/[1-9][0-9]*",
                 r"/access_groups/[1-9][0-9]*/community_member", r"/events/[1-9][0-9]*", r"/space_members"),
    "auth": (),
    "member": (r"/community_member", r"/community_members/[1-9][0-9]*/public_profile",
               r"/community_members", r"/spaces/[1-9][0-9]*/posts/[1-9][0-9]*",
               r"/posts/[1-9][0-9]*/comments(?:/[1-9][0-9]*)?", r"/posts/[1-9][0-9]*/user_likes",
               r"/courses/[1-9][0-9]*/lessons/[1-9][0-9]*", r"/courses/[1-9][0-9]*/sections",
               r"/quizzes/[1-9][0-9]*/attempts/[1-9][0-9]*", r"/events/[1-9][0-9]*/event_attendees",
               r"/messages/[0-9a-f-]{36}/chat_room_participants", r"/messages/[0-9a-f-]{36}/chat_room_messages(?:/[1-9][0-9]*)?",
               r"/notifications", r"/notifications/new_notifications_count"),
}
WRITES = {
    "admin_v1": {},
    "admin_v2": {"POST": (r"/access_groups", r"/invitation_links", r"/posts", r"/access_groups/[1-9][0-9]*/community_members"),
                 "DELETE": (r"/access_groups/[1-9][0-9]*", r"/invitation_links/[1-9][0-9]*", r"/posts/[1-9][0-9]*",
                            r"/access_groups/[1-9][0-9]*/community_members")},
    "auth": {"POST": (r"/auth_token", r"/access_token/revoke", r"/refresh_token/revoke")},
    "member": {"POST": (r"/posts/[1-9][0-9]*/comments", r"/posts/[1-9][0-9]*/user_likes", r"/direct_uploads",
                        r"/quizzes/[1-9][0-9]*/attempts", r"/events/[1-9][0-9]*/event_attendees",
                        r"/messages/[0-9a-f-]{36}/chat_room_messages"),
               "PATCH": (r"/courses/[1-9][0-9]*/lessons/[1-9][0-9]*/progress",),
               "DELETE": (r"/posts/[1-9][0-9]*/comments/[1-9][0-9]*", r"/posts/[1-9][0-9]*/user_likes",
                          r"/events/[1-9][0-9]*/event_attendees", r"/messages/[0-9a-f-]{36}/chat_room_messages/[1-9][0-9]*")},
}


class Guard:
    def __init__(self, report, mode):
        self.report, self.mode = report, mode
        self.admin_verified = False
        self.verified = False

    def check(self, family, method, path):
        require(family in READS and isinstance(path, str), "unapproved_family")
        patterns = READS[family] if method == "GET" else WRITES[family].get(method, ())
        require(any(re.fullmatch(p, path) for p in patterns), "unapproved_operation")
        if method != "GET":
            require(self.admin_verified if family == "auth" else self.verified, "sandbox_identity_not_verified")

    def attach(self, transport, family):
        original = transport.request
        def relative(path):
            base = transport.base_url.rstrip("/")
            return path[len(base):] if isinstance(path, str) and path.startswith(base + "/") else path
        if inspect.iscoroutinefunction(original):
            async def request(method, path, **kwargs):
                safe_path = relative(path)
                self.check(family, method, safe_path)
                try:
                    response = await original(method, path, **kwargs)
                except Exception as error:
                    self.report.record(self.mode, family, method, safe_path, error=error)
                    raise
                self.report.record(self.mode, family, method, safe_path, response=response)
                return response
        else:
            def request(method, path, **kwargs):
                safe_path = relative(path)
                self.check(family, method, safe_path)
                try:
                    response = original(method, path, **kwargs)
                except Exception as error:
                    self.report.record(self.mode, family, method, safe_path, error=error)
                    raise
                self.report.record(self.mode, family, method, safe_path, response=response)
                return response
        transport.request = request


async def invoke(function, *args, **kwargs):
    result = function(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


class RunLock:
    """Serialize live mutations; a stale lock requires explicit local inspection."""
    def __enter__(self):
        PRIVATE.mkdir(parents=True, exist_ok=True)
        self.path = PRIVATE / "active.lock"
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise SandboxError("active_or_interrupted_run_lock_requires_inspection") from None
        os.write(self.fd, str(os.getpid()).encode())
        return self

    def __exit__(self, *args):
        os.close(self.fd)
        self.path.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check-config", "run", "cleanup", "gate"))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    directory = args.run_dir or PRIVATE / "current"
    # Sensitive local artifacts can never accidentally be placed in tracked docs.
    try:
        require(directory.resolve().is_relative_to(PRIVATE.resolve()), "run_directory_must_be_private")
        if args.action == "gate":
            report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
            ledger = json.loads((directory / "ledger.json").read_text(encoding="utf-8"))
            require(report.get("sdk_sha") == ledger.get("sdk_sha") and report.get("run_id") == ledger.get("run_id"), "unbound_report")
            require(report.get("evidence_kind") == "live_sandbox" and report.get("observed_families") is True
                    and report.get("completed") is True and not report.get("gaps")
                    and report.get("parity") is True and report.get("unresolved_cleanup") == 0
                    and all(e["state"] in ("cleaned", "restored", "archived", "deleted") for e in ledger["fixtures"]), "sandbox_release_gate_unresolved")
            print("Sandbox report and cleanup gate passed")
            return 0
        config = Config.load()
        if args.action == "check-config":
            print("Sandbox configuration present; remote identity has not been checked")
            return 0
        require(args.live, "explicit_live_opt_in_required")
        require("PYTEST_CURRENT_TEST" not in os.environ, "live_execution_inside_offline_pytest_forbidden")
        sha = verified_version(config)
        with RunLock():
            ledger = Ledger(directory, config, sha, resume=args.action == "cleanup")
            report = Report(directory, sha, ledger.data["run_id"], live=True)
            if args.action == "cleanup":
                report.data = json.loads(report.path.read_text(encoding="utf-8"))
            from tools.sandbox_workflows import run
            result = asyncio.run(run(config, ledger, report, cleanup_only=args.action == "cleanup"))
        print("Sandbox workflows and cleanup passed" if result else "Sandbox evidence has unresolved gaps; inspect the private report")
        return 0 if result else 1
    except (Exception, KeyboardInterrupt) as error:
        # No traceback, exception repr, response body or environment value.
        message = str(error) if isinstance(error, SandboxError) else "sandbox_stopped:" + type(error).__name__
        if isinstance(error, SandboxError) and message.startswith("missing_configuration:"):
            write_json(directory / "access.json", dict(status="needs_configuration", live_requests=0,
                       missing=message.split(":", 1)[1].split(","), at=now(), completed=False))
        print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
