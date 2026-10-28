"""Representative SDK workflows for tools.sandbox; all mutations are journaled.

These are real sync/native-async SDK calls. Offline tests of this harness are
explicitly synthetic and cannot produce a passing live release report.
"""

import asyncio
from importlib.metadata import version
import hashlib
import io
from pathlib import Path
import platform
import uuid

from circlepy import (AdminV2Client, AsyncAdminV2Client, AsyncCircleClient,
                      AsyncHeadlessClient, CircleClient, HeadlessClient)
from circlepy.errors import NotFoundError
from tools.sandbox import Guard, SandboxError, WORKFLOWS, invoke, require


def object_result(value, key=None):
    require(isinstance(value, dict), "unexpected_response_object")
    result = value.get(key, value) if key else value
    require(isinstance(result, dict) and result.get("success") is not False, "unsuccessful_response")
    return result


def identifier(value, key=None):
    result = object_result(value, key)
    require(type(result.get("id")) is int and result["id"] > 0, "missing_response_id")
    return result["id"]


def complete_page(value):
    value = object_result(value)
    require(isinstance(value.get("records"), list) and value.get("has_next_page") is False,
            "complete_single_page_required")
    return value["records"]


def rich_text(text):
    return {"body": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": text}]}]}}


class Suite:
    def __init__(self, config, ledger, report, mode):
        self.config, self.ledger, self.report, self.mode = config, ledger, report, mode
        self.guard = Guard(report, mode)
        self.clients = []
        self.member = None
        self.authenticated = False

    def outcome(self, workflow, value):
        self.report.data["workflows"].setdefault(self.mode, {})[workflow] = value
        self.report.save()

    def observed(self, workflow, value):
        """Only explicit scalar invariants; never arbitrary provider objects."""
        self.report.data["outcomes"].setdefault(self.mode, {})[workflow] = value
        self.report.save()

    async def setup(self):
        c = self.config
        legacy, admin, member = ((CircleClient, AdminV2Client, HeadlessClient) if self.mode == "sync"
                                 else (AsyncCircleClient, AsyncAdminV2Client, AsyncHeadlessClient))
        options = dict(timeout=30, max_retries=0, trust_env=False, raise_on_error=True)
        self.legacy = legacy(c["ADMIN_V1_TOKEN"], community_id=c.number("COMMUNITY_ID"),
                             base_url=c["ORIGIN"] + "/api/v1", **options)
        self.clients.append(self.legacy)
        self.admin = admin(c["ADMIN_V2_TOKEN"], base_url=c["ORIGIN"] + "/api/admin/v2", **options)
        self.clients.append(self.admin)
        self.guard.attach(self.legacy.transport, "admin_v1")
        self.guard.attach(self.admin.transport, "admin_v2")
        for data in (await invoke(self.admin.communities.get),
                     await invoke(self.legacy.community.get, c.number("COMMUNITY_ID"))):
            community = object_result(data)
            require(community.get("id") == c.number("COMMUNITY_ID")
                    and community.get("name") == c["COMMUNITY_NAME"], "community_identity_mismatch")
        self.guard.admin_verified = True
        # Public, network-free factory. The placeholder is replaced by real
        # authentication before any Member call and never leaves this process.
        self.member = member.from_tokens(access_token="sandbox-preauthentication",
                                         api_key=c["HEADLESS_TOKEN"], community_url=c["ORIGIN"], **options)
        self.clients.append(self.member)
        self.guard.attach(self.member.transport, "member")
        self.guard.attach(self.member.auth.auth_transport, "auth")
        tokens = await invoke(self.member.auth.authenticate, community_member_id=c.number("MEMBER_ID"))
        self.authenticated = True
        require(tokens.get("community_id") == c.number("COMMUNITY_ID")
                and tokens.get("community_member_id") == c.number("MEMBER_ID"), "auth_identity_mismatch")
        current = await invoke(self.member.community_members.get_current_member)
        require(identifier(current) == c.number("MEMBER_ID"), "member_identity_mismatch")
        for role in ("MEMBER", "PEER"):
            member_data = object_result(await invoke(self.admin.community_members.get, c.number(role + "_ID")))
            require(member_data.get("id") == c.number(role + "_ID")
                    and member_data.get("community_id") == c.number("COMMUNITY_ID")
                    and member_data.get("email", "").lower() == c[role + "_EMAIL"].lower(), "test_account_mismatch")
        space = object_result(await invoke(self.admin.spaces.get, c.number("SPACE_ID")))
        require(space.get("community_id") == c.number("COMMUNITY_ID")
                and space.get("id") == c.number("SPACE_ID") and space.get("name") == c["SPACE_NAME"]
                and space.get("is_private") is True, "private_fixture_space_required")
        members = complete_page(await invoke(self.admin.space_members.list_members, c.number("SPACE_ID"), per_page=100))
        require({m.get("community_member_id") for m in members} == {c.number("MEMBER_ID"), c.number("PEER_ID")},
                "fixture_space_has_uncontrolled_members")
        self.guard.verified = True
        self.report.data.setdefault("capabilities", {})[self.mode] = {
            "features": {key: current["features"][key] for key in (
                "messaging_enabled", "chat_reactions_enabled", "voice_messages_enabled",
                "tiptap_webview_editor_enabled") if type(current.get("features", {}).get(key)) is bool},
            "private_space_controlled_members_verified": True,
        }
        self.outcome("identity", "passed")

    async def identity(self):
        c = self.config
        legacy = await invoke(self.legacy.member.search_raw, c["MEMBER_EMAIL"])
        modern = await invoke(self.admin.community_members.search, c["MEMBER_EMAIL"])
        require(identifier(legacy) == identifier(modern) == c.number("MEMBER_ID"), "family_search_parity_failed")
        profile = await invoke(self.member.community_members.get_public_profile, c.number("MEMBER_ID"))
        require(identifier(profile) == c.number("MEMBER_ID"), "profile_identity_failed")
        self.observed("identity", {"legacy_member_matches": True, "modern_member_matches": True,
                                   "profile_matches": True})

    async def invite_access(self):
        c, ledger = self.config, self.ledger
        group = ledger.intent(self.mode, "access_group")
        data = await invoke(self.admin.access_groups.create, {"access_group": {"name": group["marker"]}})
        ledger.update(group, "created", id=identifier(data))
        access = ledger.intent(self.mode, "access_member", group_id=group["id"], group_marker=group["marker"])
        data = await invoke(self.admin.access_group_members.add, group["id"], {"email": c["PEER_EMAIL"]})
        require(object_result(data).get("success") is not False, "access_add_failed")
        ledger.update(access, "created")
        data = await invoke(self.admin.access_group_members.get, group["id"], c["PEER_EMAIL"])
        require(data.get("community_member_id") == c.number("PEER_ID"), "access_readback_failed")
        invitation = ledger.intent(self.mode, "invitation")
        data = await invoke(self.admin.invitation_links.create,
                            {"name": invitation["marker"], "access_group_ids": [group["id"]]})
        ledger.update(invitation, "created", id=identifier(data))
        links = complete_page(await invoke(self.admin.invitation_links.list_links, name=invitation["marker"], per_page=100))
        require(any(link.get("id") == invitation["id"] and link.get("name") == invitation["marker"] for link in links),
                "invitation_readback_failed")
        self.observed("invite_access", {"controlled_member_access": True, "invitation_readback": True})
        # Redemption URL is never recorded, opened, emailed or messaged.

    async def content(self):
        c, ledger = self.config, self.ledger
        post = ledger.intent(self.mode, "post")
        data = await invoke(self.admin.posts.create, {
            "space_id": c.number("SPACE_ID"), "name": post["marker"], "slug": post["marker"],
            "tiptap_body": rich_text(post["marker"]), "status": "published", "skip_notifications": True,
            "user_email": c["MEMBER_EMAIL"], "is_comments_enabled": True, "is_liking_enabled": True,
        })
        ledger.update(post, "created", id=identifier(data, "post"))
        data = await invoke(self.member.posts.get_post, c.number("SPACE_ID"), post["id"])
        require(data.get("name") == post["marker"], "post_readback_failed")
        comment = ledger.intent(self.mode, "comment", post_id=post["id"], post_marker=post["marker"])
        data = await invoke(self.member.comments.create_post_comment, post["id"], body=comment["marker"])
        ledger.update(comment, "created", id=identifier(data))
        data = await invoke(self.member.comments.get_post_comment, post["id"], comment["id"])
        require(data.get("body_text") == comment["marker"], "comment_readback_failed")
        reaction = ledger.intent(self.mode, "reaction", post_id=post["id"], post_marker=post["marker"])
        await invoke(self.member.posts.like_post, post["id"], reaction_type="like")
        ledger.update(reaction, "created")
        data = await invoke(self.member.posts.get_post, c.number("SPACE_ID"), post["id"])
        require(data.get("reaction_summary", {}).get("current_user_reaction_type") == "like", "reaction_readback_failed")
        self.observed("content", {"post_readback": True, "comment_readback": True,
                                  "current_user_reaction_type": "like"})

    async def uploads(self):
        require(self.config.optional("ALLOW_RETAINED_UPLOADS") == "YES", "upload_retention_decision_required")
        entry = self.ledger.intent(self.mode, "upload")
        # A tiny generated text file; storage authorization isolation belongs to
        # the verified SDK. upload_file returns only after a successful storage PUT.
        content = b"circlepy30 sandbox upload\n"
        data = await invoke(self.member.uploads.upload_file, io.BytesIO(content),
                            filename=entry["marker"] + ".txt", content_type="text/plain",
                            key="uploads/" + entry["marker"] + ".txt")
        require(isinstance(data.get("signed_id"), str) and bool(data["signed_id"]), "upload_result_failed")
        self.ledger.update(entry, "retained", reason="no_documented_standalone_upload_delete", storage_put_completed=True)
        require(data.get("file_size") == len(content) and data.get("mime_type") == "text/plain", "upload_metadata_mismatch")
        self.observed("uploads", {"storage_put_completed": True, "bytes": len(content),
                                  "content_sha256": hashlib.sha256(content).hexdigest()})
        self.report.gap(self.mode, "uploads", "provider_storage_retention_requires_acceptance")

    async def learning(self):
        c = self.config
        require(c.optional("COURSE_ID") and c.optional("LESSON_ID"), "course_and_lesson_configuration_required")
        space = await invoke(self.admin.spaces.get, c.number("COURSE_ID"))
        require(space.get("community_id") == c.number("COMMUNITY_ID")
                and space.get("name", "").startswith("circlepy30-"), "dedicated_course_required")
        lesson = await invoke(self.member.courses.get_course_lesson, c.number("COURSE_ID"), c.number("LESSON_ID"))
        require(lesson.get("id") == c.number("LESSON_ID")
                and lesson.get("space", {}).get("id") == c.number("COURSE_ID"), "lesson_identity_mismatch")
        previous = lesson.get("progress", {}).get("status")
        require(previous in ("incomplete", "completed"), "unknown_original_progress")
        target = "incomplete" if previous == "completed" else "completed"
        entry = self.ledger.intent(self.mode, "progress", course_id=c.number("COURSE_ID"),
                                   lesson_id=c.number("LESSON_ID"), previous=previous, target=target)
        data = await invoke(self.member.courses.update_course_lesson_progress, entry["course_id"], entry["lesson_id"], status=target)
        self.ledger.update(entry, "created")
        require(data.get("status") == target, "progress_update_failed")
        data = await invoke(self.member.courses.get_course_lesson, entry["course_id"], entry["lesson_id"])
        require(data.get("progress", {}).get("status") == target, "progress_readback_failed")
        self.observed("learning", {"previous": previous, "updated": target, "readback": True})

    async def quiz(self):
        c = self.config
        require(c.optional("QUIZ_ID") and c.optional("ALLOW_RETAINED_QUIZ") == "YES", "quiz_retention_decision_required")
        # No arbitrary response JSON is accepted: a deliberately empty attempt is
        # documented by the schema. Provider validation/attempt limits remain gaps.
        entry = self.ledger.intent(self.mode, "quiz", quiz_id=c.number("QUIZ_ID"))
        data = await invoke(self.member.quizzes.create_quiz_attempt, entry["quiz_id"], responses=[])
        self.ledger.update(entry, "retained", id=identifier(data), reason="no_documented_attempt_delete")
        check = await invoke(self.member.quizzes.get_quiz_attempt, entry["quiz_id"], entry["id"])
        require(check.get("id") == entry["id"] and check.get("quiz_id") == entry["quiz_id"], "quiz_readback_failed")
        require(isinstance(check.get("result"), str) and type(check.get("grade")) is int, "quiz_outcome_missing")
        self.observed("quiz", {"result": check["result"], "grade": check["grade"], "readback": True})
        self.report.gap(self.mode, "quiz", "provider_attempt_retention_requires_acceptance")

    async def event(self):
        c = self.config
        require(c.optional("EVENT_ID"), "event_configuration_required")
        event_id = c.number("EVENT_ID")
        event = await invoke(self.admin.events.get, event_id)
        require(event.get("space", {}).get("community_id") == c.number("COMMUNITY_ID")
                and event.get("name", "").startswith("circlepy30-")
                and event.get("send_email_confirmation") is False and event.get("send_email_reminder") is False,
                "dedicated_nonemail_event_required")
        before = complete_page(await invoke(self.member.events.list_event_attendees, event_id, per_page=100))
        require(not any(x.get("community_member_id") == c.number("MEMBER_ID") for x in before), "preexisting_RSVP_not_owned")
        entry = self.ledger.intent(self.mode, "rsvp", event_id=event_id, event_name=event["name"])
        data = await invoke(self.member.events.create_event_attendee, event_id)
        self.ledger.update(entry, "created", id=identifier(data))
        after = complete_page(await invoke(self.member.events.list_event_attendees, event_id, per_page=100))
        require(any(x.get("community_member_id") == c.number("MEMBER_ID") for x in after), "RSVP_readback_failed")
        self.observed("event", {"controlled_member_RSVP": True, "readback": True})

    async def controlled_chat(self):
        c = self.config
        require(c.optional("CHAT_UUID"), "controlled_chat_configuration_required")
        rows = complete_page(await invoke(self.member.chat.list_chat_room_participants, c["CHAT_UUID"], per_page=100))
        require({r.get("community_member_id") for r in rows} == {c.number("MEMBER_ID"), c.number("PEER_ID")},
                "chat_has_uncontrolled_participants")

    async def chat(self):
        await self.controlled_chat()
        entry = self.ledger.intent(self.mode, "message", room=self.config["CHAT_UUID"])
        data = await invoke(self.member.chat.create_chat_room_message, entry["room"], rich_text_body=rich_text(entry["marker"]))
        require(isinstance(data.get("creation_uuid"), str), "missing_message_creation_receipt")
        receipt = str(uuid.UUID(data["creation_uuid"]))
        self.ledger.update(entry, "pending_delivery", creation_uuid=receipt)
        # Circle returns 202/creation_uuid, not a message ID. Resolve the unique
        # exact task marker; never reinterpret creation_uuid as an ID or resend.
        for _ in range(5):
            rows = object_result(await invoke(self.member.chat.list_chat_room_messages, entry["room"], previous_per_page=100)).get("records", [])
            matches = [r for r in rows if r.get("body") == entry["marker"]]
            require(len(matches) <= 1, "ambiguous_message_receipt")
            if matches:
                self.ledger.update(entry, "created", id=identifier(matches[0]))
                require(matches[0].get("sender", {}).get("community_member_id") == self.config.number("MEMBER_ID"), "message_sender_mismatch")
                self.observed("chat", {"delivered": True, "sender_matches": True, "controlled_participants": True})
                return
            await asyncio.sleep(1)
        raise SandboxError("message_delivery_unconfirmed_no_replay")

    async def notifications(self):
        # Read-only: never mutate or delete preexisting member notifications.
        page = await invoke(self.member.notifications.list_notifications, per_page=10)
        require(isinstance(object_result(page).get("records"), list), "notification_list_failed")
        count = await invoke(self.member.notifications.get_new_notifications_count)
        require(isinstance(count, dict), "notification_count_failed")
        self.observed("notifications", {"list_envelope": "records", "count_envelope": "object"})

    async def owned_post(self, entry):
        data = await invoke(self.admin.posts.get, entry.get("post_id", entry.get("id")))
        post = object_result(data, "post")
        require(post.get("name") == entry.get("post_marker", entry["marker"])
                and post.get("space_id", post.get("space", {}).get("id")) == self.config.number("SPACE_ID"), "cleanup_post_ownership_mismatch")

    async def owned_group(self, group_id, marker):
        rows = complete_page(await invoke(self.admin.access_groups.list_groups, name=marker, per_page=100))
        matches = [g for g in rows if g.get("id") == group_id and g.get("name") == marker
                   and g.get("community_id") == self.config.number("COMMUNITY_ID")]
        require(len(matches) == 1, "cleanup_group_ownership_mismatch")

    async def cleanup(self):
        for entry in reversed(self.ledger.data["fixtures"]):
            if entry["mode"] != self.mode or entry["state"] in ("cleaned", "deleted", "archived", "restored", "retained"):
                continue
            try:
                require(entry["state"] in ("created", "cleanup_intent"), "ambiguous_mutation_requires_manual_reconciliation")
                kind = entry["kind"]
                require(entry["marker"] == self.ledger.data["run_id"] + "-" + self.mode + "-" + kind, "cleanup_marker_mismatch")
                if kind in ("post", "comment", "reaction"):
                    await self.owned_post(entry)
                if kind == "post":
                    require(not any(e.get("post_id") == entry["id"] and e["state"] != "cleaned"
                                    for e in self.ledger.data["fixtures"]), "cleanup_children_unresolved")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.admin.posts.delete, entry["id"])
                    try:
                        await invoke(self.admin.posts.get, entry["id"])
                    except NotFoundError:
                        pass
                    else:
                        raise SandboxError("post_delete_unconfirmed")
                elif kind == "comment":
                    data = await invoke(self.member.comments.get_post_comment, entry["post_id"], entry["id"])
                    require(data.get("body_text") == entry["marker"], "cleanup_comment_ownership_mismatch")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.member.comments.delete_post_comment, entry["post_id"], entry["id"])
                    try:
                        data = await invoke(self.member.comments.get_post_comment, entry["post_id"], entry["id"])
                    except NotFoundError:
                        pass
                    else:
                        require(data.get("removed_at") is not None, "comment_delete_unconfirmed")
                elif kind == "reaction":
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.member.posts.unlike_post, entry["post_id"])
                    data = await invoke(self.member.posts.get_post, self.config.number("SPACE_ID"), entry["post_id"])
                    require(data.get("reaction_summary", {}).get("current_user_reaction_type") is None, "reaction_remove_unconfirmed")
                elif kind == "invitation":
                    rows = complete_page(await invoke(self.admin.invitation_links.list_links, name=entry["marker"], per_page=100))
                    require(any(r.get("id") == entry["id"] and r.get("name") == entry["marker"] for r in rows), "cleanup_invitation_ownership_mismatch")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.admin.invitation_links.delete, entry["id"])
                    rows = complete_page(await invoke(self.admin.invitation_links.list_links, name=entry["marker"], per_page=100))
                    require(not any(r.get("id") == entry["id"] and r.get("active") is not False for r in rows), "invitation_delete_unconfirmed")
                elif kind == "access_member":
                    await self.owned_group(entry["group_id"], entry["group_marker"])
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.admin.access_group_members.remove, entry["group_id"], self.config["PEER_EMAIL"])
                    try:
                        await invoke(self.admin.access_group_members.get, entry["group_id"], self.config["PEER_EMAIL"])
                    except NotFoundError:
                        pass
                    else:
                        raise SandboxError("access_remove_unconfirmed")
                elif kind == "access_group":
                    require(not any(e.get("group_id") == entry["id"] and e["state"] != "cleaned" for e in self.ledger.data["fixtures"]), "cleanup_members_unresolved")
                    require(not any(e["kind"] == "invitation" and e["mode"] == self.mode and e["state"] != "cleaned" for e in self.ledger.data["fixtures"]), "cleanup_invitation_unresolved")
                    await self.owned_group(entry["id"], entry["marker"])
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.admin.access_groups.archive, entry["id"])
                    rows = complete_page(await invoke(self.admin.access_groups.list_groups, name=entry["marker"], status="archived", per_page=100))
                    require(any(r.get("id") == entry["id"] and r.get("status") == "archived" for r in rows), "group_archive_unconfirmed")
                    self.ledger.update(entry, "archived")
                    continue
                elif kind == "progress":
                    require(entry["course_id"] == self.config.number("COURSE_ID") and entry["lesson_id"] == self.config.number("LESSON_ID"), "cleanup_lesson_mismatch")
                    data = await invoke(self.member.courses.get_course_lesson, entry["course_id"], entry["lesson_id"])
                    require(data.get("progress", {}).get("status") == entry["target"], "progress_changed_externally")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.member.courses.update_course_lesson_progress, entry["course_id"], entry["lesson_id"], status=entry["previous"])
                    data = await invoke(self.member.courses.get_course_lesson, entry["course_id"], entry["lesson_id"])
                    require(data.get("progress", {}).get("status") == entry["previous"], "progress_restore_unconfirmed")
                    self.ledger.update(entry, "restored")
                    continue
                elif kind == "rsvp":
                    require(entry["event_id"] == self.config.number("EVENT_ID"), "cleanup_event_mismatch")
                    event = await invoke(self.admin.events.get, entry["event_id"])
                    require(event.get("name") == entry["event_name"] and event.get("space", {}).get("community_id") == self.config.number("COMMUNITY_ID"), "cleanup_event_ownership_mismatch")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.member.events.delete_event_attendee, entry["event_id"])
                    rows = complete_page(await invoke(self.member.events.list_event_attendees, entry["event_id"], per_page=100))
                    require(not any(r.get("community_member_id") == self.config.number("MEMBER_ID") for r in rows), "RSVP_remove_unconfirmed")
                elif kind == "message":
                    require(entry["room"] == self.config["CHAT_UUID"], "cleanup_room_mismatch")
                    await self.controlled_chat()
                    data = await invoke(self.member.chat.get_chat_room_message, entry["room"], entry["id"])
                    require(data.get("body") == entry["marker"], "cleanup_message_ownership_mismatch")
                    self.ledger.update(entry, "cleanup_intent")
                    await invoke(self.member.chat.delete_chat_room_message, entry["room"], entry["id"])
                    try:
                        await invoke(self.member.chat.get_chat_room_message, entry["room"], entry["id"])
                    except NotFoundError:
                        pass
                    else:
                        raise SandboxError("message_delete_unconfirmed")
                else:
                    raise SandboxError("unknown_cleanup_kind")
                self.ledger.update(entry, "cleaned")
            except Exception as error:
                self.report.gap(self.mode, "cleanup", str(error) if isinstance(error, SandboxError) else type(error).__name__, getattr(error, "status_code", None))

    async def close(self):
        if self.authenticated:
            for method in (self.member.auth.revoke_refresh_token, self.member.auth.revoke_access_token):
                try:
                    await invoke(method)
                except Exception as error:
                    self.report.gap(self.mode, "auth_cleanup", type(error).__name__, getattr(error, "status_code", None))
        for client in reversed(self.clients):
            await invoke(client.close if self.mode == "sync" else client.aclose)


