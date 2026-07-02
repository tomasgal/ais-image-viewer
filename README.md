# AIs Image Viewer

A small self-hosted image viewer and upload service for a local directory of JPEG/PNG images.

The project is intentionally simple:

* nginx serves a static image viewer.
* A Python standard-library upload server accepts JPEG/PNG files and ZIP archives containing JPEG/PNG files.
* The upload server stores images in one directory and regenerates the static `index.html`.
* The viewer starts with a file list, then opens a full-window image viewer with previous/next navigation and slideshow support.
* An optional maintenance script can normalize AI-image metadata and harmonize filenames.

This repository contains anonymized, configurable versions of scripts originally deployed on a small Linux server.

## Components

| File                                  | Purpose                                                        |
| ------------------------------------- | -------------------------------------------------------------- |
| `scripts/ais-make-index.py`           | Generates `index.html` from an image directory.                |
| `scripts/ais-upload-server.py`        | Runs a local upload server for JPEG/PNG/ZIP uploads.           |
| `scripts/ais-normalize-images.py`     | Optionally normalizes AI metadata and anonymizes filenames.    |
| `web/index.html`                      | Placeholder generated index. Replace by running the generator. |
| `examples/nginx/ais.conf`             | Example nginx site configuration.                              |
| `examples/systemd/ais-upload.service` | Example systemd unit for the upload service.                   |

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

The optional metadata and filename normalization script additionally requires ExifTool:

```bash
sudo apt install libimage-exiftool-perl
```

## Development environment and maintenance notes

The original prototype was developed on a Raspberry Pi 3 running a 32-bit ARMv7 Raspberry Pi OS/Raspbian system with Linux kernel `6.6.31+rpt-rpi-v7` from the Raspberry Pi kernel build dated 2024-05-29. In human terms: this project was designed to work on modest Raspberry Pi hardware, without Docker, without a database, and without a heavyweight document-management or gallery application.

`ais-upload-server.py` currently uses Python’s standard-library `cgi` module for parsing multipart form uploads. On Debian Bookworm with Python 3.11 this is acceptable and works for this small LAN-oriented tool. However, the `cgi` module is historically deprecated and may become a problem in future Python versions. For longer-term maintenance, it would be reasonable to replace this part with a small Flask/FastAPI-based upload handler or with a dedicated multipart parser.

Empirically, the current repository is consistent and usable for the intended small self-hosted LAN deployment.

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

## Optional filename and metadata normalization

`scripts/ais-normalize-images.py` is an optional daily maintenance tool for directories that contain AI-generated images. It is not required for the viewer or upload service to work.

The script uses the filename as a processing marker. Files whose basename already matches this pattern are skipped:

```text
xxxx-xxxx-xxxx-xxxx.jpg
xxxx-xxxx-xxxx-xxxx.jpeg
xxxx-xxxx-xxxx-xxxx.png
```

Each `x` is a lowercase letter or digit. For files that do not yet match the pattern, the script performs this pipeline:

1. remove embedded content-oriented metadata with ExifTool,
2. copy back selected technical metadata where available: ICC profile, orientation, and PNG sRGB rendering information,
3. write a small homogeneous XMP metadata profile,
4. rename the file to a random browser-safe filename while keeping the original extension type,
5. optionally regenerate the static `index.html`.

The XMP metadata written by the script is:

```text
Digital Source Type: http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia
Description: AI-generated image
Creator Tool: AIs image viewer import pipeline
Subject / keywords: ai-generated, synthetic-media
```

The `Digital Source Type` value is an IPTC controlled-vocabulary URI. Human-facing software may display this as “Created using Generative AI”. The script does not store prompts, model names, generation settings, author names, copyright notices, or usage terms.

Run a dry run first:

```bash
python3 scripts/ais-normalize-images.py \
  --image-dir /srv/ais/images \
  --index-command "python3 scripts/ais-make-index.py --image-dir /srv/ais/images --output /srv/ais/web/index.html --file-url-prefix /ais/files" \
  --dry-run
```

Then run it for real:

```bash
python3 scripts/ais-normalize-images.py \
  --image-dir /srv/ais/images \
  --index-command "python3 scripts/ais-make-index.py --image-dir /srv/ais/images --output /srv/ais/web/index.html --file-url-prefix /ais/files"
```

Example daily cron entry:

```cron
25 3 * * * nice -n 10 ionice -c2 -n7 /usr/local/bin/ais-normalize-images.py --image-dir /srv/ais/images --index-command "/usr/local/bin/ais-make-index.py --image-dir /srv/ais/images --output /srv/ais/web/index.html --file-url-prefix /ais/files" >>/var/log/ais-normalize.log 2>&1
```

### Normalization limitations

This script is for library hygiene and visual/metadata uniformity. It is not a cryptographic anonymization or provenance system.

Important limitations:

* The filename pattern is treated as the processing marker. If a file is manually named in the anonymous pattern before processing, the script will skip it even if its metadata is not normalized.
* The script checks uniqueness of the complete target filename, including the extension. A duplicate random stem with a different extension is accepted, for example `abcd-1234-efgh-5678.jpg` and `abcd-1234-efgh-5678.png`.
* The random namespace is very large: `36^16`, or approximately `7.96 × 10^24` possible stems.
* The script checks that the target file does not exist before renaming. It does not implement a filesystem-wide lock or a fully atomic no-overwrite rename. If another process creates or replaces the exact same target path at the same moment, a race condition is theoretically possible.
* Do not run multiple normalization instances against the same directory at the same time.
* Failed files are left under their original names and can be retried by a later run.
* The script does not re-encode images and does not alter pixel data intentionally.
* The script does not verify that an image was actually generated by AI. It only writes a homogeneous metadata label for files in the managed directory.
* ExifTool’s `-P` option is used to preserve the filesystem modification time where possible, but inode change time and directory timestamps can still change because the file is edited and renamed.
* The script preserves only selected technical metadata. Other embedded metadata or format-specific chunks may be removed.

## Viewer controls

The generated viewer supports:

* file list as the initial page,
* image open by clicking a filename,
* previous/next buttons,
* slideshow button,
* keyboard left/right navigation,
* `Esc` to return to the list,
* click left half of image for previous,
* click right half of image for next,
* `object-fit: contain`, so images are scaled to the browser viewport without cropping.

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
sudo cp scripts/ais-normalize-images.py /usr/local/bin/ais-normalize-images.py
sudo chmod +x /usr/local/bin/ais-make-index.py /usr/local/bin/ais-upload-server.py /usr/local/bin/ais-normalize-images.py
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

The normalization script improves filename and metadata uniformity, but it does not provide access control, encryption, reliable provenance, or forensic anonymity. Treat it as housekeeping, not as a privacy boundary.
