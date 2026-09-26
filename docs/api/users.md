# Users API

## GET /users

Returns a list of users.

### Query parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| status | string | No | Filters users by current status (`active`, `inactive`, `pending`). |

### Example

```http
GET /users?status=active
```

This returns only active users.
