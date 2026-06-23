# AIs Image Viewer

A small self-hosted image viewer and upload service for a local directory of JPEG/PNG images.

The project is intentionally simple:

- nginx serves a static image viewer.
- A Python standard-library upload server accepts JPEG/PNG files and ZIP archives containing JPEG/PNG files.
- The upload server stores images in one directory and regenerates the static `index.html`.
- The viewer starts with a file list, then opens a full-window image viewer with previous/next navigation and slideshow support.

This repository contains anonymized, configurable versions of scripts originally deployed on a small Linux server.

## Components

| File | Purpose |
|---|---|
| `scripts/ais-make-index.py` | Generates `index.html` from an image directory. |
| `scripts/ais-upload-server.py` | Runs a local upload server for JPEG/PNG/ZIP uploads. |
| `web/index.html` | Placeholder generated index. Replace by running the generator. |
| `examples/nginx/ais.conf` | Example nginx site configuration. |
| `examples/systemd/ais-upload.service` | Example systemd unit for the upload service. |

