# CHANGELOG.md

## 2025-10-17

### Added
- Introduced `find_by_product_id(product_id)` method in the Promotion model.
- Added consistent return types for query methods:
  - Single-item queries (`find(id)`) return a single object or `None`.
  - Multiple-item queries (`find_by_name`, `find_by_product_id`, `find_by_promotion_type`) return lists.
- Added support for multiple query filters in the `GET /promotions` endpoint (`?id`, `?name`, `?product_id`, `?promotion_type`).
  - Applied query priority order: `id` > `name` > `product_id` > `promotion_type`.
- Added backward compatibility: `find_by_category` alias method now internally calls `find_by_product_id`.
- Added stricter validation for update operations (`PUT /promotions/<id>`): returns HTTP 400 if payload `id` does not match URL path.
- Improved error handling, allowing `Content-Type` header validation to accept charset parameters (e.g., `application/json; charset=utf-8`).

### Changed
- Renamed ambiguous query parameter `category` to explicit `product_id`.
- Updated `find_by_name` method to return a list instead of a query object.

### Removed
- Removed `find_by_id` method (previously returned a single-element list or empty list). Use `find(id)` instead.

### Fixed
- Ensured robust handling of non-integer and invalid inputs in query methods; invalid inputs now return empty lists or `None` instead of errors.
- Unified database transaction handling in `create`, `update`, and `delete` methods; rollback and raise clear business exceptions if errors occur.

### Example Usage

#### Model queries
```python
# Retrieve by ID (single object or None)
promotion = Promotion.find(42)
if promotion:
    print(promotion.name)

# Retrieve by name (list)
promotions_by_name = Promotion.find_by_name("NYU Demo")
for promo in promotions_by_name:
    print(promo.id)

# Retrieve by product_id (list)
promotions_by_product = Promotion.find_by_product_id("123")
print(len(promotions_by_product))

# Retrieve by promotion_type (list)
promotions_bogo = Promotion.find_by_promotion_type("Buy One Get One")
````

#### HTTP API examples

```bash
# Filter promotions by promotion_type
curl "http://localhost:8080/promotions?promotion_type=Buy%20One%20Get%20One"

# Filter promotions by product_id
curl "http://localhost:8080/promotions?product_id=123"

# Filter promotions by name
curl "http://localhost:8080/promotions?name=OnlyMe"

# Filter promotions by id (single item in array or empty array)
curl "http://localhost:8080/promotions?id=42"

# Create a promotion (charset in Content-Type is accepted)
curl -X POST "http://localhost:8080/promotions" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"name":"NYU Demo","promotion_type":"AMOUNT_OFF","value":10,"product_id":123,"start_date":"2025-10-01","end_date":"2025-10-31"}'

# Update a promotion (HTTP 400 if URL and payload IDs mismatch)
curl -X PUT "http://localhost:8080/promotions/10" \
  -H "Content-Type: application/json" \
  -d '{"id":11,"name":"Mismatch","promotion_type":"AMOUNT_OFF","value":10,"product_id":123,"start_date":"2025-10-01","end_date":"2025-10-31"}'

# Delete a promotion (204 if exists, 404 if not)
curl -i -X DELETE "http://localhost:8080/promotions/42"
```



## 2025-10-18

### Added

* **New Query Parameter:** `active=true` for `/promotions` endpoint.

  * Allows marketing managers to retrieve all **currently active promotions** based on the server’s current date.
  * Active promotions are defined as those where `start_date <= today <= end_date`.
  * Returns only promotions active on the current day with `200 OK` response.

* **New Model Method:**

  * `Promotion.find_active(on_date=None)` — retrieves all active promotions as a list.
  * Supports optional `on_date` parameter for testing or future scheduling logic.

### Updated

* **Routes (`list_promotions`)**

  * Added new branch to handle `?active=true` query parameter.
  * Defined clear query priority: `id > active > name > product_id > promotion_type > all`.

* **Tests**

  * Added unit and integration tests covering:

    * Active promotions retrieval.

## 2025-10-18

### Added

* **Action endpoint:** `PUT /promotions/{id}/deactivate` to **immediately** stop a running promotion while preserving history.

  * Sets `end_date` to **yesterday** (`today - 1 day`, server date) so, under the inclusive active-window rule (`start_date <= today <= end_date`), the promo is **excluded from “today’s” active list** right away.
  * **Idempotent & safe:** uses `end_date = min(current_end_date, yesterday)` so repeated calls don’t push the date forward, and already expired promos are **not** extended.
  * **No request body** required; returns **200 OK** with the updated resource.
  * Returns **404 Not Found** if the promotion doesn’t exist.

### Rationale

* Managers need to halt flawed or harmful campaigns **immediately** without deleting records.
* Using `yesterday` avoids changing global “active” semantics and achieves instant-effect deactivation with **minimal blast radius**.

### API Contract

* **Request:**
  `PUT /promotions/{id}/deactivate`
* **Success (200):**

  ```json
  {
    "id": 123,
    "name": "Promo X",
    "promotion_type": "Percentage off",
    "value": 10,
    "product_id": 456,
    "start_date": "2025-10-10",
    "end_date": "2025-10-17"   // yesterday (server date - 1)
  }
  ```
* **Errors:**

  * `404 Not Found` – promotion id does not exist
  * `400 Bad Request` – validation/update failure (unlikely in normal use)

### Related Behavior

* `GET /promotions?active=true` uses **server date** and inclusive bounds; after deactivation, the promotion **no longer appears** in the active list **today**.

### Tests

* Added:

  * `test_deactivate_promotion_sets_end_date_to_yesterday_and_excludes_from_active`
  * `test_deactivate_is_idempotent_and_never_extends`
  * `test_deactivate_promotion_not_found`
