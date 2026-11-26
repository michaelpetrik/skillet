---
name: stack-grill
description: Grill an AI-proposed tech stack (or a project idea) before the vibecoder builds on it. Rolls the six faces of the "loaded die" - cost at 10x traffic, exit and lock-in, data location and GDPR, who runs it at 3 a.m., who pays and where (CZ cards, QR/bank transfer, VAT, MoR vs gateway), and what the team already knows. Forces at least two alternatives per layer (hosting, DB/BaaS, auth, payments, language/framework) and ends with a decision table plus open risks. Use when the user says "grill my stack", "is Vercel/Supabase/Stripe right for me", "rozgriluj stack", "jaký stack", "AI mi navrhla Next.js + Vercel + Supabase + Stripe", or pastes a stack proposal from an AI.
category: General
version: 1.0.0
---

# Stack Grill

The AI did not choose your stack. It rolled a loaded die: the most frequent answer in its training data, the vendor whose docs, plugins and MCP sit in its context, and the "startup default" it hands to anyone who sounds like a beginner. This skill re-rolls that die with you, face by face.

The default may still win. "Vercel + Supabase + Stripe" is a legitimate answer for many projects. It just has to win **with reasons**, not by default.

## Language

Answer in the user's language. Czech in, Czech out; English in, English out. Keep vendor and product names as-is.

## Input

Accept any of:

- a project description ("chci appku na rezervace pro kadeřnictví v Ostravě"),
- an existing AI proposal ("Next.js + Vercel + Supabase + Clerk + Stripe"),
- a repo or files. If the stack is visible in the environment (`package.json`, config files, lockfiles, `vercel.json`, `supabase/`, env var names), detect it yourself. Never ask the user for facts you can look up.

If there is no proposal yet, write down the stack a typical coding agent would propose for this project and label it **"default roll"**. That is the starting point you grill.

## Known AI biases to call out

Name these whenever they apply, briefly, without lecturing:

1. **Most common is not best.** Recommendation frequency tracks training-data frequency and vendor-supplied agent tooling (plugins, MCP servers, `llms.txt`, docs bundled for agents). Popularity is a signal, not a proof.
2. **The vibecoder gets the startup default.** Agents give beginners and "vibe coders" BaaS and serverless far more often than they give seniors or enterprise teams. Ask what a senior engineer on this exact project would pick.
3. **Builders pick for you.** v0, Lovable, Bolt and similar tools ship a fixed stack and deploy target. "The tool did it" is not a decision.
4. **US-shaped defaults.** Agents rarely know the user invoices from the Czech Republic or the EU: local payment methods, CZK, VAT registration, EU data residency.
5. **Stale knowledge.** Pricing, free tiers, terms of service and APIs change after the model's training cutoff (pricing models get reworked, defaults flip, products get acquired or shut down). Every price and limit in this session is a **heuristic estimate**. Tell the user to verify the current pricing page, ToS and docs online before committing, and do so yourself if you have web access.
6. **Hallucinated packages and outdated APIs.** Before installing anything an agent suggested, check that the package exists and that the API matches the current docs.

## The design tree

Map the decision as a design tree: six faces (questions) cut across five layers.

**Layers:** hosting/runtime, database/BaaS, auth, payments, language/framework. Add a layer only if the project needs it (email, file storage, AI/LLM API, search).

**Faces of the die:**

