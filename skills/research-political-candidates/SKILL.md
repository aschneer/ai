---
name: research-political-candidates
description: Research political candidates for an election and produce individual candidate profiles plus a comparison summary with voting recommendations. Use when the user wants to research candidates, prepare for an election, analyze candidates against their values, or build a voting guide. Triggers: "research candidates", "help me vote", "who should I vote for", "candidate research", "election research", "voting guide".
disable-model-invocation: true
---

# Research Political Candidates

Produces per-candidate markdown profiles and a comparison/recommendation summary, organized by office, grounded in the voter's values.

## Setup

Before starting, confirm:
1. **Voter values file** — path to a markdown file describing the voter's values, priorities, and red flags (e.g. `voting/context.md`)
2. **Election** — date and jurisdiction (e.g. "California Primary, June 2, 2026")
3. **Output folder** — base folder for all research (e.g. `voting/260602_ca_primary/`)
4. **Candidates** — list of names per office; user provides these

## Folder Structure

```
voting/
└── [YYMMDD_election_name]/
    ├── [election]_voting_context.md   ← voter values (user-provided)
    ├── [office_1]/
    │   ├── candidate_a.md
    │   ├── candidate_b.md
    │   └── summary.md                 ← comparison + recommendation
    └── [office_2]/
        ├── ...
        └── summary.md
```

- Office folder names: `snake_case`, no spaces (e.g. `lt_governor`, `us_senate`, `state_assembly_15`)
- Candidate file names: `firstname_lastname.md`
- One `summary.md` per office

## Research Workflow

### 1. Create folder structure

Create the office subfolder(s) before researching.

### 2. Launch parallel research agents

For each candidate, launch a background `generalPurpose` subagent. This avoids serial web fetch approval dialogs.

Each agent's prompt should instruct it to:
- Find and fetch the candidate's **campaign website** (no website = major red flag — note it explicitly)
- Fetch their **Ballotpedia** profile (`ballotpedia.org/[First_Last]`)
- Check **OpenSecrets** for campaign finance and top donors
- Check **GovTrack** or the relevant state legislature website for any voting history — not just incumbents; check all candidates who have ever held office
- Search for **debate recordings, forum transcripts, and notable interviews** (YouTube, local news, League of Women Voters, etc.)
- Search for **news coverage**, controversies, and endorsements — include both mainstream and independent journalism; evaluate sources by the quality of their reasoning and evidence, not their institutional prestige
- Assess **authenticity and substance**: based on interviews, debates, and written statements, does the candidate appear to genuinely understand the issues they speak about? Do they articulate specific policy ideas, or do they rely on platitudes and vague promises? How likely are they to actually follow through?
- Return all findings as a structured summary

### 3. Write files as results arrive; summary last

Write each candidate file as its agent returns — don't wait for all to finish. Write `summary.md` only after all candidate files are complete.

## Candidate File Template

```markdown
# [Full Name] — [Office] [Year]

**Party**: [Party]
**Website**: ✅/⚠️ [URL] — [note if missing: "No website found — RED FLAG"]
**Background**: [2-line bio]
**Location**: [City, State]

---

## Background

[3–5 sentences: career, relevant experience, why they're running]

## Policy Positions

- **[Issue]**: [position]
- **[Issue]**: [position]

## Endorsements

[List or "None identified"]

## Funding

- **Total raised**: $X
- **Top donors / funding sources**: [list]
- [Note any concerning funding patterns]

## Red Flags

[Bullet list of anything concerning: legal issues, contradictions, opacity, rhetorical tactics, bad policy positions per the voter's values]

## Alignment with Voter Values

| Value | Rating | Notes |
|---|---|---|
| [Value from context file] | ✅/⚠️/🚫 | [brief note] |

## Bottom Line

[2–4 sentences: honest overall assessment]

**Recommendation**: [Vote / Consider / Do not vote] — [one sentence why]

---

*Sources: [list]*
```

## Summary File Template

```markdown
# [Office] — [Election] Summary

**Recommendation**: **[Candidate Name]**

---

## Candidate Comparison

| Candidate | Party | Website | Funding | Key Strengths | Key Concerns | Rating |
|---|---|---|---|---|---|---|
| [Name] | [Party] | ✅/🚫 | $X | [brief] | [brief] | ⭐⭐⭐ |

---

## Recommendation

**Vote for [Name]** because [2–3 sentences grounded in the voter's values].

### Runner-up

[Name] — [why they're close but not the top pick]

### Do Not Vote For

- **[Name]**: [one-line reason]
- **[Name]**: [one-line reason]

---

## Notes

[Any caveats, strategic voting considerations, or things to watch]
```

## Key Research Sources

