# Documentation PR Proposal

## Summary
The users API now supports a status filter and the query contract has changed.

## Affecting documents
- docs/api/users.md: The API contract and parameter documentation are directly affected.
- docs/guides/user-management.md: The user management guide references available filtering behavior and examples.

## Draft content
### GET /users

Use the `status` query parameter to filter users by lifecycle state.

Example request:

```http
GET /users?status=active
```

This parameter is optional. If omitted, all users are returned.

## PR title
Update users API documentation for status filtering

## PR body
## Documentation update

### Summary
This PR updates the API documentation for the users endpoint after the status filter change.

### Proposed content
### GET /users

Use the `status` query parameter to filter users by lifecycle state.

Example request:

```http
GET /users?status=active
```

This parameter is optional. If omitted, all users are returned.

### Validation
- Markup reviewed
- Links checked
- Docs build validated
