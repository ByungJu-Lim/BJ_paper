# Scientific Writing Rules

> User-specified rule, 2026-11-05. Applies to every manuscript text this project writes or revises:
> `docs/sections/*.md`, front matter (abstract, highlights), supplementary text and the cover letter.
>
> **Relation to the other project rules.** Where `CLAUDE.md` gives a more specific rule (manuscript
> formatting of 2026-10-11 and 2026-10-29, cover-letter rule of 2026-11-04, figure rules), that rule
> governs. The claim-status rules govern certainty: an `assumed` claim is never written as settled,
> whatever these rules say about hedging. The rules below never justify removing a number, condition,
> citation or qualifier that the evidence needs, and never justify adding one.
>
> **Keeping a needed number or condition never requires a long sentence.** Split the sentence, or state
> the condition once in Methods or a table and refer to it by name. Packing every qualifier into one
> sentence is the main source of unreadable drafts in this project (pipeline validation run 1 averaged
> 39-67 words per sentence in Results, Discussion and Conclusions, with sentences up to 209 words).
>
> **Mechanical gate (user rule 2026-11-12).** The hard limits in section 2 are checked by
> `python scripts/check_prose.py --sections "docs/sections/*.md"`. Text that fails it is not
> finished, and a `critic` review cannot pass it.

## 1. Core Writing Principles

All scientific writing must follow five principles:

1. Clarity: Express each idea in simple, direct, and unambiguous language.
2. Conciseness: Use the fewest words necessary to communicate the intended meaning without losing essential information.
3. Precision: Use technically accurate terms, quantitative evidence, and appropriately qualified statements.
4. Logic: Present information in a clear sequence that connects the research problem, methodology, evidence, and conclusions.
5. Objectivity: Prioritize evidence over rhetoric, speculation, or subjective evaluation.

Scientific accuracy takes precedence over brevity. Never remove information essential to understanding or reproducing the research. Accuracy is not a reason for long sentences: when a sentence must carry more information, split it.

## 2. Sentence Construction

Hard limits (checked by `scripts/check_prose.py`; failing text is a `revise` verdict):

| Limit | Value |
|---|---|
| Words per sentence | at most 35 |
| Mean words per sentence, per file (5+ sentences) | at most 22 |
| Words per paragraph | at most 180 |
| Colons and semicolons per sentence | at most 1 (no clause chains) |
| Inline enumeration such as "(a) ... (b) ... (c)" | not allowed; use a list or table |
| Phrases in `BANNED_PHRASES` of `scripts/check_prose.py` (fillers of sections 3 and 8) | not allowed |

Target 15-22 words. Methods and Results sentences that hold one number with its condition are usually 12-20 words.

If one paragraph genuinely cannot meet the limits (for example, it defines every symbol of an equation), put
`<!-- prose-ok: <reason> -->` on the line before it (blank lines may separate them, but no heading, table, equation or caption may). The checker exempts it from the length limits and prints
the reason. Use it rarely. A waiver needs a reason the critic accepts, and a waiver whose reason is only
"needs many conditions" is rejected.

Writing rules:

- Express one primary idea per sentence. A second claim, comparison or condition set starts a new sentence.
- Use subject–verb–object structure whenever possible.
- Write the condition once, then the result. Do not wrap a result in its conditions before and after.
  - Bad (illustrative values): "At the reference flow and 25 °C, and excluding the two start-up runs, the new design, which uses the smaller pump, reduced energy use by 12% relative to the baseline, which was operated at the same set point."
  - Good: "Both designs ran at the reference flow and 25 °C. Start-up runs were excluded (Section 2.3). The new design used 12% less energy than the baseline."
  - The example values are invented for illustration. Never copy them into a manuscript.
