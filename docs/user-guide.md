# ChoreControl User Guide

Welcome to ChoreControl! This guide will help you get the most out of your chore management system.

## Table of Contents

1. [Overview](#overview)
2. [For Parents](#for-parents)
3. [For Kids](#for-kids)
4. [Dashboard Setup](#dashboard-setup)
5. [Common Workflows](#common-workflows)
6. [Tips and Best Practices](#tips-and-best-practices)

## Overview

ChoreControl helps families manage chores, track completion, and reward kids for their work.

**Key Concepts**:

- **Chores**: Tasks that need to be completed (one-time or recurring)
- **Points**: Earned by completing chores, used to claim rewards
- **Rewards**: Things kids can "buy" with their points
- **Approval Workflow**: Kids claim chores, parents approve them

## For Parents

### Managing Kids

> **TODO**: Complete when user management is implemented

1. Go to **ChoreControl** → **Kids**
2. Add each child by mapping to their Home Assistant user
3. Set initial points if desired

### Creating Chores

> **TODO**: Complete when chore creation is implemented

#### One-Time Chores

1. Go to **ChoreControl** → **Chores** → **New Chore**
2. Fill in the form:
   - **Name**: Short, descriptive name
   - **Description**: Details about what needs to be done
   - **Points**: How many points this chore is worth
   - **Recurrence**: Select "None" for one-time
   - **Assign to**: Select which kid(s) should do this
   - **Requires approval**: Yes (recommended)
3. Click **Save**

#### Recurring Chores

1. Follow the same steps as one-time chores
2. For **Recurrence**, select:
   - **Daily**: Every day or every N days
   - **Weekly**: Specific days of the week
   - **Monthly**: Specific days of the month
3. Set the start date (when the chore becomes active)

**Example: Weekly Trash Day**

- Name: "Take out trash"
- Description: "Roll both bins to the curb"
- Points: 5
- Recurrence: Weekly on Mondays
- Assign to: Kid1
- Requires approval: Yes

### Creating Rewards

> **TODO**: Complete when reward creation is implemented

1. Go to **ChoreControl** → **Rewards** → **New Reward**
2. Fill in the form:
   - **Name**: What the reward is
   - **Description**: Details about the reward
   - **Points cost**: How many points it costs
   - **Cooldown** (optional): Days before it can be claimed again
   - **Max claims** (optional): Limit total or per-kid claims
3. Click **Save**

**Example Rewards**:

- "Ice cream trip" (20 points, 7-day cooldown)
- "Extra 30 minutes screen time" (10 points)
- "Choose dinner" (15 points)
- "Movie night" (25 points, 2 week cooldown)

### Approving Chores

> **TODO**: Complete when approval workflow is implemented

**From Parent Dashboard**:

1. Open your Home Assistant dashboard
2. Check the "Pending Approvals" section
3. Review each claimed chore
4. Click **Approve** or **Reject**
5. If rejecting, provide a reason

**From Mobile Notifications**:

1. Receive notification: "Kid1 claimed 'Take out trash'"
2. Tap notification to open approval screen
3. Approve or reject

### Managing Points

> **TODO**: Complete when points management is implemented

**Manual Adjustments**:

1. Go to **ChoreControl** → **Points**
2. Select the kid
3. Enter points to add (positive) or deduct (negative)
4. Provide a reason (e.g., "Bonus for being helpful", "Broke house rule")
5. Click **Save**

**Viewing History**:

1. Go to **ChoreControl** → **Points History**
2. Select the kid
3. See all point transactions with timestamps and reasons

## For Kids

### Viewing Your Chores

> **TODO**: Complete when kid dashboard is implemented

1. Open your Home Assistant dashboard
2. See the "My Chores Today" section
3. See upcoming chores for the week

### Claiming a Chore

> **TODO**: Complete when claim workflow is implemented

1. Complete the chore in real life
2. Go to your dashboard
3. Find the chore in "My Chores Today"
4. Click the **Claim** button
5. Wait for parent approval
6. Receive notification when approved
7. Points are added to your balance

### Claiming Rewards

> **TODO**: Complete when reward claiming is implemented

1. Go to the "Available Rewards" section
2. See your current points balance
3. Find a reward you can afford
4. Click **Claim Reward**
5. Your points are deducted
6. Parent receives notification

### Viewing Your Progress

> **TODO**: Complete when dashboards are implemented

- **Current Points**: See your total points
- **Completed This Week**: Track your progress
- **Recent Activity**: See recent chores and rewards
- **Upcoming Chores**: Plan ahead

## Dashboard Setup

### Kid Dashboard

> **TODO**: Complete when dashboard examples are ready

Example dashboard YAML:

```yaml
# TODO: Add kid dashboard YAML example
```

### Parent Dashboard

> **TODO**: Complete when dashboard examples are ready

Example dashboard YAML:

```yaml
# TODO: Add parent dashboard YAML example
```

### Shared Family Dashboard

> **TODO**: Complete when dashboard examples are ready

Example dashboard showing all kids:

```yaml
# TODO: Add family dashboard YAML example
```

## Common Workflows

### Setting Up a New Chore Schedule

> **TODO**: Complete with step-by-step examples

**Scenario**: You want to set up daily and weekly chores for your two kids.

1. List out all chores needed
2. Decide which are daily vs. weekly
3. Assign point values based on effort
4. Create each chore in the system
5. Review the calendar to verify schedule

### Handling Vacations

> **TODO**: Complete when chore management is implemented

**Option 1: Disable Chores Temporarily**

1. Edit each recurring chore
2. Set an end date before vacation
3. After vacation, create a new version with start date

**Option 2: Pause Assignments**

1. Go to each kid's profile
2. Mark as "On Vacation"
3. System won't generate new chore instances

### Adjusting Points for Fairness

> **TODO**: Complete when points management is implemented

If chore difficulty changes or kids need balancing:

1. Review points history for each kid
2. Make manual adjustments if needed
3. Update chore point values for future instances
4. Communicate changes with kids

## Tips and Best Practices

### Setting Point Values

- **Start simple**: 1-10 points for most chores
- **Consider time**: More points for longer chores
- **Consider difficulty**: Harder chores worth more
- **Be consistent**: Similar chores should have similar values

**Example Point Scale**:

- Make bed: 2 points (5 min, easy)
- Dishes: 5 points (15 min, medium)
- Vacuum room: 5 points (20 min, medium)
- Clean bathroom: 10 points (30 min, harder)

### Choosing Rewards

- **Mix of small and large**: Some quick wins, some to save for
- **Include non-material rewards**: Extra time, special activities
- **Let kids suggest**: They know what motivates them
- **Adjust cooldowns**: Prevent overuse of favorite rewards

**Example Reward Tiers**:

- **Small (10-15 points)**: Extra screen time, stay up late, choose dessert
- **Medium (20-30 points)**: Friend sleepover, movie night, restaurant choice
- **Large (50+ points)**: Special outing, new toy, big experience

### Making It Work

1. **Start small**: Begin with just a few chores
2. **Be consistent**: Approve/reject chores promptly
3. **Communicate**: Explain point values and expectations
4. **Adjust as needed**: Fine-tune based on what works
5. **Celebrate success**: Acknowledge milestones and streaks

### Avoiding Common Issues

- **Don't make rewards too expensive**: Kids should be able to earn them
- **Don't forget to approve**: Set reminders to check pending chores
- **Don't be too strict**: Allow some flexibility in chore completion
- **Do explain rejections**: Help kids understand what was wrong

## Advanced Features

### Calendar Integration

> **TODO**: Complete when calendar integration is implemented

1. Set up ICS feed in Home Assistant
2. Subscribe to calendar on phones/tablets
3. See chore schedule alongside other events

### Automations

> **TODO**: Complete when HA services are implemented

**Example: Remind kids of chores**

```yaml
# TODO: Add automation example
```

**Example: Celebrate milestones**

```yaml
# TODO: Add automation example
```

### Notifications

> **TODO**: Complete when notifications are implemented

Configure notification preferences:

- When kid claims chore
- When parent approves/rejects
- When reward is claimed
- Daily summary of pending chores

## Troubleshooting

### Kid can't claim chore

> **TODO**: Add troubleshooting steps

- Verify chore is assigned to them
- Check that chore is due today
- Ensure chore isn't already claimed

### Points aren't updating

> **TODO**: Add troubleshooting steps

- Verify chore was approved (not just claimed)
- Check points history for transaction
- Refresh dashboard

### Chore isn't appearing

> **TODO**: Add troubleshooting steps

- Check chore's start date
- Verify chore is active
- Check assignment settings

## Getting Help

- **Documentation**: [Full docs](https://github.com/shaunadam/chorecontrol/docs)
- **Issues**: [Report bugs](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [Ask questions](https://github.com/shaunadam/chorecontrol/discussions)

## What's Next?

- **Explore the API**: See [API Reference](api-reference.md)
- **Contribute**: Check out [Development Guide](development.md)
- **Request Features**: Open an issue with your ideas!
