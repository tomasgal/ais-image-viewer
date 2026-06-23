#!/usr/bin/env python3
"""Generate a static HTML image viewer for JPEG/PNG files."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote

ALLOWED = (".jpg", ".jpeg", ".png")

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
html, body {{ margin:0