- Move repeated conditions (operating point, tie rule, case set) to Methods or a table. Give the set a short name and use the name afterwards.
- List three or more parallel items as a bulleted list or table, not inside a sentence.
- Put at most two numerical results in one sentence (three in the abstract, which has no tables). More numbers belong in a table that the sentence cites.
- Do not use a colon or semicolon to attach a second sentence. End the sentence instead.
- Keep parentheses for symbols, units, citations and cross-references. Do not hide a clause in parentheses.
- Place the main claim or finding early in the sentence.
- Prefer active voice when it improves clarity. Use passive voice when the process or result is more important than the actor.
- Avoid unnecessary subordinate clauses, nested structures, and long introductory phrases.
- Divide complex sentences when doing so improves readability.
- Ensure that each modifier clearly refers to the intended term.

## 3. Word Selection

- Prefer common, precise scientific terms over unnecessarily sophisticated vocabulary.
- Use one consistent term for each technical concept.
- Avoid synonyms that may imply different technical meanings.
- Prefer strong verbs over abstract nouns and verbose verb phrases.
- Remove redundant words, empty modifiers, and unnecessary qualifiers.
- Avoid promotional, emotional, or exaggerated expressions.
- Avoid vague adjectives such as significant, substantial, remarkable, and considerable unless their meaning is quantitatively or statistically supported.
- Retain established technical terminology when simpler alternatives would reduce precision.

Examples:

- "utilize" → "use"
- "in order to" → "to"
- "due to the fact that" → "because"
- "a large number of" → "many" or an exact number
- "conduct an analysis of" → "analyze"
- "has the capability to" → "can"
- "it is important to note that" → delete
- "the results clearly demonstrate that" → "the results show that"

## 4. Paragraph Structure

Each paragraph must communicate one central message. Use the following structure where appropriate:

1. Topic: State the main point.
2. Evidence: Present supporting data, methods, or observations.
3. Interpretation: Explain the meaning of the evidence.
4. Connection: Link the finding to the research question or next argument when needed.

Additional rules:

- Place the central message in the first sentence when possible.
- Arrange sentences in a logical sequence.
- Avoid repeating information within or across paragraphs.
- Use transitions only when they clarify relationships.
- Do not add concluding sentences that merely repeat earlier statements.
- Split paragraphs containing multiple independent arguments.

## 5. Logical Reasoning

- Every scientific claim must be supported by evidence, established theory, or an explicit assumption.
- Distinguish observations, interpretations, hypotheses, and conclusions.
- Do not confuse correlation with causation.
- Do not claim causality unless supported by the research design, physical principles, or appropriate analysis.
- Explain the physical or mathematical mechanism when it is necessary to understand a result.
- Present quantitative comparisons using clear reference conditions.
- Identify relevant assumptions, constraints, and uncertainties.
- Avoid conclusions that extend beyond the evidence.
- Do not introduce new claims in the conclusion without supporting results.

The preferred logical sequence is:
Research problem → Knowledge gap → Research objective → Method → Results → Interpretation → Contribution

## 6. Quantitative and Technical Reporting

- Prefer quantitative statements over qualitative descriptions.
- Include numerical values, units, baselines, and operating conditions when necessary.
- Distinguish absolute and relative changes.
- Distinguish percentage changes from percentage-point changes.
- Use consistent symbols, units, and terminology.
- Report uncertainty, variability, or statistical evidence when relevant.
- Distinguish statistical significance from practical or engineering significance.
- Avoid unsupported claims of optimality, robustness, superiority, or general applicability.
- Do not invent data, numerical results, citations, experimental conditions, or explanations.

## 7. Section-Specific Rules

### Abstract

- Present the problem, objective, method, main quantitative findings, and principal conclusion.
- Emphasize what was done and what was found.
- Prioritize the most important numerical findings.
- Avoid lengthy background descriptions, generic motivation, and unsupported claims.
- Every sentence must contribute new information.

### Introduction

