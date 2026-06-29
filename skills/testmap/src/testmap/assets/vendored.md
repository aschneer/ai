# Vendored Report Assets

The report's charting and markdown libraries are committed here as minified files
so the report works fully offline with no network dependency (PRD 8.1.2). They are
copied verbatim into each run's `testmap_output/report/` folder.

## Updating

To update a library: download the pinned URL below at the new version, replace the
file, recompute its SHA-256 (`sha256sum <file>`), and bump the version + hash here.
No build step or package manager is involved.

Files keep their upstream release names. The rendering layer references the stable
canonical names `chart.js` and `marked.js`, which are symlinks to the real release
files. On update, drop in the new file and repoint the symlink — references never
change, and this table still records exactly which file was downloaded. marked ships
no minified build by default, so its UMD source is vendored as-is.

Canonical symlinks: `chart.js` → `chart.umd.min.js`, `marked.js` → `marked.umd.js`.

| File | Library | Version | Source | SHA-256 |
|------|---------|---------|--------|---------|
| `chart.umd.min.js` | Chart.js (minified UMD) | 4.5.1 | https://github.com/chartjs/Chart.js/releases/tag/v4.5.1 | `48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a` |
| `marked.umd.js` | marked (UMD, unminified) | 18.0.5 | https://github.com/markedjs/marked/releases/tag/v18.0.5 | `2dc4769dfde29f51c7aca1a539c6407c789c8ea644cf8b7d01ded28a9c1d800b` |
