---
name: figures-tables
description: Generates figures and tables from processed experiment data. Use once code-experiment has produced data/processed/ output.
---

# Figures and Tables

## Procedure

1. Delegate to `executor`: write a plotting/table-generation script under `code/` that reads from `data/processed/` and writes working images to `figures/*.png`. These are the venue-neutral renders used while drafting.
2. Take every render setting the venue controls — output format, DPI, figure width, colour mode, font — as **parameters of that script**, never as values hard-coded inside it. Journals differ on all of them, and a script that can only emit one variant has to be rewritten at every venue change.
3. Embed tables as Markdown tables (header, separator, data rows) and images as local Markdown links in the section. Put `Table 1: Description` immediately above the table or `Fig. 1: Description` immediately above `![Description](../../figures/fig1.png)`. Caption numbers must be unique by kind across sections. The story validator resolves evidence to these captions and files; a prose mention alone is not evidence.
4. Hand off to `critic` through the `paper-supervise` loop: review checks axis labels, units, and caption accuracy against `data/processed/`.

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
