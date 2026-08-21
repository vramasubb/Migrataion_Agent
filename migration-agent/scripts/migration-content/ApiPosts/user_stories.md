# User Stories — API: Posts Contract

**Stage:** 2 — Generate User Stories  
**Derived from:** `analysis/ApiPosts/analysis.md`  
**Status:** ✅ Approved (Gate 1)

---

## US-API-01 · Retrieve All Posts

**As an** API consumer  
**I want to** retrieve the complete list of posts  
**So that** I can display or process all available content

### Acceptance Criteria

- **AC-1.1** `GET /posts` returns HTTP 200.
- **AC-1.2** The response body is an array containing exactly 100 items.

### Test Tags: `@smoke`, `@positive`

---

## US-API-02 · Retrieve a Single Post

**As an** API consumer  
**I want to** retrieve a specific post by its ID  
**So that** I can display the post details

### Acceptance Criteria

- **AC-2.1** `GET /posts/1` returns HTTP 200.
- **AC-2.2** Response contains fields `id`, `title`, `body`, and `userId`.
- **AC-2.3** The `id` field equals `1`.

### Test Tags: `@positive`

---

## US-API-03 · Handle Non-Existent Post

**As an** API consumer  
**I want to** receive a 404 when requesting a post that does not exist  
**So that** I can handle missing resources gracefully in my application

### Acceptance Criteria

- **AC-3.1** `GET /posts/9999` returns HTTP 404.

### Test Tags: `@negative`

---

## US-API-04 · Retrieve Comments for a Post

**As an** API consumer  
**I want to** retrieve comments associated with a post  
**So that** I can display the discussion thread

### Acceptance Criteria

- **AC-4.1** `GET /posts/1/comments` returns HTTP 200.
- **AC-4.2** The response is a non-empty array.
- **AC-4.3** Every item has a `postId` field equal to `1`.

### Test Tags: `@positive`

---

## US-API-05 · Filter Posts by User

**As an** API consumer  
**I want to** filter posts by userId via a query parameter  
**So that** I can retrieve only the posts authored by a specific user

### Acceptance Criteria

- **AC-5.1** `GET /posts?userId=1` returns HTTP 200.
- **AC-5.2** The response is a non-empty array.
- **AC-5.3** Every item in the array has `userId` equal to `1`.

### Test Tags: `@positive`

---

## US-API-06 · Create a New Post

**As an** API consumer  
**I want to** create a new post by sending a POST request  
**So that** I can publish new content through the API

### Acceptance Criteria

- **AC-6.1** `POST /posts` with a valid JSON body returns HTTP 201.
- **AC-6.2** Response echoes the submitted `title` and `userId`.
- **AC-6.3** Response contains an `id` field.

### Test Tags: `@positive`

---

## US-API-07 · Fully Replace a Post

**As an** API consumer  
**I want to** replace all fields of an existing post using PUT  
**So that** I can update published content atomically

### Acceptance Criteria

- **AC-7.1** `PUT /posts/1` with a full JSON body returns HTTP 200.
- **AC-7.2** Response `title` matches the submitted value.

### Test Tags: `@positive`

---

## US-API-08 · Partially Update a Post

**As an** API consumer  
**I want to** update specific fields of an existing post using PATCH  
**So that** I can make targeted edits without resending the entire resource

### Acceptance Criteria

- **AC-8.1** `PATCH /posts/1` with a partial JSON body returns HTTP 200.
- **AC-8.2** Response `title` matches the patched value.

### Test Tags: `@positive`

---

## US-API-09 · Delete a Post

**As an** API consumer  
**I want to** delete a post using DELETE  
**So that** I can remove unwanted content through the API

### Acceptance Criteria

- **AC-9.1** `DELETE /posts/1` returns HTTP 200.

### Test Tags: `@positive`

---

## US-API-10 · Validate User Contract

**As an** API consumer  
**I want to** verify that the `/users` endpoint returns all required contract fields  
**So that** downstream consumers can rely on a stable schema

### Acceptance Criteria

- **AC-10.1** `GET /users/1` returns HTTP 200.
- **AC-10.2** Response contains `id`, `name`, `email`, `address.city`, and `company.name`.
- **AC-10.3** The `id` field equals `1`.

### Test Tags: `@regression`

---

## Traceability Matrix

| User Story | AC | Selenium Scenario | Playwright Test |
|------------|-----|-------------------|-----------------|
| US-API-01 | AC-1.1, AC-1.2 | Get the full list of posts | `@smoke GET /posts returns 200 with 100 posts` |
| US-API-02 | AC-2.1–2.3 | Get a single existing post | `@positive GET /posts/1 returns the correct post` |
| US-API-03 | AC-3.1 | Get a post that does not exist | `@negative GET /posts/9999 returns 404` |
| US-API-04 | AC-4.1–4.3 | Get comments for a specific post | `@positive GET /posts/1/comments returns comments` |
| US-API-05 | AC-5.1–5.3 | Filter posts by userId | `@positive GET /posts?userId=1 filters correctly` |
| US-API-06 | AC-6.1–6.3 | Create a new post | `@positive POST /posts creates a new post` |
| US-API-07 | AC-7.1–7.2 | Update an existing post with PUT | `@positive PUT /posts/1 fully replaces a post` |
| US-API-08 | AC-8.1–8.2 | Partially update with PATCH | `@positive PATCH /posts/1 partially updates a post` |
| US-API-09 | AC-9.1 | Delete a post | `@positive DELETE /posts/1 returns 200` |
| US-API-10 | AC-10.1–10.3 | Get a single user and validate contract | `@regression GET /users/1 validates contract fields` |
