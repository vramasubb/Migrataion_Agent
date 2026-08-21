# Test Data — API: Posts Contract

**Stage:** 1 — Analyze & Extract  
**Source:** `features/api_posts.feature` (inline docstrings)

---

## Static IDs

| Resource | ID | Used in |
|----------|----|---------|
| Post | `1` | GET, PUT, PATCH, DELETE |
| Post (non-existent) | `9999` | GET → 404 |
| User | `1` | GET /users/1, userId filter, POST body |

## POST /posts body

```json
{
  "title": "Automation is fun",
  "body": "Selenium + Cucumber + RestAssured working together nicely.",
  "userId": 1
}
```

## PUT /posts/1 body

```json
{ "id": 1, "title": "Updated title via PUT", "body": "Updated body content", "userId": 1 }
```

## PATCH /posts/1 body

```json
{ "title": "Patched title only" }
```

## Expected Sizes

| Endpoint | Expected array length |
|----------|-----------------------|
| GET /posts | 100 |
| GET /posts/1/comments | > 0 (non-empty) |
| GET /posts?userId=1 | > 0 (non-empty) |

## Notes

- Write operations (POST/PUT/PATCH/DELETE) are **simulated** by JSONPlaceholder.
  They return realistic HTTP status codes and echo the body, but changes are not persisted.
- Tests are therefore **idempotent** — safe to run repeatedly without cleanup.
