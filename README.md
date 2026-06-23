# AIs Image Viewer

A small self-hosted image viewer and upload service for a local directory of JPEG/PNG images.

The project is intentionally simple: nginx serves a static image viewer, a Python standard-library upload server accepts JPEG/PNG files and ZIP archives, uploaded images are stored in one directory, and the static `index.html` is regenerated after upload.

This repository contains anonymized, configurable versions of scripts originally deployed on a small Linux server.

## Components

- `scripts