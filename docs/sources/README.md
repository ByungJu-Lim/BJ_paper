# Downloaded Source Files

Full-text PDFs the user downloaded so a source could actually be read before it
was cited. Named by registry key: `docs/sources/<key>.pdf`.

**Nothing in this folder is committed.** Publisher PDFs are copyrighted, and this
repository is mirrored to a public host. `.gitignore` excludes everything here
except this README — do not add exceptions.

A file listed as `local_file` in `docs/notes/retrieved-sources.json` must exist
here on the machine doing the writing; `verify_source_registry.py` fails if it
does not. On another machine, download it again from the recorded `url` or `doi`.
