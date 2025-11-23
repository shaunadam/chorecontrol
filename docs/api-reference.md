# ChoreControl API Reference

This document provides a complete reference for the ChoreControl REST API.

## Base URL

When running locally for development:
```
http://localhost:8099/api
```

When running as a Home Assistant add-on:
```
http://homeassistant.local:8099/api
```

## Authentication

ChoreControl uses Home Assistant ingress authentication. All requests must include the ingress headers set by Home Assistant.

**Headers**:

- `X-Ingress-User`: Home Assistant user ID (required)

For local development/testing, you can set this header manually:
```bash
curl -H "X-Ingress-User: test-parent-1" http://localhost:8099/api/users
```

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

### Get User

#### `GET /api/users/{id}`

Get details for a specific user.

**Response**: Same as create user response

### Update User

#### `PUT /api/users/{id}`

Update user details.

**Request Body**: Same as create user

**Response**: Same as create user response

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
      "recurrence_pattern": "{\"type\": \"weekly\", \"days_of_week\": [1]}",
      "assignment_type": "individual",
      "requires_approval": true,
      "is_active": true,
      "created_at": "2025-11-01T10:00:00Z"
    }
  ]
}
```

### Create Chore

#### `POST /api/chores`

Create a new chore.

**Request Body**:

```json
{
  "name": "Take out trash",
  "description": "Roll both bins to curb",
  "points": 5,
  "recurrence_pattern": {"type": "weekly", "days_of_week": [1]},
  "assignment_type": "individual",
  "requires_approval": true,
  "assigned_users": [1, 2]
}
```

**Response**: Same as list chores item

### Get Chore

#### `GET /api/chores/{id}`

Get details for a specific chore.

**Response**: Same as list chores item

### Update Chore

#### `PUT /api/chores/{id}`

Update chore details.

**Request Body**: Same as create chore

**Response**: Same as list chores item

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

### Get Chore Instances

#### `GET /api/chores/{id}/instances`

Get all instances for a specific chore.

**Query Parameters**:

- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Response**: Paginated list of instances

---

## Chore Instances

### List Instances

#### `GET /api/instances`

Get a list of chore instances.

**Query Parameters**:

- `status` (optional): Filter by status (`assigned`, `claimed`, `approved`, `rejected`, `missed`)
- `user_id` (optional): Filter by assigned user
- `chore_id` (optional): Filter by chore
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
      "claimed_late": false,
      "points_awarded": null
    }
  ]
}
```

### Get Instance

#### `GET /api/instances/{id}`

Get details for a specific instance.

**Response**: Same as list instances item

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
    "claimed_at": "2025-11-11T08:00:00Z",
    "claimed_late": false
  }
}
```

### Approve Instance

#### `POST /api/instances/{id}/approve`

Parent approves a claimed chore.

**Request Body** (optional):

```json
{
  "points": 10
}
```

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

### Unclaim Instance

#### `POST /api/instances/{id}/unclaim`

Unclaim a previously claimed chore (returns to assigned status).

**Response**: Updated instance data

### Reassign Instance

#### `POST /api/instances/{id}/reassign`

Reassign an instance to a different user.

**Request Body**:

```json
{
  "user_id": 2
}
```

**Response**: Updated instance data

### Get Due Today

#### `GET /api/instances/due-today`

Get all instances due today.

**Response**: List of instances

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
      "requires_approval": false,
      "is_active": true
    }
  ]
}
```

### Create Reward

#### `POST /api/rewards`

Create a new reward.

**Request Body**:

```json
{
  "name": "Ice cream trip",
  "description": "Go get ice cream together",
  "points_cost": 20,
  "cooldown_days": 7,
  "requires_approval": false
}
```

**Response**: Same as list rewards item

### Get Reward

#### `GET /api/rewards/{id}`

Get details for a specific reward.

**Response**: Same as list rewards item

### Update Reward

#### `PUT /api/rewards/{id}`

Update reward details.

**Request Body**: Same as create reward

**Response**: Same as list rewards item

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
    "status": "approved",
    "claimed_at": "2025-11-11T12:00:00Z"
  }
}
```

**Errors**:

- `INSUFFICIENT_POINTS`: Not enough points
- `REWARD_ON_COOLDOWN`: Must wait before claiming again
- `REWARD_LIMIT_REACHED`: Max claims exceeded

### Unclaim Reward

#### `POST /api/rewards/claims/{claim_id}/unclaim`

Unclaim a pending reward (refunds points).

**Response**: Updated claim data

### Approve Reward Claim

#### `POST /api/rewards/claims/{claim_id}/approve`

Approve a pending reward claim.

**Response**: Updated claim data

### Reject Reward Claim

#### `POST /api/rewards/claims/{claim_id}/reject`

Reject a pending reward claim (refunds points).

**Request Body**:

```json
{
  "reason": "Not available this week"
}
```

**Response**: Updated claim data

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

---

## Webhooks and Events

ChoreControl sends webhook events to Home Assistant for real-time updates.

### Event Types

| Event | Description |
|-------|-------------|
| `chore_instance_created` | New instance created (due today or NULL) |
| `chore_instance_claimed` | Kid claims a chore |
| `chore_instance_approved` | Parent approves (or auto-approval) |
| `chore_instance_rejected` | Parent rejects |
| `points_awarded` | Any point change |
| `reward_claimed` | Kid claims a reward |
| `reward_approved` | Parent approves reward claim |
| `reward_rejected` | Parent rejects or claim expires |

### Event Format

```json
{
  "event": "chore_instance_claimed",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "instance_id": 42,
    "chore_name": "Take out trash",
    "user_id": 3,
    "username": "Emma",
    "points": 5
  }
}
```

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

---

## Support

- **Issues**: [Report bugs](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [Ask questions](https://github.com/shaunadam/chorecontrol/discussions)
