from .base_api_client import BaseAPIClient


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
        if payload is None:
            if flagged_content is None:
                required = [
                    flagged_contentable_id,
                    flagged_contentable_type,
                    reported_reason_type,
                    reported_reason_body,
                ]
                if any(value is None for value in required):
                    raise ValueError("Provide flagged_content or all flagged_content fields")
                flagged_content = {
                    "flagged_contentable_id": flagged_contentable_id,
                    "flagged_contentable_type": flagged_contentable_type,
                    "reported_reason_type": reported_reason_type,
                    "reported_reason_body": reported_reason_body,
                }
            payload = {"flagged_content": flagged_content}
        return self.post("/flagged_contents", data=payload)
