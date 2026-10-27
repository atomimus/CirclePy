from .base_api_client import BaseAPIClient
from .learning import live_room_payload


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
        body = live_room_payload(name, description, slug, view_type, recording_enabled,
            mute_on_join, limit_url_sharing, access_type, room_type, invited_entities_ids, payload)
        return self.post("/live_streams/rooms", data=body)
