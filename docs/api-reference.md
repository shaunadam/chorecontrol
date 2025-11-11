# ChoreControl API Reference

This document provides a complete reference for the ChoreControl REST API.

## Base URL

When running in Home Assistant, the API is available at:

```
http://homeassistant.local:PORT/api
```

> **TODO**: Update with actual base URL when add-on is deployed

## Authentication

ChoreControl uses Home Assistant ingress authentication. All requests must include the ingress headers set by Home Assistant.

**Headers**:

- `X-Ingress-User`: Home Assistant user ID
- `X-Ingress-Name`: User's display name

> **TODO**: Complete when authentication is implemented

## Response Format

All API responses follow this format:

### Success Response

```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

## Common HTTP Status Codes

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server error

---

## API Endpoints

### Health Check

#### `GET /health`

Check if the API is running and database is accessible.

**Response**:

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.1.0"
}
```

> **TODO**: Implement health check endpoint

---

## Users

### List Users

#### `GET /api/users`

Get a list of all users.

**Query Parameters**:

- `role` (optional): Filter by role (`parent` or `kid`)

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "ha_user_id": "abc123",
      "username": "Kid1",
      "role": "kid",
      "points": 45,
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2025-11-10T15:30:00Z"
    }
  ]
}
```

> **TODO**: Implement GET /api/users

### Create User

#### `POST /api/users`

Create a new user.

**Request Body**:

```json
{
  "ha_user_id": "abc123",
  "username": "Kid1",
  "role": "kid",
  "points": 0
}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "ha_user_id": "abc123",
    "username": "Kid1",
    "role": "kid",
    "points": 0,
    "created_at": "2025-11-01T10:00:00Z"
  }
}
```

> **TODO**: Implement POST /api/users

### Get User

#### `GET /api/users/{id}`

Get details for a specific user.

**Response**: Same as create user response

> **TODO**: Implement GET /api/users/{id}

### Update User

#### `PUT /api/users/{id}`

Update user details.

**Request Body**: Same as create user

**Response**: Same as create user response

> **TODO**: Implement PUT /api/users/{id}

### Get User Points

#### `GET /api/users/{id}/points`

Get user's current points and recent history.

**Response**:

```json
{
  "success": true,
  "data": {
    "current_points": 45,
    "history": [
      {
        "id": 10,
        "points_delta": 5,
        "reason": "Approved chore: Take out trash",
        "created_at": "2025-11-10T15:30:00Z"
      }
    ]
  }
}
```

> **TODO**: Implement GET /api/users/{id}/points

---

## Chores

### List Chores

#### `GET /api/chores`

Get a list of all chores.

**Query Parameters**:

- `active` (optional): Filter by active status (`true` or `false`)
- `assigned_to` (optional): Filter by assigned user ID

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Take out trash",
      "description": "Roll both bins to curb",
      "points": 5,
      "recurrence_type": "simple",
      "recurrence_pattern": "{\"type\": \"weekly\", \"days\": [1]}",
      "assignment_type": "individual",
      "requires_approval": true,
      "is_active": true,
      "created_at": "2025-11-01T10:00:00Z"
    }
  ]
}
```

> **TODO**: Implement GET /api/chores

### Create Chore

#### `POST /api/chores`

Create a new chore.

**Request Body**:

```json
{
  "name": "Take out trash",
  "description": "Roll both bins to curb",
  "points": 5,
  "recurrence_type": "simple",
  "recurrence_pattern": "{\"type\": \"weekly\", \"days\": [1]}",
  "assignment_type": "individual",
  "requires_approval": true,
  "assigned_users": [1, 2]
}
```

**Response**: Same as list chores item

> **TODO**: Implement POST /api/chores

### Get Chore

#### `GET /api/chores/{id}`

Get details for a specific chore.

**Response**: Same as list chores item

> **TODO**: Implement GET /api/chores/{id}

### Update Chore

#### `PUT /api/chores/{id}`

Update chore details.

**Request Body**: Same as create chore

**Response**: Same as list chores item

> **TODO**: Implement PUT /api/chores/{id}

### Delete Chore

#### `DELETE /api/chores/{id}`

Soft delete a chore (sets `is_active = false`).

**Response**:

```json
{
  "success": true,
  "message": "Chore deleted successfully"
}
```

> **TODO**: Implement DELETE /api/chores/{id}

---

## Chore Instances

### List Instances

#### `GET /api/instances`

Get a list of chore instances.

**Query Parameters**:

- `status` (optional): Filter by status (`assigned`, `claimed`, `approved`, `rejected`)
- `user_id` (optional): Filter by assigned user
- `start_date` (optional): Filter instances due on or after this date
- `end_date` (optional): Filter instances due on or before this date

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "chore_id": 1,
      "chore_name": "Take out trash",
      "due_date": "2025-11-11",
      "status": "claimed",
      "claimed_by": 1,
      "claimed_at": "2025-11-11T08:00:00Z",
      "points_awarded": null
    }
  ]
}
```

> **TODO**: Implement GET /api/instances

### Get Instance

#### `GET /api/instances/{id}`

Get details for a specific instance.

**Response**: Same as list instances item

> **TODO**: Implement GET /api/instances/{id}

### Claim Instance

#### `POST /api/instances/{id}/claim`

Kid claims a chore as completed.

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "claimed",
    "claimed_by": 1,
    "claimed_at": "2025-11-11T08:00:00Z"
  }
}
```

> **TODO**: Implement POST /api/instances/{id}/claim

### Approve Instance

#### `POST /api/instances/{id}/approve`

