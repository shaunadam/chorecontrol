# Dashboard Setup Guide

This guide helps you set up Home Assistant dashboards for ChoreControl.

## Required Custom Cards

For the best dashboard experience, install these custom cards from HACS.

### Essential

**auto-entities** - Automatically shows entities matching patterns
- Required for dynamic button display
- Shows all available chore claim buttons for each kid
- [GitHub](https://github.com/thomasloven/lovelace-auto-entities)

### Recommended

**mushroom** - Modern, clean card designs
- Mobile-friendly interface
- Beautiful entity cards and chips
- [GitHub](https://github.com/piitaya/lovelace-mushroom)

**decluttering-card** - Reusable card templates
- Great for multi-kid setups
- Define once, use many times
- [GitHub](https://github.com/custom-cards/decluttering-card)

**card-mod** - CSS styling for cards
- Customize card appearance
- Add custom colors and styles
- [GitHub](https://github.com/thomasloven/lovelace-card-mod)

## Installation

### Install HACS (if not already installed)

1. Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant
3. Complete HACS setup in the UI

### Install Custom Cards

1. Go to **HACS** in the sidebar
2. Click **Frontend**
3. Click **+ Explore & Download Repositories**
4. Search for each card and install:
   - auto-entities
   - mushroom
   - decluttering-card (optional)
   - card-mod (optional)
5. Restart Home Assistant
6. Clear your browser cache (Ctrl+F5 or Cmd+Shift+R)

## Finding Your User IDs

To use the example dashboards, you need to know each kid's user_id.

### Option 1: Developer Tools

1. Go to **Developer Tools** in the sidebar
2. Click **States** tab
3. Search for `sensor.chorecontrol_`
4. Click on any kid's sensor (e.g., `sensor.chorecontrol_emma_points`)
5. Look at the **Attributes** section for `user_id`

### Option 2: Entity Attributes

1. Go to **Settings** > **Devices & Services**
2. Find **ChoreControl** integration
3. Click on it to see all entities
4. Click on a kid's sensor
5. View the `user_id` attribute

### Option 3: Add-on API

Access the API directly:

```bash
curl http://localhost:8099/api/users
```

Or open in browser: `http://homeassistant.local:8099/api/users`

### Option 4: Add-on Web UI

1. Go to **Settings** > **Add-ons**
2. Open **ChoreControl** add-on
3. Click **Open Web UI**
4. Go to the Users page
5. User IDs are shown in the user list

## Creating Your Dashboard

### Method 1: Dashboard UI Editor

1. Go to your dashboard
2. Click the three dots menu (top right)
3. Click **Edit Dashboard**
4. Click **+ Add Card**
5. Choose card type and configure

### Method 2: YAML Configuration

1. Go to your dashboard
2. Click the three dots menu
3. Click **Edit Dashboard**
4. Click the three dots menu again
5. Click **Raw configuration editor**
6. Paste YAML from examples

### Method 3: Create New Dashboard

1. Go to **Settings** > **Dashboards**
2. Click **+ Add Dashboard**
3. Name it (e.g., "ChoreControl")
4. Toggle on **Show in sidebar**
5. Click **Create**
6. Edit the new dashboard

## Dashboard Examples

See the [examples](examples/) directory for ready-to-use dashboard configurations:

- **kid-dashboard.yaml** - Simple dashboard for each kid
- **parent-dashboard.yaml** - Overview for parents
- **dynamic-dashboard.yaml** - Uses decluttering templates
- **mushroom-dashboard.yaml** - Modern UI with mushroom cards

### Using the Examples

1. Copy the YAML content from an example file
2. Open your dashboard in raw configuration editor
3. Replace or add views from the example
4. Update usernames and user_ids to match your family
5. Save and refresh

## Customization Tips

### Replace User Information

In all examples, replace these placeholders:

| Placeholder | Replace With |
|-------------|--------------|
| `emma` | Your kid's username (lowercase) |
| `3` (user_id) | Your kid's actual user ID |
| `jack` | Second kid's username |
| `4` (user_id) | Second kid's user ID |

### Add More Kids

For each additional kid, copy the card section and update:
- Username in entity IDs
- user_id in attributes filter
- Display name in titles

### Customize Colors

With card-mod, you can customize colors:

```yaml
type: entity
entity: sensor.chorecontrol_emma_points
card_mod:
  style: |
    ha-card {
      background-color: #f0f9ff;
    }
```

### Add Conditional Cards

Show content only when conditions are met:

```yaml
type: conditional
conditions:
  - entity: sensor.chorecontrol_pending_approvals
    state_not: "0"
card:
  type: markdown
  content: "Chores need approval!"
```

## Troubleshooting

### Cards Not Showing

1. Make sure HACS custom cards are installed
2. Clear browser cache
3. Check browser console for errors (F12)

### Buttons Not Appearing

1. Verify user_id is correct in the filter
2. Check that there are claimable chores in ChoreControl
3. Make sure auto-entities card is installed

### Entity Not Found

1. Verify the entity exists in Developer Tools > States
2. Check spelling of username in entity ID
3. Ensure ChoreControl integration is loaded

### Template Errors

1. Check Jinja2 template syntax
2. Use Developer Tools > Template to test templates
3. Ensure entity exists before referencing it

## Mobile App Dashboards

The dashboards work great in the Home Assistant mobile app. For the best mobile experience:

1. Use the mushroom dashboard example
2. Set `columns: 2` for grid layouts
3. Use `layout: vertical` for mushroom cards
4. Keep cards compact

### Create a Mobile-Only View

```yaml
views:
  - title: Mobile
    path: mobile
    panel: false
    cards:
      # Mobile-optimized cards here
```

## Next Steps

1. Start with a simple kid-dashboard.yaml
2. Test that entities show correctly
3. Add more customization as needed
4. Create separate dashboards for kids and parents
5. Set up notifications for chore events

For more information on entities and services, see the [Entity Reference](entity-reference.md).
