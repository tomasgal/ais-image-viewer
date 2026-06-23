# AIs Image Viewer

A small self-hosted image viewer and upload service for a local directory of JPEG/PNG images.

The project is intentionally simple:

- nginx serves a static image viewer.
- A Python standard-library upload server accepts JPEG/PNG files and ZIP archives containing JPEG/PNG files.
- The upload server stores images in one directory and regenerates the static `index.html`.
- The viewer starts with a file list, then opens a full-window image viewer with previous/next navigation and