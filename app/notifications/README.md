# ArmLenQuant Notification System

## Overview

The notification system provides real-time alerts and communication through multiple channels:

- **Telegram Bot**: Interactive bot for receiving notifications and sending commands
- **Dashboard**: Real-time event stream for the web UI

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token provided

### 2. Get Your Chat ID

1. Start a chat with your new bot
2. Send any message to it
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your chat ID in the response: `"chat":{"id": YOUR_CHAT_ID}`

### 3. Configure Environment Variables

Add these to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_ENABLED=true
NOTIFICATIONS_ENABLED=true
```

### 4. Notification Settings

Control what notifications you receive:

```bash
NOTIFY_ON_TASK_COMPLETE=true
NOTIFY_ON_TASK_FAILED=true
NOTIFY_ON_AGENT_ALERT=true
NOTIFY_ON_SYSTEM_ERROR=true
```

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and setup |
| `/help` | Show all available commands |
| `/status` | System health status |
| `/agents` | List registered agents |
| `/tasks` | Recent task list |
| `/crypto` | Crypto market update |
| `/jobs` | Job search status |
| `/brief` | Generate daily brief |

## Natural Language Commands

You can also send natural language commands directly to the bot:

- "Find Python jobs in Berlin"
- "What's the crypto market looking like?"
- "Analyze SOL and ETH"
- "Create a new FastAPI project"

The bot will route your request to the appropriate agent.

## API Endpoints

### Send Notification
```
POST /api/v1/notifications/send
{
  "title": "Custom Alert",
  "message": "Your message here",
  "type": "custom",
  "priority": "normal",
  "channel": "all"
}
```

### Get Recent Notifications
```
GET /api/v1/notifications/recent?limit=50
```

### Check Telegram Status
```
GET /api/v1/notifications/telegram/status
```

### Test Telegram
```
POST /api/v1/notifications/telegram/test
```

## Notification Types

| Type | Description |
|------|-------------|
| `task_completed` | Task finished successfully |
| `task_failed` | Task failed after retries |
| `agent_alert` | Agent warning/error |
| `system_error` | System-level error |
| `daily_brief` | Morning brief ready |
| `crypto_signal` | Trading signal generated |
| `job_match` | New job matching profile |
| `custom` | Custom notification |

## Priority Levels

| Priority | Description | Sound |
|----------|-------------|-------|
| `low` | Informational | Silent |
| `normal` | Standard updates | Normal |
| `high` | Important alerts | Normal |
| `urgent` | Critical alerts | Always |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SYSTEM                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐        ┌─────────────────┐           │
│   │ NotificationSvc │───────►│  Telegram Bot   │           │
│   │                 │        └────────┬────────┘           │
│   │  - send()       │                 │                     │
│   │  - notify_*()   │        ┌────────▼────────┐           │
│   │                 │        │   Your Phone    │           │
│   └────────┬────────┘        └─────────────────┘           │
│            │                                                │
│            │                 ┌─────────────────┐           │
│            └────────────────►│  Event Stream   │           │
│                              │   (Dashboard)   │           │
│                              └─────────────────┘           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Integration Points

Notifications are automatically triggered from:

1. **Task Queue**: When tasks complete or fail
2. **Crypto Sentinel**: When trading signals are generated
3. **Job Hunter**: When jobs matching your profile are found
4. **System Monitoring**: On errors or health alerts

## Testing

Run the notification tests:

```bash
cd armlenquant-cloud/api
pytest tests/test_notifications.py -v
```

## Troubleshooting

### Bot not responding?
- Check `TELEGRAM_ENABLED=true`
- Verify bot token is correct
- Ensure you've started a chat with the bot first

### Not receiving notifications?
- Verify `TELEGRAM_CHAT_ID` is correct
- Check `NOTIFICATIONS_ENABLED=true`
- Look at API logs for errors

### Commands not working?
- The bot must be running (check startup logs)
- Database must be connected
- Try `/start` to reinitialize


