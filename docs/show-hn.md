# Show HN draft

**Title (≤ 80 chars):**

```
Show HN: uctx – local, user-owned memory shared across AI agents (MCP)
```

**URL:** https://github.com/tmeng7777/uctx

**Body:**

---

Every AI assistant keeps its own siloed memory. I tell Claude I prefer Python;
ChatGPT still has no idea. Switching tools means re-explaining myself every time,
and my accumulated context is locked inside whichever vendor I happened to use.

uctx is a tiny MCP server backed by a local SQLite file *I own*
(`~/.uctx/context.db`). Any MCP-enabled agent — Claude Desktop, Cursor, etc. —
reads and writes the same context. So I tell Claude "remember I prefer Python and
tabs," and later Cursor already knows. No cloud, no account: the data is a file
on my machine, and it moves *between* vendors instead of being trapped inside one.

It's four tools: `save_context`, `search_context`, `list_context`,
`forget_context`. ~150 lines of Python. There's an end-to-end test where an MCP
client launches the server and round-trips a save + search.

What it deliberately does NOT do yet (v0): embeddings, provenance/signing,
temporal validity, access control, multi-user. Those are the genuinely hard
parts, and I only want to build them if people actually use the simple version.

I'm honestly unsure whether "portable, user-owned memory" is a real need or a
thing people applaud and never use — projects like Solid got the principle right
and adoption wrong. So I'm shipping the smallest thing that could tell me. If
you'd use this (or wouldn't), I'd genuinely like to know why.

Repo + 30-second demo: https://github.com/tmeng7777/uctx

---

**Notes for posting**
- Post Tue–Thu, ~9–11am ET tends to get more eyeballs.
- Reply to every comment for the first few hours — engagement helps ranking.
- Lead with the honest "is this a real need?" framing; HN rewards candor over hype.
