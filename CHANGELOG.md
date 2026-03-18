# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added - 2026-03-18
- Request capture support for pytest users:
  - `myna.last_request`
  - `myna.requests`
  - `myna.clear_requests()`
- Internal capture endpoints:
  - `GET /__myna/requests`
  - `GET /__myna/requests/last`
  - `DELETE /__myna/requests`
- Structured capture payloads for protocol assertions:
  - `method`, `path`, `query`, `headers`, `content_type`
  - `json` for JSON requests
  - `form` and `files` for multipart/form and URL-encoded requests
  - `body_text`, `body_base64` for raw payload validation

### Changed - 2026-03-18
- Pytest `myna` fixture now clears captured request history at fixture start to keep tests isolated.

