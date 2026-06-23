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

## Default example paths

The repository uses neutral example paths:

```text
/srv/ais/images
/srv/ais/web/index.html
```

Adjust them to match your own server. Do not commit private LAN IP addresses, local share names, or personal filesystem paths.

## Requirements

Debian/Raspberry Pi OS or another Linux distribution with:

```bash
sudo apt install nginx python3
```

No external Python packages are required.

## Generate the viewer

```bash
sudo mkdir -p /srv/ais/images /srv/ais/web
sudo python3 scripts/ais-make-index.py \
  --image-dir /srv/ais/images \
  --output /srv/ais/web/index.html \
  --file-url-prefix /ais/files
```

## Run the upload server manually

```bash
python3 scripts/ais-upload-server.py \
  --image-dir /srv/ais/images \
  --index-command "/usr/local/bin/ais-make-index.py --image-dir /srv/ais/images --output /srv/ais/web/index.html --file-url-prefix /ais/files" \
  --host 127.0.0.1 \
  --port 9080
```

In production, install it as a systemd service and put nginx in front of it.

## Upload behavior

Allowed uploads:

```text
.jpg
.jpeg
.png
.zip
```

ZIP archives are not stored as ZIP files. The service extracts allowed images into the image directory and deletes temporary files afterward.

Duplicate handling is name-based: if a file with the same target filename already exists, the upload is rejected for that file. The service does not overwrite the existing file and does not create `_1` copies.

Current limits in the script:

```text
single image: 100 MB
ZIP uncompressed total: 500 MB
ZIP file count: 1000 files
nginx example request size: 600 MB
```

## Viewer controls

The generated viewer supports:

- file list as the initial page,
- image open by clicking a filename,
- previous/next buttons,
- slideshow button,
- keyboard left/right navigation,
- `Esc` to return to the list,
- click left half of image for previous,
- click right half of image for next,
- `object-fit: contain`, so images are scaled to the browser viewport without cropping.

## Example nginx installation

Copy the example config and adjust paths/ports:

```bash
sudo cp examples/nginx/ais.conf /etc/nginx/sites-available/ais
sudo ln -s /etc/nginx/sites-available/ais /etc/nginx/sites-enabled/ais
sudo nginx -t
sudo systemctl reload nginx
```

## Example systemd installation

Copy scripts to production locations:

```bash
sudo cp scripts/ais-make-index.py /usr/local/bin/ais-make-index.py
sudo cp scripts/ais-upload-server.py /usr/local/bin/ais-upload-server.py
sudo chmod +x /usr/local/bin/ais-make-index.py /usr/local/bin/ais-upload-server.py
```

Then install the service:

```bash
sudo cp examples/systemd/ais-upload.service /etc/systemd/system/ais-upload.service
sudo systemctl daemon-reload
sudo systemctl enable --now ais-upload.service
sudo systemctl status ais-upload.service --no-pager
```

## Security notes

This is a small LAN-oriented service, not a hardened public upload platform.

Before exposing it outside a trusted network, add authentication, TLS, stricter upload limits, logging, and ideally an application-level framework with CSRF protection and stronger request validation.

The ZIP extraction logic avoids direct path extraction and only stores sanitized filenames, but the service should still be treated as local-network tooling unless further hardened.
