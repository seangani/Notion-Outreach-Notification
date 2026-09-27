# Notion Reach-Out Bot

Checks the "Linkdin Outreach" Notion database on a schedule and sends a free
push notification (via ntfy.sh) for anyone whose "When to followup?" column
says REACH OUT.

## One-time setup

1. **Create a Notion integration**
   - Go to https://www.notion.so/my-integrations → "New integration"
   - Give it a name (e.g. "Reach Out Bot"), select your workspace, save
   - Copy the "Internal Integration Token" — this is `NOTION_TOKEN`

2. **Share your database with the integration**
   - Open the "Linkdin Outreach" table in Notion
   - Click the `...` menu (top right) → "Connections" → add your integration

3. **Get the database ID**
   - Open the database as a full page, copy its URL
   - The URL looks like `notion.so/<workspace>/<DATABASE_ID>?v=...`
   - The `DATABASE_ID` is the 32-character string right before `?v=`

4. **Pick an ntfy topic and subscribe on your phone**
   - Install the ntfy app (iOS/Android) or use https://ntfy.sh in a browser
   - Make up a private, hard-to-guess topic name, e.g. `sean-outreach-x7k2`
   - Subscribe to that topic in the app — that's your `NTFY_TOPIC`

5. **Push this folder to a GitHub repo**
   ```
   cd notion-reachout-bot
   git init
   git add .
   git commit -m "Add Notion reach-out bot"
   gh repo create notion-reachout-bot --private --source=. --push
   ```

6. **Add your secrets to the GitHub repo**
   - On GitHub: repo → Settings → Secrets and variables → Actions → New repository secret
   - Add three secrets: `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `NTFY_TOPIC`

7. **Test it**
   - Go to the repo's "Actions" tab → "Notion reach-out check" → "Run workflow"
   - Check your phone for a push notification (or the Actions log for
     "Nobody due for reach-out right now.")

After that, it runs automatically once a day, weekdays at 12:07 UTC — see
the cron schedule in `.github/workflows/reach-out-check.yml` if you want
to change the timing.

## Call reminders

A second, independent check: pings you ~1 hour before a scheduled call, and
lets you log the outcome (Call finished / Resource for Fulltime / Sent
Resume) straight from the notification.

### Setup

1. **Add two properties to the Notion database**
   - `Call Time` — a Date property, with "include time" turned on
   - `Call reminder set` — a Checkbox property (bookkeeping only, so you
     don't get pinged twice for the same call)

2. **Update the "When to followup?" formula** to flip to `CALL REMINDER`
   when `Stat` is `"Call"` and `Call Time` is within the next hour.

3. **Use it**: set someone's `Stat` to `Call` and fill in `Call Time`
   whenever you schedule a call (e.g. by asking Claude, if it's connected
   to this Notion workspace, to do it for you). Nothing else to configure —
   this check reuses the same `NOTION_TOKEN`, `NTFY_TOPIC`, and
   `DISPATCH_TOKEN` secrets as the reach-out check above.

Runs automatically every hour (all day, every day — calls aren't limited to
weekday business hours) at :07 past the hour, via
`.github/workflows/call-reminder-check.yml`.
