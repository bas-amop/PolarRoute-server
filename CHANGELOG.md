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


## 0.2.2 - 14/10/2025

## 0.2.1 - 18/09/2025

## 0.2.0 - 19/02/2025

## 0.1.6 - 09/12/2024

## 0.1.5 - 05/12/2024

## 0.1.4 - 28/11/2024

## 0.1.3 - 26/11/2024

## 0.1.2 - 25/11/2024

## 0.1.1 - 20/11/2024

## 0.1.0 - 20/11/2024
