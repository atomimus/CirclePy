from .base_api_client import BaseAPIClient


class LiveStreamsAPI(BaseAPIClient):
    def create_live_stream_room(
        self,
        name=None,
        description=None,
        slug=None,
        view_type=None,
        recording_enabled=None,
        mute_on_join=None,
        limit_url_sharing=None,
        access_type=None,
        room_type=None,
        invited_entities_ids=None,
        payload=None,
    ):
        if payload is None:
            payload = {}
            if name is not None:
                payload["name"] = name
            if description is not None:
                payload["description"] = description
            if slug is not None:
                payload["slug"] = slug
            if view_type is not None:
                payload["view_type"] = view_type
            if recording_enabled is not None:
                payload["recording_enabled"] = recording_enabled
            if mute_on_join is not None:
                payload["mute_on_join"] = mute_on_join
            if limit_url_sharing is not None:
                payload["limit_url_sharing"] = limit_url_sharing
            if access_type is not None:
                payload["access_type"] = access_type
            if room_type is not None:
                payload["room_type"] = room_type
            if invited_entities_ids is not None:
                payload["invited_entities_ids"] = invited_entities_ids
            if not payload:
                raise ValueError("Provide payload or at least one field")
        return self.post("/live_streams/rooms", data=payload)
