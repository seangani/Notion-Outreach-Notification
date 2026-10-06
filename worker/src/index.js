// Cloudflare is only the on-time scheduler here. At the right moment it tells
// GitHub to run the existing Python checks (repository_dispatch), which do the
// Notion query and ntfy push. Sending ntfy from a Worker hits ntfy's per-IP
// quota on Cloudflare's shared IPs, so that part stays on GitHub.
const GITHUB_REPO = "seangani/Notion-Outreach-Notification";

async function dispatch(env, eventType) {
  const resp = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.DISPATCH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "notion-outreach-notifier",
    },
    body: JSON.stringify({ event_type: eventType }),
  });
  if (!resp.ok) throw new Error(`GitHub ${resp.status}: ${await resp.text()}`);
  console.log(`Dispatched ${eventType}`);
}

// True on weekdays at 12:xx New York time. The cron fires at both 16:00 and
// 17:00 UTC so this works in both daylight and standard time.
function isNoonEasternWeekday() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "numeric",
    hour12: false,
    weekday: "short",
  }).formatToParts(new Date());
  const get = (type) => parts.find((p) => p.type === type).value;
  return Number(get("hour")) % 24 === 12 && !["Sat", "Sun"].includes(get("weekday"));
}

export default {
  async scheduled(event, env, ctx) {
    if (event.cron === "7 * * * *") {
      ctx.waitUntil(dispatch(env, "run-call-reminder"));
    } else if (isNoonEasternWeekday()) {
      ctx.waitUntil(dispatch(env, "run-reach-out"));
    }
  },

  // Manual test: /?run=reach or /?run=call, with ?key=<NTFY_TOPIC>.
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.searchParams.get("key") !== env.NTFY_TOPIC) return new Response("not found", { status: 404 });
    const run = url.searchParams.get("run");
    if (run === "reach") await dispatch(env, "run-reach-out");
    else if (run === "call") await dispatch(env, "run-call-reminder");
    else return new Response("use ?run=reach or ?run=call", { status: 400 });
    return new Response("dispatched");
  },
};
