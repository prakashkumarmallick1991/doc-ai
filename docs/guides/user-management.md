# User management

The user management experience supports filtering by status.

## Status filtering

Use the `status` parameter on the users API to limit results to a specific lifecycle state.

### Example

```http
GET /users?status=pending
```

This is useful for listing accounts awaiting review.
