# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.2.1] - 2026-03-22

### Changed - 2026-03-22
- Structured JSON mock generation now respects common string `format` values used by Pydantic-generated schemas:
  - `date`
  - `date-time`
  - `email`
  - `uri` / `url`
  - `uuid`
- Structured JSON mock generation for `anyOf` / `oneOf` now prefers non-`null` variants instead of defaulting to nullable branches.
- Structured JSON object generation now supports dict-like schemas via `additionalProperties`, producing a small mock map with generated values from the nested schema.

## [0.2.0] - 2026-03-18

### Added - 2026-03-18
- Request capture support for pytest users:
  - `myna.last_request`
  - `myna.requests`
  - `myna.clear_requests()`
  - `myna_url` fixture alias for function-scoped `myna.base_url`
- One-shot response seeding for pytest users:
  - `myna.next_response(...)`
  - `myna.clear_seeded_responses()`
- Internal capture endpoints:
  - `GET /__myna/requests`
  - `GET /__myna/requests/last`
  - `DELETE /__myna/requests`
- Internal response-seeding endpoints:
  - `POST /__myna/responses/next`
  - `DELETE /__myna/responses`
- Structured capture payloads for protocol assertions:
  - `method`, `path`, `query`, `headers`, `content_type`
  - `json` for JSON requests
  - `form` and `files` for multipart/form and URL-encoded requests
  - `body_text`, `body_base64` for raw payload validation

### Changed - 2026-03-18
- Pytest `myna` fixture now clears captured request history at fixture start to keep tests isolated.
- Pytest `myna` fixture now clears seeded responses at fixture start to keep tests isolated.
- Added `path_with_scenario(...)` on `MynaFixture` for path-only clients that cannot pass headers.
- `myna.next_response(path=...)` now follows short-path fixture conventions (for example `"/chat/completions"`); `/v1/...` remains accepted for compatibility.
- Clarified fixture scope guidance in README (`myna`/`myna_url` vs `myna_base_url`).
