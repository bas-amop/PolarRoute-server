# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- This changelog!

### Changed
- Restricted upper limit of Django support to version 5.2
- Name of maintainer from David Wilby to David Wyld.
- Moved the docker volume for the `db` service to a managed volume instead of a bind-mount.

#### `request_route`
- utility move to its own module.

### Fixed
- `request_route` utility now does not wait for the delay period before the first status request, only after receipt of a 'PENDING' job status.

### Removed
- Support for python 3.9
- Support for Django < 5.2


## 0.2.2 - 2025-10-14

### Added
- Optimisation metrics exposure (time, fuel, distance) in route responses.
- Job ID inclusion in `recent_routes` response for better tracking.
- Recent routes output validation tests.

### Changed
- **Breaking**: Route response structure now consistent regardless of optimisation types available.
- Improved `recent_routes` endpoint performance by removing repeated job status calls and heavy JSON processing.
- Route calculated timestamp only applied when both route optimisations are complete.
- Re-coupled `recent_routes` status to Celery state using database instead of broker for better reliability/performance.
- Removed top-level metadata duplication in route responses.

### Fixed
- Performance issues with `recent_routes` endpoint loading unnecessary data.

## 0.2.1 - 2025-09-18

### Added
- Response refactor for improved error code consistency.
- New `responses.py` module for centralized response handling.
- Response validation tests (`test_responses.py`).
- Location management functionality.
- Job status schema with all possible Celery states.
- Vehicle management with CRUD operations.
- Vehicle configuration validation using PolarRoute validator.
- Location fixtures for standard locations (Bird Island, Falklands, Halley, Rothera, etc.).
- Swagger UI served alongside the application.

### Changed
- **Breaking**: Separated job and route endpoints - routes now accessed via job workflow.
- **Breaking**: Route cancellation moved from route endpoint to job endpoint.
- Unified error responses across all endpoints for consistency.
- Route model now cascades deletion when job is deleted.
- Vehicle model expanded with additional SDA properties (`beam`, `hull_type`, `force_limit`).
- LocationView refactored to `LocationViewSet`.

### Fixed
- Route schema missing from API documentation after merge conflicts.
- Inconsistent error response formats across endpoints.
- Route cancellation bug where deletion didn't work properly.

### Removed
- Redundant "no mesh available" response variations - now unified.
- Separate route cancellation endpoint (moved to job endpoint).

## 0.2.0 - 2025-02-19

## 0.1.6 - 2024-12-09

## 0.1.5 - 2024-12-05

## 0.1.4 - 2024-11-28

## 0.1.3 - 2024-11-26

## 0.1.2 - 2024-11-25

## 0.1.1 - 2024-11-20

## 0.1.0 - 2024-11-20

