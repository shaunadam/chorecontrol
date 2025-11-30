# User Management in ChoreControl

ChoreControl integrates with Home Assistant users to provide seamless authentication and role-based access control.

## Overview

ChoreControl supports two types of user accounts:

1. **Home Assistant Users** - Automatically discovered when accessing the addon
2. **Local Accounts** - Fallback authentication (e.g., admin:admin)

## How It Works

### Auto-Discovery

When a Home Assistant user accesses the ChoreControl addon via ingress:

1. **Auto-Create**: A ChoreControl user entry is automatically created
2. **Role Assignment**: New users get role='unmapped' (pending parent assignment)
3. **Display Name**: User's HA display name is fetched and stored

### User Roles

ChoreControl has three user roles:

| Role | Addon Access | HA Dashboard | Description |
|------|--------------|--------------|-------------|
| **parent** | Full access | Yes | Can manage chores, rewards, users, and approve actions |
| **kid** | Locked out | Yes | Earns points, claims chores via HA integration |
| **unmapped** | Locked out | No | Temporary state - needs parent to assign role |

### Access Control

- **Parents**: Full access to addon UI for administration
- **Kids**: Locked out of addon, interact via HA dashboards and claim buttons
- **Unmapped**: See "needs mapping" message, must wait for parent assignment

## First-Time Setup

### 1. Install Add-on and Integration

Follow the [Installation Guide](installation.md) to install both components.

### 2. Initial Login

Access ChoreControl via the HA sidebar:

```
Username: admin
Password: admin
```

**Important:** This is a local account fallback. Change the password immediately.

### 3. Map HA Users

When family members access the addon:

1. They're auto-created with role='unmapped'
2. They see a message: "Your account needs to be mapped by a parent"
3. Parent logs in and navigates to **Users → Mapping**
4. Parent assigns each user a role (parent or kid)

## User Mapping Interface

### Accessing the Mapping Page

1. Login as a parent (or admin)
2. Navigate to **Users → Mapping**
3. View all users with their HA IDs, display names, and current roles

### Assigning Roles

**Unmapped Users** (top section):
- Shows users needing attention
- Use dropdown to select Parent or Kid
- Click **Save Changes** to apply

**All Users** (bottom section):
- View all ChoreControl users
- Change roles as needed
- Local accounts (like admin) cannot be changed via mapping

### Example Workflow

1. Dad accesses addon → Auto-created with role='unmapped'
2. Mom accesses addon → Auto-created with role='unmapped'
3. Kid1 accesses addon → Auto-created with role='unmapped'
4. Admin logs in, goes to User Mapping:
   - Sets Dad → parent
   - Sets Mom → parent
   - Sets Kid1 → kid
5. Saves changes
6. Next login:
   - Dad sees full parent interface
   - Mom sees full parent interface
   - Kid1 sees lockout message (uses HA dashboard instead)

## Local Admin Account

### Default Account

ChoreControl creates a local admin account on first run:

```
Username: admin
Password: admin
```

**This account:**
- Has role='parent' (full access)
- Uses ha_user_id='local-admin'
- Can login even without HA authentication
- **Should have password changed immediately**

### Changing Admin Password

1. Login as admin
2. Navigate to **Users → Edit Profile** (future feature)
3. Or use the Users list to update the password

**For now**, the admin password can be changed via the database or by creating a new parent user and deleting admin.

## Creating Kid Users Manually

If you want to create a kid user without having them access the addon:

1. Login as parent
2. Navigate to **Users → Create User**
3. Fill in:
   - **Username**: Kid's display name
   - **HA User ID**: Leave blank or enter their HA user ID manually
   - **Role**: kid
   - **Password**: Leave blank (HA authentication only)
4. Click **Create**

The kid can now claim chores via the HA integration without ever accessing the addon UI.

## Notifications and HA User Mapping

To send targeted notifications to specific users:

1. **Option A - Automations (Recommended)**:
   - Create HA automations listening to ChoreControl events
   - Target specific notify services based on event data
   - See [notification-automations.yaml](examples/notification-automations.yaml)

2. **Option B - Manual Mapping** (Future Enhancement):
   - Map ChoreControl users to HA notify services
   - Built-in notification preferences in addon
   - Coming in Phase 2+

## Security Considerations

### HA Ingress Authentication

- ChoreControl trusts the `X-Ingress-User` header from HA
- HA handles authentication before proxying to addon
- No password needed for HA users

### Local Account Security

- Local accounts (admin) bypass HA authentication
- Use strong passwords for local accounts
- Consider disabling admin account after mapping HA users

### Role-Based Access

- Kids cannot access addon UI (parent-only)
- API routes remain accessible (needed for HA integration)
- Kids can still claim chores via HA services

## Troubleshooting

### User Not Auto-Created

**Problem**: HA user accesses addon but account not created

**Solutions**:
- Check addon logs for errors
- Verify HA user ID is not prefixed with 'local-'
- Manually create user via Users page

### User Shows as Unmapped

**Problem**: User can't access anything after auto-creation

**Expected**: This is normal for new users

**Solution**:
- Login as parent
- Navigate to User Mapping
- Assign appropriate role (parent/kid)

### Kid Can't Claim Chores

**Problem**: Kid assigned kid role but can't interact with chores

**Cause**: Kid is trying to use addon UI instead of HA integration

**Solution**:
- Install and configure the HA integration
- Set up kid dashboard with claim buttons
- Kid uses HA dashboard, not addon UI

### Local Admin Locked Out

**Problem**: Can't login with admin:admin

**Unlikely**: Local accounts always work

**Check**:
- Ensure password wasn't changed
- Verify `ha_user_id='local-admin'` exists in database
- Check addon logs for authentication errors

## Best Practices

1. **Change Default Password**: First thing after installation
2. **Map Users Early**: Assign roles as soon as users access addon
3. **Use HA Authentication**: Prefer HA users over local accounts
4. **Limit Parent Roles**: Only assign parent to users who need admin access
5. **Test with One Kid**: Set up one kid's dashboard before adding others
6. **Document Notify Services**: Keep track of which HA users map to which notify services

## Future Enhancements

Planned improvements for user management:

- [ ] Password change UI for local accounts
- [ ] Bulk user import from HA
- [ ] User profile customization
- [ ] Built-in notification service mapping
- [ ] User activity logs
- [ ] Two-factor authentication for parents

---

See also:
- [Installation Guide](installation.md)
- [Integration Setup](integration-setup.md)
- [API Reference](api-reference.md)
