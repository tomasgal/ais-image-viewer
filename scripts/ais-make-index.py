#!/usr/bin/env python3
"""
AIs Image Viewer index generator.

Scans an image directory for JPEG/PNG files and generates a static HTML viewer.
The generated page starts with a file list and opens a full-window viewer after
the user selects an image.

This script intentionally uses only the Python standard library.
"""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote


ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")


def build_images(image_dir: Path, file_url_prefix: str) -> list[dict[str, str]]:
    files = [
        item.name
        for item in sorted(image_dir.iterdir(), key=lambda p: p.name.lower())
        if item.is_file() and item.name.lower().endswith(ALLOWED_EXTENSIONS)
    ]

    return [
        {
            "name": name,
            "url": file_url_prefix.rstrip("/") + "/" + quote(name),
        }
        for name in files
    ]


def render_html(images: list[dict[str, str]], title: str) -> str:
    images_json = json.dumps(images, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
html, body {{
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: #111;
  color: #eee;
  font-family: sans-serif;
}}

#listPage {{
  padding: 20px;
}}

h1 {{
  margin-top: 0;
}}

.filelist {{
  max-width: 1100px;
  margin-top: 16px;
}}

.fileitem {{
  display: block;
  padding: 9px 12px;
  margin-bottom: 6px;
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 6px;
  color: #eee;
  text-decoration: none;
  word-break: break-all;
}}

.fileitem:hover {{
  background: #2a2a2a;
}}

#viewerPage {{
  display: none;
  height: 100vh;
}}

#topbar {{
  box-sizing: border-box;
  height: 48px;
  padding: 10px 16px;
  background: #1d1d1d;
  display: flex;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid #333;
}}

button {{
  padding: 5px 10px;
}}

#filename {{
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}}

#viewer {{
  height: calc(100% - 48px);
  display: flex;
  align-items: center;
  justify-content: center;
}}

#image {{
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: pointer;
}}
</style>
</head>
<body>

<div id="listPage">
  <h1>{title}</h1>

  <form method="post" enctype="multipart/form-data" action="/upload/" style="margin-bottom: 16px;">
    <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.zip,image/jpeg,image/png,application/zip">
    <button type="submit">Upload</button>
  </form>

  <div id="summary"></div>
  <div class="filelist" id="filelist"></div>
</div>

<div id="viewerPage">
  <div id="topbar">
    <button onclick="showList()">List</button>
    <button onclick="prevImage()">Prev</button>
    <button onclick="nextImage()">Next</button>
    <button onclick="toggleSlideshow()" id="slideshowButton">Start slideshow</button>
    <span id="counter"></span>
    <span id="filename"></span>
  </div>

  <div id="viewer">
    <img id="image" alt="">
  </div>
</div>

<script>
const images = {images_json};

let current = 0;
let timer = null;

function buildList() {{
  const summary = document.getElementById("summary");
  const filelist = document.getElementById("filelist");

  summary.textContent = images.length + " image(s)";
  filelist.innerHTML = "";

  images.forEach((item, index) => {{
    const link = document.createElement("a");
    link.href = "#";
    link.className = "fileitem";
    link.textContent = item.name;
    link.addEventListener("click", function(event) {{
      event.preventDefault();
      openViewer(index);
    }});
    filelist.appendChild(link);
  }});
}}

function showList() {{
  if (timer) {{
    clearInterval(timer);
    timer = null;
    document.getElementById("slideshowButton").textContent = "Start slideshow";
  }}

  document.getElementById("viewerPage").style.display = "none";
  document.getElementById("listPage").style.display = "block";
}}

function openViewer(index) {{
  document.getElementById("listPage").style.display = "none";
  document.getElementById("viewerPage").style.display = "block";
  showImage(index);
}}

function showImage(i) {{
  if (images.length === 0) {{
    showList();
    return;
  }}

  current = (i + images.length) % images.length;
  const item = images[current];

  const img = document.getElementById("image");
  img.src = item.url;
  img.alt = item.name;

  document.getElementById("counter").textContent = (current + 1) + " / " + images.length;
  document.getElementById("filename").textContent = item.name;
}}

function prevImage() {{
  showImage(current - 1);
}}

function nextImage() {{
  showImage(current + 1);
}}

function toggleSlideshow() {{
  const button = document.getElementById("slideshowButton");

  if (timer) {{
    clearInterval(timer);
    timer = null;
    button.textContent = "Start slideshow";
  }} else {{
    timer = setInterval(nextImage, 5000);
    button.textContent = "Stop slideshow";
  }}
}}

document.getElementById("image").addEventListener("click", function(event) {{
  const rect = event.target.getBoundingClientRect();
  const x = event.clientX - rect.left;

  if (x < rect.width / 2) {{
    prevImage();
  }} else {{
    nextImage();
  }}
}});

document.addEventListener("keydown", function(event) {{
  if (document.getElementById("viewerPage").style.display !== "block") return;

  if (event.key === "ArrowLeft") prevImage();
  if (event.key === "ArrowRight") nextImage();

  if (event.key === " ") {{
    event.preventDefault();
    toggleSlideshow();
  }}

  if (event.key === "Escape") showList();
}});

buildList();
showList();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a static image viewer index.")
    parser.add_argument("--image-dir", default="/srv/ais/images", help="Directory containing JPEG/PNG images.")
    parser.add_argument("--output", default="/srv/ais/web/index.html", help="Output HTML file.")
    parser.add_argument("--file-url-prefix", default="/ais/files", help="URL prefix used to serve image files.")
    parser.add_argument("--title", default="AIs Image Viewer", help="HTML page title.")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    output = Path(args.output)

    output.parent.mkdir(parents=True, exist_ok=True)
    images = build_images(image_dir, args.file_url_prefix)
    output.write_text(render_html(images, args.title), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
