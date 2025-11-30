# Changelog

All notable changes to the ChoreControl add-on will be documented in this file.

## [0.2.4] - 2025-11-30

### Fixed
- Enable INFO level logging in Gunicorn to see application logs
- This reveals HA API calls and user fetching diagnostics
- Previously only WARNING+ logs were visible, hiding useful debug info

## [0.2.3] - 2025-11-30

### Fixed
- Use correct Supervisor API endpoint: `/auth/list` instead of `/core/api/auth`
- Updated API base URL from `http://supervisor/core/api` to `http://supervisor`
- Fixed health check endpoint to use `/supervisor/info`
- HA user list should now be successfully retrieved

## [0.2.2] - 2025-11-30

### Fixed
- **CRITICAL**: Use `/usr/bin/with-contenv bashio` shebang in run.sh
- This fixes SUPERVISOR_TOKEN not being available at runtime
- Environment variables are now properly injected by s6-overlay
- HA API integration now works correctly to fetch user information

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
