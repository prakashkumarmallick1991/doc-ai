def get_users(status: str | None = None):
    """Return the list of users, optionally filtered by status."""
    users = [
        {"id": 1, "name": "Asha", "status": "active"},
        {"id": 2, "name": "Rahul", "status": "pending"},
        {"id": 3, "name": "Nina", "status": "inactive"},
    ]

    if status is None:
        return users

    return [user for user in users if user["status"] == status]
