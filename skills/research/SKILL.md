---
name: research
description: Only use when explicitly invoked as /research. Verifies facts through live source checks and produces well-cited research.
disable-model-invocation: true
---

# Research

If this skill is invoked, apply every standard below in full.

The sections below describe **how to think and work**, not a script to walk the user through. Proceed directly to research unless something is genuinely ambiguous — only then ask a follow-up question. Do not interview the user about scope, output format, or depth on every task; infer reasonable defaults from the prompt and start.

## What needs verification

Not everything requires a fetched source. Distinguish stable knowledge from information that goes stale.

**Stable knowledge — training data is sufficient.** Fundamental facts that persist over time and are unlikely to have changed: laws of physics, well-established mathematics, historical events with settled records, general scientific principles, how standard algorithms work. Explain directly; no citation required.

**Ephemeral or dynamic — verify live and cite.** Anything current, recent, or rapidly evolving: news, prices, product features, policies, personnel, statistics, legal/regulatory status, version-specific behavior, "what does X say/do now." Training data may help you find where to look, but never treat it as the source of a fact. Fetch, confirm the claim is on the page, then cite.

When uncertain which category applies, verify.

## Core principles

### Verify before citing

For every claim that requires live verification, fetch the specific page and confirm:

1. **URL resolves** — not 404, not a generic error page
2. **Not a redirect to a homepage** — you landed on the page that contains the claim
3. **Content is present** — the statistic, quote, date, or policy you cite actually appears on that page
4. **Content is current** — check dates; note if the page is outdated or superseded

Use `WebFetch` (or equivalent fetch tool). Search snippets alone are not verification.

If you cannot confirm a claim, do not present it as fact. Label it **unverified** or **could not confirm**, and say what you tried.

### Trace to the primary source

Follow citation chains to the original. News cites a study → cite the study. Blog cites government data → cite the government page.

If the primary exists online and is accessible, cite it directly. If the primary is offline, paywalled, or inaccessible, cite the best available secondary source and note: *Primary source not directly verified.*

Secondary sources misquote primaries. Training data misquotes everything. The extra hop is worth it.

### Cite next to the claim

Put the source **right beside the fact** so the user can click through immediately. Inline citations are preferred; markdown footnotes work well for dense prose.

**Format:**

```
[Organization, "Title or Description", Year](URL)
```

Examples:

- The federal minimum wage is $7.25/hour [DOL, "Minimum Wage", 2026](https://www.dol.gov/...).
- Cursor Pro costs $20/month[^1].

[^1]: [Cursor, "Pricing", 2026](https://cursor.com/pricing)

**Link rules:**

- Link to the **specific page**, not a homepage, search result, or category index
- Use anchor links (`#section`) when they pinpoint the claim
- If a URL may be unstable, note the access date

**No duplicate source lists.** Sources cited inline (or as footnotes) do not need to be repeated in a separate Sources section. Only add a Sources section for references that do not belong inline — background reading, tangential context, or sources that support the whole document rather than a specific claim.

### Flag uncertainty

Be explicit about conflicting sources, paywalled primaries, single-source claims on contentious topics, and information that may have changed since publication.

## How to work

These steps are for your own execution — not a user-facing checklist.

1. **Understand the question.** Parse what the user wants. If the prompt is clear enough, start researching immediately.
2. **Find sources.** Search the web; use training data only as a map to candidate URLs. Prefer official docs, government/regulatory sites, primary data publishers, and reputable journalism. Wikipedia is a lead generator, not a citable source. Collect multiple candidates per claim.
3. **Verify and trace.** Fetch pages, confirm content, follow chains to primaries.
4. **Write the answer.** Synthesize findings with inline citations on every verified claim. Adapt format to the task — brief answer, comparison table, report, or file.

Ask the user a question only when the request is genuinely ambiguous and you cannot make a reasonable assumption (e.g., which of two similarly-named products, which time period, which jurisdiction).

## Before delivering

- [ ] Ephemeral claims verified via fetch or marked unverified — not stated from training data alone
- [ ] Every cited URL was fetched and contains the claimed information
- [ ] Primary sources cited where accessible; secondaries noted when not
- [ ] Citations are inline (or footnoted) next to the facts they support
- [ ] No homepage or search-page links standing in for specific pages
- [ ] Conflicts and gaps flagged, not smoothed over

## Parallel research

For multi-topic or multi-entity work (several products, candidates, jurisdictions), launch parallel `generalPurpose` subagents — one per entity or topic. **Give each subagent the full skill** (provide the path to this `SKILL.md` and instruct them to read and follow it). Each prompt should also include the specific sub-question and what structured output to return.

Write results as they arrive; synthesize only after components are complete.

## Common mistakes

| Mistake | Fix |
|---|---|
| Citing ephemeral facts from memory | Fetch the page; verify the claim is there |
| Citing a secondary summary | Follow the link chain to the primary |
| Link goes to homepage | Find the deep link that contains the fact |
| Search snippet as evidence | Open the actual page |
| Citations only at the bottom | Move links inline, next to each claim |
| Interviewing the user before starting | Infer defaults; ask only when genuinely stuck |