async def run(config, ledger, report, *, cleanup_only=False):
    import circlepy
    from tools.sandbox import ROOT
    if report.data["evidence_kind"] == "live_sandbox":
        require(ROOT / "circlepy" in Path(circlepy.__file__).resolve().parents,
                "SDK_source_import_mismatch")
    report.data["harness_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("tools/sandbox.py", "tools/sandbox_workflows.py")}
    report.data["versions"] = {"python": platform.python_version(), **{
        package: version(package) for package in ("circlepy", "requests", "aiohttp", "pillow", "commonmark")}}
    report.save()
    for mode in ("sync", "async"):
        suite = Suite(config, ledger, report, mode)
        try:
            await suite.setup()
            if not cleanup_only:
                for workflow in WORKFLOWS:
                    try:
                        await getattr(suite, workflow)()
                        suite.outcome(workflow, "passed")
                    except Exception as error:
                        status = getattr(error, "status_code", None)
                        code = str(error) if isinstance(error, SandboxError) else type(error).__name__
                        # 403 alone cannot prove a plan limitation; it may be the
                        # wrong token or permissions. Require a maintainer decision.
                        suite.outcome(workflow, "access_unavailable" if status in (401, 403) else "failed")
                        report.gap(mode, workflow, code, status)
        except Exception as error:
            report.gap(mode, "identity", str(error) if isinstance(error, SandboxError) else type(error).__name__, getattr(error, "status_code", None))
        finally:
            try:
                if suite.guard.verified:
                    await suite.cleanup()
            finally:
                await suite.close()
    return report.finish(ledger)
