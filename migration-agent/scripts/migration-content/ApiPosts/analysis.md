# Feature Analysis — API: Posts Contract

**Stage:** 1 — Analyze & Extract  
**Source file:** `src/test/resources/features/api_posts.feature`  
**Step defs:** `stepdefinitions/ApiSteps.java`  
**API utility:** `utils/ApiUtils.java`  
**Context:** `context/ScenarioContext.java`  
**Generated:** Stage 1 of migration pipeline

---

## Test Intent Summary

This feature validates the JSONPlaceholder `/posts` REST API contract, covering all standard CRUD
operations (GET, POST, PUT, PATCH, DELETE) plus a user-contract check on `/users/1`.

---

## Scenario Inventory

| # | Scenario | Tags | HTTP Method | Endpoint |
|---|----------|------|-------------|----------|
| 1 | Get the full list of posts | @smoke @positive | GET | `/posts` |
| 2 | Get a single existing post | @positive | GET | `/posts/1` |
| 3 | Get a post that does not exist | @negative | GET | `/posts/9999` |
| 4 | Get comments for a specific post | @positive | GET | `/posts/1/comments` |
| 5 | Filter posts by userId | @positive | GET | `/posts?userId=1` |
| 6 | Create a new post | @positive | POST | `/posts` |
| 7 | Update an existing post with PUT | @positive | PUT | `/posts/1` |
| 8 | Partially update an existing post with PATCH | @positive | PATCH | `/posts/1` |
| 9 | Delete a post | @positive | DELETE | `/posts/1` |
| 10 | Get a single user and validate contract fields | @regression | GET | `/users/1` |
| **Total** | | | | **10 scenarios** |

---

## Step Definition Mapping

| Cucumber step | Java method | REST Assured call |
|---------------|-------------|-------------------|
| `I send a GET request to …` | `ApiUtils.get(endpoint)` | `given().get(BASE + endpoint)` |
| `I send a POST request to … with body:` | `ApiUtils.post(endpoint, body)` | `given().body(json).post(…)` |
| `I send a PUT request to … with body:` | `ApiUtils.put(endpoint, body)` | `given().body(json).put(…)` |
| `I send a PATCH request to … with body:` | `ApiUtils.patch(endpoint, body)` | `given().body(json).patch(…)` |
| `I send a DELETE request to …` | `ApiUtils.delete(endpoint)` | `given().delete(…)` |
| `the response status code should be …` | `response.statusCode()` | integer assert |
| `the response field … should equal …` | `response.jsonPath().get(path)` | String.valueOf assert |
| `the response should contain field …` | `response.jsonPath().get(path)` | not-null assert |
| `the response array size should be …` | `jsonPath.getList("$").size()` | int assert |
| `every item in the response array should have field … equal to …` | `jsonPath.getList(field)` | for-each assert |

---

## Assertions Extracted

| Scenario | Status code | Additional assertions |
|----------|-------------|----------------------|
| GET /posts | 200 | Array length == 100 |
| GET /posts/1 | 200 | `id`=="1", has `title`, `body`, `userId` |
| GET /posts/9999 | 404 | None |
| GET /posts/1/comments | 200 | Array not empty, `[0].postId`=="1" |
| GET /posts?userId=1 | 200 | All items have `userId`=="1" |
| POST /posts | 201 | `title`=="Automation is fun", `userId`=="1", has `id` |
| PUT /posts/1 | 200 | `title`=="Updated title via PUT" |
| PATCH /posts/1 | 200 | `title`=="Patched title only" |
| DELETE /posts/1 | 200 | None |
| GET /users/1 | 200 | `id`=="1", has `name`, `email`, `address.city`, `company.name` |

---

## Migration Notes

- **JSONPlaceholder** simulates writes — POST/PUT/PATCH/DELETE return realistic responses but are **not persisted**.
- REST Assured `ScenarioContext` DI → replaced by Playwright's `request` fixture (per-test isolation).
- `ApiUtils.get(endpoint)` with `BASE_URL` → `request.get(\`\${API_BASE_URL}\${endpoint}\`)`.
- `jsonPath.getList("$")` (root array) → `await response.json()` + `Array.isArray()` check.
- Nested path `address.city` → `expect(body).toHaveProperty('address.city')`.
