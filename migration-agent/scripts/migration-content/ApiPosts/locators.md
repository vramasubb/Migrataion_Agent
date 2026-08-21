# Endpoint Map — API: Posts Contract

**Stage:** 1 — Analyze & Extract  
**Source:** `utils/ApiUtils.java`

---

## Base URL

| Config key | Value |
|------------|-------|
| `API_BASE_URL` | `https://jsonplaceholder.typicode.com` |

## Endpoints

| Method | Path | Request body | Expected status | Notes |
|--------|------|-------------|-----------------|-------|
| GET | `/posts` | None | 200 | Returns array of 100 posts |
| GET | `/posts/{id}` | None | 200 / 404 | 404 for non-existent id |
| GET | `/posts/{id}/comments` | None | 200 | Nested resource |
| GET | `/posts?userId={n}` | None | 200 | Query-param filter |
| POST | `/posts` | `{title, body, userId}` | 201 | Simulated — not persisted |
| PUT | `/posts/{id}` | `{id, title, body, userId}` | 200 | Full replace |
| PATCH | `/posts/{id}` | `{title}` | 200 | Partial update |
| DELETE | `/posts/{id}` | None | 200 | Simulated |
| GET | `/users/{id}` | None | 200 | Contract validation |

## Request Bodies

### POST /posts
```json
{
  "title": "Automation is fun",
  "body": "Selenium + Cucumber + RestAssured working together nicely.",
  "userId": 1
}
```

### PUT /posts/1
```json
{ "id": 1, "title": "Updated title via PUT", "body": "Updated body content", "userId": 1 }
```

### PATCH /posts/1
```json
{ "title": "Patched title only" }
```

## Response Schema (POST contract)

| Field | Type | Rule |
|-------|------|------|
| `id` | integer | Must be present (auto-assigned by server) |
| `title` | string | Must echo the submitted title |
| `userId` | integer | Must echo the submitted userId |
