"""Native async Admin v2 messaging, forms, moderation, leaderboards and workflows."""

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncChatPreferencesAPI(AsyncResource):
    async def update(self, payload):
        return await self._request("PUT", "/chat_preferences", json=payload_copy(payload))


class AsyncChatRoomMessageImportsAPI(AsyncResource):
    async def create(self, payload):
        """Import one historical message; Circle may add its sender to the space."""
        return await self._request("POST", "/chat_room_message_imports", json=payload_copy(payload))


class AsyncMessagesAPI(AsyncResource):
    async def create(self, payload):
        """Send to one documented destination with the caller's full rich text."""
        return await self._request("POST", "/messages", json=payload_copy(payload))


class AsyncFlaggedContentsAPI(AsyncResource):
    async def report(self, payload):
        return await self._request("POST", "/flagged_contents", json=payload_copy(payload))

    async def list_contents(self, *, page=UNSET, per_page=UNSET, status=UNSET):
        return await self._request(
            "GET", "/flagged_contents", params=query_params(
                page=page, per_page=per_page, status=status,
            ),
        )

    async def iter_contents_pages(self, *, page=1, per_page=UNSET, status=UNSET, max_pages=None):
        async for value in self._pages(
            "/flagged_contents", query_params(page=page, per_page=per_page, status=status),
            max_pages,
        ):
            yield value

    async def iter_contents(self, *, page=1, per_page=UNSET, status=UNSET, max_pages=None):
        async for value in aiter_records(self.iter_contents_pages(
            page=page, per_page=per_page, status=status, max_pages=max_pages,
        )):
            yield value


class AsyncFormsAPI(AsyncResource):
    async def get(self, form_id):
        return await self._request("GET", f"/forms/{segment(form_id)}")

    async def update(self, form_id, payload):
        """Send the flat settings and recursive elements without changing IDs."""
        return await self._request("PUT", f"/forms/{segment(form_id)}", json=payload_copy(payload))

    async def delete(self, form_id):
        return await self._request("DELETE", f"/forms/{segment(form_id)}")

    async def duplicate(self, form_id):
        return await self._request("POST", f"/forms/{segment(form_id)}/duplicate")

    async def list_forms(self, *, page=UNSET, per_page=UNSET, name=UNSET):
        return await self._request(
            "GET", "/forms", params=query_params(page=page, per_page=per_page, name=name),
        )

    async def iter_forms_pages(self, *, page=1, per_page=UNSET, name=UNSET, max_pages=None):
        async for value in self._pages(
            "/forms", query_params(page=page, per_page=per_page, name=name), max_pages,
        ):
            yield value

    async def iter_forms(self, *, page=1, per_page=UNSET, name=UNSET, max_pages=None):
        async for value in aiter_records(self.iter_forms_pages(
            page=page, per_page=per_page, name=name, max_pages=max_pages,
        )):
            yield value

    async def create_submission(self, form_id, payload):
        """Submit element IDs and string/null or string-array answers once."""
        return await self._request(
            "POST", f"/forms/{segment(form_id)}/submissions", json=payload_copy(payload),
        )

    async def list_submissions(self, form_id, *, page=UNSET, per_page=UNSET):
        return await self._request(
            "GET", f"/forms/{segment(form_id)}/submissions",
            params=query_params(page=page, per_page=per_page),
        )

    async def iter_submissions_pages(self, form_id, *, page=1, per_page=UNSET, max_pages=None):
        async for value in self._pages(
            f"/forms/{segment(form_id)}/submissions",
            query_params(page=page, per_page=per_page), max_pages,
        ):
            yield value

    async def iter_submissions(self, form_id, *, page=1, per_page=UNSET, max_pages=None):
        async for value in aiter_records(self.iter_submissions_pages(
            form_id, page=page, per_page=per_page, max_pages=max_pages,
        )):
            yield value


class AsyncGamificationAPI(AsyncResource):
    async def get_leaderboard(self, *, period=UNSET):
        """Return the full leaderboard array; omit period for all time."""
        return await self._request("GET", "/gamification/leaderboard", params=query_params(period=period))


class AsyncWorkflowsAPI(AsyncResource):
    async def get(self, workflow_id):
        """Read the full trigger/action graph with provider ordering intact."""
        return await self._request("GET", f"/workflows/{segment(workflow_id)}")

    async def activate(self, workflow_id):
        """Immediately enable an eligible dynamic workflow; no automatic retry."""
        return await self._request("PUT", f"/workflows/{segment(workflow_id)}/activate")

    async def deactivate(self, workflow_id):
        return await self._request("PUT", f"/workflows/{segment(workflow_id)}/deactivate")

    async def duplicate(self, workflow_id):
        return await self._request("POST", f"/workflows/{segment(workflow_id)}/duplicate")

    async def list_workflows(
        self, *, query=UNSET, status=UNSET, workflow_type=UNSET, page=UNSET, per_page=UNSET,
    ):
        return await self._request(
            "GET", "/workflows", params=query_params(
                query=query, status=status, workflow_type=workflow_type,
                page=page, per_page=per_page,
            ),
        )

    async def iter_workflows_pages(
        self, *, query=UNSET, status=UNSET, workflow_type=UNSET,
        page=1, per_page=UNSET, max_pages=None,
    ):
        async for value in self._pages(
            "/workflows", query_params(
                query=query, status=status, workflow_type=workflow_type,
                page=page, per_page=per_page,
            ), max_pages,
        ):
            yield value

    async def iter_workflows(
        self, *, query=UNSET, status=UNSET, workflow_type=UNSET,
        page=1, per_page=UNSET, max_pages=None,
    ):
        async for value in aiter_records(self.iter_workflows_pages(
            query=query, status=status, workflow_type=workflow_type,
            page=page, per_page=per_page, max_pages=max_pages,
        )):
            yield value