- Establish the research problem and its importance.
- Summarize previous research by relevance, not as a disconnected list of studies.
- Identify the specific knowledge gap.
- Explain why the gap matters.
- State the research objective and contribution explicitly.
- Avoid broad statements that do not advance the research argument.

### Methods

- Describe methods in a reproducible and logically ordered manner.
- State critical assumptions and boundary conditions.
- Define variables, parameters, and performance metrics clearly.
- Avoid repeating standard procedures unless necessary for reproducibility.
- Separate methodological choices from results and interpretations.

### Results

- Lead with the main finding.
- Report what was observed. Interpretation belongs in the section that carries `Implication` (by default Discussion).
- State comparisons and reference conditions explicitly.
- Avoid describing every visible feature of a figure or table.
- Do not repeat complete numerical datasets already shown in figures or tables.
- Emphasize patterns, differences, and findings relevant to the research questions.

### Discussion

- Explain why the observed results occurred.
- Connect results to physical mechanisms and previous research.
- Distinguish supported explanations from hypotheses.
- Discuss relevant limitations and uncertainty.
- Focus on implications rather than repeating results.

### Conclusions

- Directly answer the research objectives.
- Summarize the principal findings and their implications.
- Avoid introducing new evidence or claims.
- Avoid generic claims of importance and unnecessary repetition.
- State limitations or future work only when relevant.

## 8. Prohibited Writing Patterns

Avoid the following unless scientifically justified:

- Long sentences containing multiple independent claims.
- Decorative vocabulary that does not improve precision.
- Repeated descriptions of the same result.
- Empty phrases such as "It is worth mentioning that..."
- Generic claims such as "This is a very important issue."
- Unsupported claims such as "This method is highly efficient."
- "Clearly," "obviously," "remarkably," and "interestingly" (banned outright by the checker).
- Excessive hedging that obscures established findings.
- Excessive certainty that exceeds the available evidence.
- Speculative mechanisms presented as proven facts.
- Fabricated references, experimental results, or statistical significance.

## 9. Revision and Quality Control

Before finalizing any scientific text, check:

0. Does `python scripts/check_prose.py --sections <files>` pass? Fix every violation by splitting or moving content, never by deleting needed information.
1. Can the main message of each paragraph be identified immediately?
2. Does every sentence contribute necessary information?
3. Can any sentence be shortened without losing meaning?
4. Are technical terms used consistently?
5. Are numerical claims supported by the available evidence?
6. Is the logical connection between evidence and conclusion explicit?
7. Are limitations and uncertainties represented accurately?
8. Are any statements redundant, vague, exaggerated, or unsupported?

Revise until all applicable conditions are satisfied.

## 10. LLM Execution Instructions

When drafting or revising scientific manuscripts:

- Preserve the original scientific meaning, numerical values, technical conditions, and level of certainty.
- Improve clarity, conciseness, logical flow, and technical precision.
- Remove redundancy without removing scientifically essential information.
- Do not add new scientific claims, references, data, or assumptions.
- Do not strengthen conclusions beyond the supporting evidence.
- Do not make sentences longer or more complex merely to sound academic.
- Draft, then run a compression pass before returning the text:
  1. Write each paragraph's message as one sentence. Delete any sentence that does not support it.
  2. Split every sentence over the limit. Move repeated conditions to Methods or a table.
  3. Delete restatements: a result stated in Results is referred to, not restated, in Discussion and Conclusions.
  4. Run `scripts/check_prose.py` and repeat until it passes.
- Report the checker's per-file mean and maximum with the returned text.
- Prefer straightforward scientific English over ornate academic prose.
- When a claim is ambiguous or unsupported, flag the issue rather than inventing a clarification.
- Return publication-ready scientific text unless explanations or tracked changes are requested.

Final priority order: Scientific accuracy → Logical consistency → Clarity → Precision of expression → Conciseness → Style.

This order decides what to keep when content conflicts. It does not relax the hard limits of section 2: accuracy and the limits are met together by splitting sentences.
