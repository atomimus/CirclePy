from .base_api_client import BaseAPIClient
from .learning import flagged_payload


class FlaggedContentsAPI(BaseAPIClient):
    def create_flagged_content(
        self,
        flagged_content=None,
        payload=None,
        flagged_contentable_id=None,
        flagged_contentable_type=None,
        reported_reason_type=None,
        reported_reason_body=None,
    ):
        body = flagged_payload(flagged_content, payload, flagged_contentable_id,
            flagged_contentable_type, reported_reason_type, reported_reason_body)
        return self.post("/flagged_contents", data=body)
