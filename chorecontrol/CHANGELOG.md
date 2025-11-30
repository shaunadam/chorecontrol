# Changelog

All notable changes to the ChoreControl add-on will be documented in this file.

## [0.2.1] - 2025-11-30

### Fixed
- Enhanced logging to diagnose SUPERVISOR_TOKEN availability at module load time
- Added helpful diagnostics when token is not available
- Improved log messages to help identify Python bytecode cache issues

## [0.2.0] - 2025-11-30

### Added
- Home Assistant Supervisor API access for fetching HA users
- User mapping page now displays all HA users proactively
- Enhanced logging for API endpoint debugging
- Configuration flags: `homeassistant_api`, `hassio_api`, `hassio_role: admin`

### Changed
- User mapping UI shows HA users before they access the addon
- Improved error messages when SUPERVISOR_TOKEN unavailable

### Fixed
- Added missing API permissions to config.yaml
- Fixed issue where HA users weren't visible in mapping UI

## [0.1.0] - 2025-11-29

### Initial Release
- Full chore management system with Flask backend
- Home Assistant ingress authentication
- User roles: parent, kid, unmapped
- Auto-creation of users from HA ingress
- Points and rewards system
- 295+ test coverage
