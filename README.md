# AIs Image Viewer

A small self-hosted image viewer and upload service for a local directory of JPEG/PNG images.

Components: `scripts/ais-make-index.py` generates the static viewer; `scripts/ais-upload-server.py` accepts JPEG/PNG/ZIP uploads; `examples/nginx/ais.conf` and `examples/systemd/ais-upload.service` show one possible Linux deployment.

Default example paths are `/srv/ais/images` for images and `/srv/ais/web/index.html` for the generated viewer. Adjust them for your own server.

## Runtime notes

The