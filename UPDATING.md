# Updating ChoreControl

This document explains how to update the ChoreControl addon in your Home Assistant instance.

## For Users: Updating the Addon

### Method 1: Through Home Assistant UI (Recommended)

1. Go to **Settings → Add-ons → ChoreControl**
2. Click the **Update** button (appears when new version available)
3. Wait for the update to complete
4. Check the logs to verify the new version

### Method 2: Force Refresh Repository

If updates aren't showing:

1. Go to **Settings → Add-ons → Add-on Store** (3 dots menu)
2. Click **Repositories**
3. Find `https://github.com/shaunadam/chorecontrol`
4. Click **Reload** or remove and re-add the repository
5. Return to ChoreControl addon
6. The update button should now appear

### Method 3: Uninstall and Reinstall

⚠️ **Warning**: This will reset your configuration options (but NOT your database)

1. Go to **Settings → Add-ons → ChoreControl**
2. Click **Uninstall**
3. Go to **Add-on Store**
4. Find ChoreControl
5. Click **Install**
6. Reconfigure your options (timezone, debug mode, etc.)
7. Start the addon

## For Developers: Releasing New Versions

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.2.0): New features, backward compatible
- **Patch** (0.1.1): Bug fixes, backward compatible

### Release Checklist

1. **Update version** in `chorecontrol/config.yaml`
2. **Update CHANGELOG.md** with changes
3. **Commit changes**:
   ```bash
   git add chorecontrol/config.yaml chorecontrol/CHANGELOG.md
   git commit -m "Release vX.Y.Z: Brief description"
   ```
4. **Tag the release**:
   ```bash
   git tag -a vX.Y.Z -m "Version X.Y.Z"
   git push origin main --tags
   ```
5. **CI/CD builds Docker images** automatically
6. **Users see update** in HA within 24 hours (or after repo refresh)

### Current Version

See [CHANGELOG.md](chorecontrol/CHANGELOG.md) for the latest version and changes.

## Troubleshooting Updates

### Update Not Showing

**Problem**: New version committed but HA doesn't show update

**Solutions**:
1. Home Assistant caches repository info - force reload (see Method 2 above)
2. Wait up to 24 hours for automatic refresh
3. Check the version in config.yaml matches what's in GitHub

### Update Fails

**Problem**: Update button shows but fails to update

**Solutions**:
1. Check addon logs for errors
2. Try uninstall/reinstall method
3. Verify CI/CD built images successfully: https://github.com/shaunadam/chorecontrol/actions

### Config Changes Not Applied

**Problem**: Updated addon but new config options not available

**Root Cause**: Home Assistant reads `config.yaml` from GitHub when refreshing repository

**Solution**:
1. Verify `config.yaml` is committed and pushed to GitHub
2. Force refresh repository (Method 2)
3. Update or reinstall addon
4. Check addon info page for new configuration options

## Version History

| Version | Release Date | Key Changes |
|---------|--------------|-------------|
| 0.2.0   | 2025-11-30  | Added Supervisor API access, HA user mapping |
| 0.1.0   | 2025-11-29  | Initial release |

See [CHANGELOG.md](chorecontrol/CHANGELOG.md) for detailed change history.