Parent approves a claimed chore.

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "approved",
    "approved_by": 3,
    "approved_at": "2025-11-11T18:00:00Z",
    "points_awarded": 5
  }
}
```

> **TODO**: Implement POST /api/instances/{id}/approve

### Reject Instance

#### `POST /api/instances/{id}/reject`

Parent rejects a claimed chore.

**Request Body**:

```json
{
  "reason": "Trash cans not placed correctly"
}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "rejected",
    "rejected_by": 3,
    "rejected_at": "2025-11-11T18:00:00Z",
    "rejection_reason": "Trash cans not placed correctly"
  }
}
```

> **TODO**: Implement POST /api/instances/{id}/reject

---

## Rewards

### List Rewards

#### `GET /api/rewards`

Get a list of all rewards.

**Query Parameters**:

- `active` (optional): Filter by active status

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Ice cream trip",
      "description": "Go get ice cream together",
      "points_cost": 20,
      "cooldown_days": 7,
      "is_active": true
    }
  ]
}
```

> **TODO**: Implement GET /api/rewards

### Create Reward

#### `POST /api/rewards`

Create a new reward.

**Request Body**:

```json
{
  "name": "Ice cream trip",
  "description": "Go get ice cream together",
  "points_cost": 20,
  "cooldown_days": 7
}
```

**Response**: Same as list rewards item

> **TODO**: Implement POST /api/rewards

### Update Reward

#### `PUT /api/rewards/{id}`

Update reward details.

**Request Body**: Same as create reward

**Response**: Same as list rewards item

> **TODO**: Implement PUT /api/rewards/{id}

### Delete Reward

#### `DELETE /api/rewards/{id}`

Soft delete a reward.

**Response**:

```json
{
  "success": true,
  "message": "Reward deleted successfully"
}
```

> **TODO**: Implement DELETE /api/rewards/{id}

### Claim Reward

#### `POST /api/rewards/{id}/claim`

Kid claims a reward.

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "reward_id": 1,
    "user_id": 1,
    "points_spent": 20,
    "claimed_at": "2025-11-11T12:00:00Z"
  }
}
```

**Errors**:

- `INSUFFICIENT_POINTS`: Not enough points
- `REWARD_ON_COOLDOWN`: Must wait before claiming again
- `REWARD_LIMIT_REACHED`: Max claims exceeded

> **TODO**: Implement POST /api/rewards/{id}/claim

---

## Points

### Adjust Points

#### `POST /api/points/adjust`

Manually adjust a user's points (parent only).

**Request Body**:

```json
{
  "user_id": 1,
  "points_delta": 10,
  "reason": "Bonus for being helpful"
}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "new_balance": 55,
    "points_delta": 10,
    "reason": "Bonus for being helpful"
  }
}
```

> **TODO**: Implement POST /api/points/adjust

### Get Points History

#### `GET /api/points/history/{user_id}`

Get points history for a user.

**Query Parameters**:

- `limit` (optional): Number of records to return (default: 50)
- `offset` (optional): Pagination offset

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "user_id": 1,
      "points_delta": 5,
      "reason": "Approved chore: Take out trash",
      "created_at": "2025-11-10T15:30:00Z"
    }
  ]
}
```

> **TODO**: Implement GET /api/points/history/{user_id}

---

## Calendar

### Get ICS Feed

#### `GET /api/calendar/{user_id}.ics`

Get ICS calendar feed for a user's chores.

**Response**: ICS format calendar file

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ChoreControl//EN
...
END:VCALENDAR
```

> **TODO**: Implement GET /api/calendar/{user_id}.ics

---

## Dashboard

### Kid Dashboard

#### `GET /api/dashboard/kid/{user_id}`

Get dashboard data for a kid.

**Response**:

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "Kid1",
      "points": 45
    },
    "chores_today": [...],
    "upcoming_chores": [...],
    "available_rewards": [...],
    "recent_activity": [...]
  }
}
```

> **TODO**: Implement GET /api/dashboard/kid/{user_id}

### Parent Dashboard

#### `GET /api/dashboard/parent`

Get dashboard data for parents.

**Response**:

```json
{
  "success": true,
  "data": {
    "pending_approvals": [...],
    "kids_overview": [...],
    "recent_activity": [...]
  }
}
```

> **TODO**: Implement GET /api/dashboard/parent

---

## Webhooks and Events

> **TODO**: Document webhook/event system when implemented

---

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_INPUT` | Request data validation failed |
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | Insufficient permissions |
| `NOT_FOUND` | Resource doesn't exist |
| `INSUFFICIENT_POINTS` | Not enough points for operation |
| `REWARD_ON_COOLDOWN` | Reward can't be claimed yet |
| `REWARD_LIMIT_REACHED` | Reward claim limit exceeded |
| `INVALID_STATUS_TRANSITION` | Invalid chore status change |
| `DATABASE_ERROR` | Database operation failed |

> **TODO**: Add more error codes as they're defined

---

## Rate Limiting

> **TODO**: Document rate limiting when implemented

---

## Versioning

The API follows semantic versioning. Breaking changes will result in a new major version.

Current version: `v1` (implicit in all endpoints)

> **TODO**: Implement API versioning

---

## OpenAPI / Swagger

Interactive API documentation is available at:

```
http://homeassistant.local:PORT/docs
```

> **TODO**: Generate and link OpenAPI spec

---

## Examples

### Python Example

```python
import requests

# TODO: Add Python example
```

### JavaScript Example

```javascript
// TODO: Add JavaScript example
```

### Home Assistant Automation Example

```yaml
# TODO: Add HA automation example using REST commands
```

---

## Support

- **Issues**: [Report bugs](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [Ask questions](https://github.com/shaunadam/chorecontrol/discussions)