1. **Cost at 10x** - What does this cost at ten times today's expected traffic, users and data, on a paid commercial plan? Free tiers do not count: hobby tiers are often non-commercial, free projects pause, and usage-based billing (function duration, bandwidth, image optimization, seats, MAU, per-project fees) is where viral spikes and DDoS turn into invoices. Ask about spend caps and alerts.
2. **Exit** - How do I get out? What is proprietary (APIs, edge runtime, auth user store, RLS policies, webhooks, customer payment tokens)? What does a migration cost, can data be exported in a standard format, and what happens if the vendor is acquired, changes pricing or shuts down?
3. **Data** - Where does the data live and who is the contracting party? EU region chosen explicitly (often unchangeable after creation), DPA available, subprocessors, backups, personal data in logs. Who is liable when the database is exposed (for example missing row-level security on a BaaS with a public anon key)?
4. **3 a.m.** - Who runs this when it breaks at 3 a.m.? Managed platform vs VPS you patch yourself, backups and restore actually tested, monitoring, support tier, bus factor of one.
5. **Who pays and where** - Who are the customers and how do they pay? Czech cards, QR payment or bank transfer in CZK, invoices with IČO/DIČ, VAT. Is the user a VAT payer, an OSVČ non-payer, or a company? Payment gateway (user is the seller, handles VAT) vs Merchant of Record (MoR sells on the user's behalf, handles VAT, takes a bigger cut, may restrict product types). Payout delays and reserves. Foreign service invoices can trigger VAT obligations (for example "identified person" status in CZ) - flag it as "may", recommend checking with an accountant.
6. **What I know** - What do you or the team already know and can debug without the AI? An unfamiliar stack the AI writes fluently is still a stack nobody on the team can fix. A boring stack you know (PHP, WordPress, Django, Rails, a VPS) can beat a trendy one.

Not every face applies equally to every layer. Skip combinations that clearly do not matter and say so in one line.

## Alternatives rule

For **every layer**, put the default choice next to **at least two real alternatives**. Pick alternatives that fit this project, not a fixed list. Typical candidates (verify they are still current):

- **Hosting:** Vercel, Netlify, Cloudflare Pages/Workers, Render, Railway, Fly.io, a VPS (Hetzner and similar) with Coolify or Docker, classic shared PHP hosting (VEDOS, Forpsi and similar Czech hosts).
- **DB/BaaS:** Supabase, Neon, plain managed Postgres, SQLite/Turso, PocketBase, Convex, Firebase, the app's own server with an ORM.
- **Auth:** BaaS built-in auth, Clerk, Better Auth or Auth.js in your own app, framework-native auth (Laravel, Django, Rails), Keycloak.
- **Payments:** Stripe, Czech gateways (Comgate, GoPay, ThePay), MoR (Paddle, Stripe Managed Payments, similar), plain bank transfer + QR + invoicing tool for low volume.
- **Language/framework:** Next.js, Astro, SvelteKit, Remix/React Router, Laravel/PHP, Django, Rails, a static site, WordPress.

For each option give:

- **When yes** - one line, concrete.
- **When no** - one line, concrete.
- **Cost if it succeeds** - an order-of-magnitude estimate at 10x, marked as an estimate (for example "~tens of USD/month", "~1 % + fixed fee per payment"). Never present it as a hard number.

Do not trash the default. If the default is the best fit, say so and say why.

## Rounds

Work the tree in rounds. The **frontier** is every question you can ask now without guessing answers you have not heard yet. Ask the whole frontier in one round, number the questions, give your recommended answer for each, then **stop and wait** for the user's answers.

Round 1 is always context: what the project does, expected users and traffic, who the customers are and where, how money comes in, the user's legal/tax setup (CZ/EU/other, VAT payer or not), team skills, budget and deadline. Skip anything already answered or visible in the environment.

Later rounds walk the faces, one or two faces per round, across the relevant layers. A question that depends on an answer still open belongs to a later round.

Format a round like this:

```
🎲 **Q1** - **<face>: <question title>**: <question, with options and the alternatives table when relevant>

➡️ <your recommended answer and the one-line reason>

---

🎲 **Q2** - ...
```

Answers reshape the tree: a settled decision can make a whole branch irrelevant (no payments, no payment face) or open a new one (EU health data, stricter residency). Recompute the frontier and ask the next round.

Finding facts is your job. If you can check the repo, a pricing page or the docs, do it instead of asking. Decisions are the user's: put each one to them and wait.

## Finish

The session ends when every face has been rolled for every relevant layer and nothing is silently assumed. Before finishing, confirm with the user that you reached a shared understanding. Then output:

### Decision table

| Layer | Choice | Why | Alternative (runner-up) | Cost at 10x (estimate) | Exit plan |
|---|---|---|---|---|---|
| Hosting | ... | ... | ... | ... | ... |
| DB/BaaS | ... | ... | ... | ... | ... |
| Auth | ... | ... | ... | ... | ... |
| Payments | ... | ... | ... | ... | ... |
| Language/framework | ... | ... | ... | ... | ... |

### Open risks

A numbered list of what is still uncertain or accepted on purpose: unverified prices, VAT questions for an accountant, missing spend caps, untested backups, RLS or access rules to audit, skills the team still has to learn. Each with one concrete next step.

### Verify before you build

A short checklist of the pricing pages, terms of service and docs the user should check online today, because the numbers above are estimates and may be out of date.
