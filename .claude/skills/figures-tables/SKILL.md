---
name: figures-tables
description: Generates figures and tables from processed experiment data. Use once code-experiment has produced data/processed/ output.
---

# Figures and Tables

## Procedure

1. Delegate to `executor`: write a plotting/table-generation script under `code/` that reads from `data/processed/` and writes images to `figures/*.png`.
2. Embed any tables directly as Markdown tables in the relevant `docs/sections/*.md` file (not as images), with a one-line caption above each table and figure reference.
3. Hand off to `critic` through the `paper-supervise` loop: review checks axis labels, units, and caption accuracy against `data/processed/`.