| Source | What It's Good For |
|---|---|
| Candidate website | Stated positions, biography — **always check; missing = red flag** |
| `ballotpedia.org/[Name]` | Biography, election history, endorsements, candidate surveys |
| `opensecrets.org` | Campaign finance, top donors, industry funding (federal races) |
| `govtrack.us` | Congressional voting records (federal races) |
| State legislature website | Legislative voting records and bill history — search "[State] legislature" or "[State] general assembly" (e.g. `leginfo.legislature.ca.gov`, `legislature.texas.gov`) |
| State campaign finance authority | Contribution and expenditure records — search "[State] campaign finance" or "[State] secretary of state campaign finance" (e.g. `cal-access.sos.ca.gov`, `ethics.ga.gov`) |
| Debates, forums & interviews | YouTube, local news archives, civic organizations (League of Women Voters, etc.) — search "[Candidate Name] debate [Year]"; local papers often publish Q&A transcripts |
| News search (broad) | Corporate/mainstream and independent journalism alike; judge by coherence, logic, and evidence — not source prestige |

## Research Rigor & Citation Standards

All candidate information must come from live research, not training data. Training data may be used as a starting point to find leads or identify where to look, but never as a source of facts — candidates' positions, records, funding, and associations change, and training data goes stale. Even historical facts that predate the model's training cutoff should be verified against live sources.

1. **Verify before citing.** Fetch the specific page and confirm the information is actually there — the URL resolves, is not a 404 or homepage redirect, and the claimed content is present. If you cannot confirm it, flag it as unverified rather than presenting it as fact.

2. **Trace to the primary source.** Follow citation chains as far as possible. If the primary exists and is accessible online, cite it directly. If not (e.g. a printed document, paywalled archive, or offline record), cite the secondary source but note explicitly that the primary was not directly verified.

3. **Link to the specific page** — and the specific section if possible. Not a homepage, search result, or category page. Use anchor links (e.g. `#campaign-finance`) when available; preferred but not required.

4. **Use a consistent citation format** — inline or as a footnote:
   `[Organization, "Title or Description", Year](URL)`
   Example: `[OpenSecrets, "Andrew Example — 2026 Campaign Finance Summary", 2026](https://opensecrets.org/...)`

5. **Every claim gets a citation.** Funding figures, voting records, endorsements, biographical facts, policy positions, legal issues — all of it. Flag anything that cannot be sourced and verified as unconfirmed.

6. **The `*Sources: [list]*` footer is mandatory**, not optional.

## Rating System

Use this consistently in both candidate files and the summary:

| Symbol | Meaning |
|---|---|
| ✅ | Aligns well with voter values |
| ⚠️ | Mixed, unclear, or minor concern |
| 🚫 | Conflicts with voter values or disqualifying |

## Red Flag Checklist

### Red Flags

- **No campaign website** — in any race, any level, a missing website is a hard red flag
- **Extremely low viability** — polling at or near 0%, no meaningful support, no path to winning; flag as a fringe candidacy not worth deep research
- **No campaign finance data** — unexplained absence of filings; investigate before concluding
- **Campaign committee mislabeled or disorganized** — may indicate operational incompetence or compliance issues
- **Funding from special interests conflicting with stated positions** — note the conflict explicitly
- **Record of lying or misrepresenting past actions**
- **Careerism over substance** — pattern of seeking office without a meaningful platform, or a track record of voting with party leadership and special interests rather than in voters' interests in order to preserve their political position
- **Political platitudes** — vague, feel-good statements ("I support working people", "I care about the environment") with no specific policy substance; a candidate who relies on platitudes instead of demonstrating understanding of issues and proposing concrete solutions is a significant red flag
- **Word salad / substance evasion** — talking at length without saying anything, using circular language, or giving non-answers to direct questions; assess whether the candidate actually understands and believes what they're saying and whether they are likely to follow through
- **Rhetorical red flags**: ad hominem attacks, deflection instead of answers, scripted talking points, guilt by association, lack of substantive positions or coherent worldview
- **Positions that conflict with the voter's values** — always flag based on the voter's context file; use ⚠️ or 🚫 in the alignment table

### Highlight (Not Necessarily a Red Flag)

Note these in the profile and let the voter decide:

- **No voter guide statement filed** — may simply mean the candidate didn't meet the eligibility requirements (which vary by jurisdiction and can include contribution limits or filing fees); explain the local rules if known
- **Self-funded or unfunded campaign** — could mean the candidate is independently wealthy and deliberately avoiding donor influence; note the funding structure and let the voter assess
- **Active legal or regulatory issues** — describe the specifics; some legal challenges are legitimate concerns, others may be politically motivated harassment (lawfare); present the facts and let the voter decide
- **Endorsements** — list all endorsements for each candidate; what constitutes a "concerning" source is subjective and depends on the voter's values

## Tips

- **Write files as agents return** — don't wait for all to finish before writing any
- **Voting record**: for any candidate who has held office, prioritize their record over stated positions
- **Local races**: candidates may have thin online presence — this is acceptable, but a website is the minimum bar in any race; no website = red flag; note when other info is insufficient
- **Viability screening**: before deep-diving all candidates, do a quick polling and support check — identify the top contenders (roughly top 5, or fewer if it's a small field) so the voter can focus their attention; flag any candidates with negligible support as low-priority
- **Strategic voting**: in top-two primaries, note which candidates are actually viable for the general
- **Cross-reference**: if a candidate's stated positions conflict with their funding sources or voting record, flag it explicitly
