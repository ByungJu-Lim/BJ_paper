---
name: figures-tables
description: Generates figures and tables from processed experiment data. Use once code-experiment has produced data/processed/ output.
---

# Figures and Tables

## Procedure

1. Delegate to `executor`: write a plotting/table-generation script under `code/` that reads from `data/processed/` and writes working images to `figures/*.png`. These are the venue-neutral renders used while drafting.
2. Take every render setting the venue controls — output format, DPI, figure width, colour mode, font — as **parameters of that script**, never as values hard-coded inside it. Journals differ on all of them, and a script that can only emit one variant has to be rewritten at every venue change.
3. Embed tables as Markdown tables (header, separator, data rows) and images as local Markdown links in the section. Put `Table 1: Description` immediately above the table or `Fig. 1: Description` immediately above `![Description](../../figures/fig1.png)`. Caption numbers must be unique by kind across sections. The story validator resolves evidence to these captions and files; a prose mention alone is not evidence.
4. Hand off to `critic` through the `paper-supervise` loop, using the rubric below.

## Figure and table review

Axis labels and units are the floor, not the review. A figure is an argument
about the data; these are the ways it can misstate one. Adapted from Tufte's
principles of graphical integrity and data density.

**Integrity — the figure must not say more than the data does**

| Check | Failure it catches |
|---|---|
| The visual magnitude of each mark is proportional to the number it represents | A truncated or expanded axis that turns a 3% gap into a visual chasm |
| Axis ranges are stated and justified; a non-zero baseline on a magnitude scale is deliberate and marked | The most common way a plot overstates a difference |
| Uncertainty is shown wherever a comparison is being made, and the interval is named (SD, SE, CI, IQR — which one) | An unlabelled error bar means nothing |
| Repetition count is on the figure or in its caption | A median over 10 seeds and over 2 look identical |
| The number of data dimensions in the graphic does not exceed the number in the data | 3-D bars and area-encoded volumes inflate differences |
| Every panel comparing the same quantity shares scale, or the break is marked | Free scales hide the effect being claimed |

**Density and clarity**

| Check | Failure it catches |
|---|---|
| Every mark carries information; gridlines, borders, shadows, and backgrounds that carry none are removed | Decoration competing with data |
| Repeated comparisons use small multiples with a shared scale rather than one crowded overlay | Six series in one panel is a legend, not a figure |
| The reader can find the intended comparison without decoding a legend across the plot | Colour-only encodings that fail in greyscale and for colour-blind readers |
| Table columns are ordered and aligned so the comparison being claimed reads down a column | A table nobody can read is a table nobody checks |
| Significant digits reflect the measurement, not the float | Six decimals on a quantity known to two |

**Correspondence — check against `data/processed/`, not against memory**

| Check | Failure it catches |
|---|---|
| Every number in a table appears in the processed data, traced to its run manifest | A number that drifted during a redraw |
| The caption states what the figure shows, not what the authors conclude from it | Conclusions smuggled into captions |
| The claim the section declares is the claim the figure actually supports | A figure carried over from a superseded claim |
| Nothing is plotted that no section references, and nothing referenced is missing | Orphaned figures and dangling `Fig. N` |

A figure that fails an integrity check is a `revise` verdict. Fix it in the
plotting script under `code/`, never in the exported image.

## Rendering for a venue

Venue-specific figures are produced by `submission-manage`, not here, and they are **generated output** — never hand-edited. The settings live in `submissions/NN-<venue-slug>/figure-profile.json` and the script reads them:

```json
{
  "format": "tiff",
  "dpi": 300,
  "column_width_mm": { "single": 90, "double": 190 },
  "color_mode": "cmyk",
  "min_font_pt": 7,
  "main_figures": ["fig1", "fig2"],
  "supplementary_figures": ["figS1"]
}
```

Rendered files land in `submissions/NN-<venue-slug>/figures/` and `check_submissions.py` fails if a figure named in `main_figures` is not actually there in the declared format.

Two things a page limit forces that are figure *content*, not formatting — merging panels, or moving a figure to supplementary — belong in `main_figures`/`supplementary_figures` and in the plotting script, not in a hand-touched export.
