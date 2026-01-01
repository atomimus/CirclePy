from .base_api_client import BaseAPIClient


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
        if payload is None:
            data = {}
            if notification_type is not None:
                data["notification_type"] = notification_type
            if parent_notifiable is not None:
                data["parent_notifiable"] = parent_notifiable
            payload = data
        return self.post("/notifications/mark_all_as_read", data=payload or {})

    def delete_notification(self, notification_id):
        return self.delete(f"/notifications/{notification_id}")

    def archive_notification(self, notification_id):
        return self.post(f"/notifications/{notification_id}/archive")

    def mark_notification_as_read(self, notification_id):
        return self.post(f"/notifications/{notification_id}/mark_as_read")

    def get_notification_preferences(self, medium):
        return self.get(f"/notification_preferences/{medium}")

    def update_notification_preferences(self, medium, preference_type=None, enabled=None):
        if preference_type is None or enabled is None:
            raise ValueError("Provide preference_type and enabled")
        params = {"type": preference_type, "enabled": enabled}
        return self._request("PUT", f"/notification_preferences/{medium}", params=params)

    def update_notification_preferences_for_spaces(self, medium, choice=None):
        if choice is None:
            raise ValueError("Provide choice")
        params = {"choice": choice}
        return self._request("PUT", f"/notification_preferences/{medium}/spaces", params=params)

    def update_notification_preferences_for_space(self, medium, space_member_id, choice=None):
        if choice is None:
            raise ValueError("Provide choice")
        params = {"choice": choice}
        return self._request("PUT", f"/notification_preferences/{medium}/spaces/{space_member_id}", params=params)

    def get_space_notification_preferences(self, space_member_id):
        return self.get(f"/notification_preferences/space_members/{space_member_id}")
