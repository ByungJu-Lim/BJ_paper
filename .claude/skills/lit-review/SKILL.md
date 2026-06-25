---
name: lit-review
description: Searches for and organizes literature on a research topic, registering every real source found into docs/notes/retrieved-sources.json. Use when starting literature review or when a later stage needs an additional source.
---

# Literature Review

## Rule

Every entry in `docs/notes/retrieved-sources.json` must come from an actual search result (WebSearch or equivalent). Never invent an entry — `citation-manage` (Task 14) trusts this file as ground truth and will reject any citation whose key is missing from it.

## Procedure

1. Delegate to the `scientist` agent: search for papers/reports relevant to the given topic or keyword using WebSearch.
2. For each real result, append one object to `docs/notes/retrieved-sources.json`:
   ```json
   {
     "key": "<firstauthorsurname><year><oneword>",
     "title": "<exact title from the source>",
     "url": "<the URL actually returned by the search>",
     "retrieved_at": "<today's date, YYYY-MM-DD>"
   }
   ```
3. Write or update a summary note at `docs/notes/<topic-slug>.md` covering what the source claims and how it relates to the current paper's topic.
4. Hand off to `paper-supervise`, which routes the result through the critic for the `lit-review` stage's review round.
