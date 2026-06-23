#!/usr/bin/env python3
"""
AIs Image Viewer index generator.

Scans an image directory for JPEG/PNG files and generates a static HTML viewer.
The generated page starts with a file list and opens a full-window viewer after
the user selects an image.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import quote

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")


def build_images(image_dir: Path, file_url_prefix: str) -> list[dict[str, str]]:
