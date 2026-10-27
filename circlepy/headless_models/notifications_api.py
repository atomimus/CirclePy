from .base_api_client import BaseAPIClient
from .content import segment
from .messaging import notification_payload


class NotificationsAPI(BaseAPIClient):
    def list_notifications(self, page=None, per_page=None, sort=None, status=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        if status is not None:
            params["status"] = status
        return self.get("/notifications", params=params or None)

    def get_new_notifications_count(self):
        return self.get("/notifications/new_notifications_count")

    def reset_new_notifications_count(self):
        return self.post("/notifications/reset_new_notifications_count")

    def mark_all_as_read(self, notification_type=None, parent_notifiable=None, payload=None):
        return self.post("/notifications/mark_all_as_read",
                         data=notification_payload(notification_type, parent_notifiable, payload))

    def delete_notification(self, notification_id):
        return self.delete(f"/notifications/{segment(notification_id)}")

    def archive_notification(self, notification_id):
        return self.post(f"/notifications/{segment(notification_id)}/archive")

    def mark_notification_as_read(self, notification_id):
        return self.post(f"/notifications/{segment(notification_id)}/mark_as_read")

    def get_notification_preferences(self, medium):
        return self.get(f"/notification_preferences/{segment(medium)}")

    def update_notification_preferences(self, medium, preference_type=None, enabled=None):
        if preference_type is None or enabled is None:
            raise ValueError("Provide preference_type and enabled")
        params = {"type": preference_type, "enabled": str(enabled).lower() if isinstance(enabled, bool) else enabled}
        return self._request("PUT", f"/notification_preferences/{segment(medium)}", params=params)

    def update_notification_preferences_for_spaces(self, medium, choice=None):
        if choice is None:
            raise ValueError("Provide choice")
        params = {"choice": choice}
        return self._request("PUT", f"/notification_preferences/{segment(medium)}/spaces", params=params)

    def update_notification_preferences_for_space(self, medium, space_member_id, choice=None):
        if choice is None:
            raise ValueError("Provide choice")
        params = {"choice": choice}
        return self._request("PUT", f"/notification_preferences/{segment(medium)}/spaces/{segment(space_member_id)}", params=params)

    def get_space_notification_preferences(self, space_member_id):
        return self.get(f"/notification_preferences/space_members/{segment(space_member_id)}")
