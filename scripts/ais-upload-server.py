#!/usr/bin/env python3
"""
AIs Image Viewer upload server.

Small local upload service for JPEG/PNG images and ZIP archives containing
JPEG/PNG images. Intended to run behind nginx as a reverse proxy.

This script intentionally uses only the Python standard library.
"""

import argparse
import cgi
import html
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_SINGLE_FILE = 100 * 1024 * 1024
MAX_ZIP_TOTAL = 500 * 1024 * 1024
MAX_ZIP_FILES = 1000


class UploadConfig:
    image_dir = Path("/srv/ais/images")
    index_command = ["/usr/local/bin/ais-make-index.py"]
    host = "127.0.0.1"
    port = 9080
    viewer_url = "/ais/"
    upload_url = "/upload/"


def safe_filename(name: str | None) -> str:
    name = os.path.basename(name or "")
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    name = name.strip(" .")
    return name or "uploaded_file"


def is_allowed_image_name(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS


def looks_like_image(path: Path) -> bool:
    with path.open("rb") as f:
        head = f.read(16)

    if head.startswith(b"\xff\xd8\xff"):
        return True

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    return False


def save_image_file(src_path: Path, original_name: str, config: UploadConfig) -> tuple[str | None, str | None]:
    filename = safe_filename(original_name)

    if not is_allowed_image_name(filename):
        return None, "skipped: unsupported extension"

    if src_path.stat().st_size > MAX_SINGLE_FILE:
        return None, "skipped: file too large"

    if not looks_like_image(src_path):
        return None, "skipped: not a valid JPEG/PNG signature"

    target = config.image_dir / filename

    if target.exists():
        return None, "skipped: file already exists"

    shutil.copy2(src_path, target)
    os.chmod(target, 0o664)

    return target.name, None


def process_zip(zip_path: Path, config: UploadConfig) -> tuple[list[str], list[str]]:
    saved: list[str] = []
    errors: list[str] = []
    total_size = 0
    file_count = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for info in z.infolist():
                if info.is_dir():
                    continue

                file_count += 1
                if file_count > MAX_ZIP_FILES:
                    errors.append("zip skipped partly: too many files")
                    break

                total_size += info.file_size
                if total_size > MAX_ZIP_TOTAL:
                    errors.append("zip skipped partly: uncompressed total too large")
                    break

                filename = safe_filename(info.filename)

                if not is_allowed_image_name(filename):
                    continue

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    with z.open(info, "r") as src:
                        shutil.copyfileobj(src, tmp)

                try:
                    out_name, err = save_image_file(tmp_path, filename, config)
                    if out_name:
                        saved.append(out_name)
                    elif err:
                        errors.append(f"{filename}: {err}")
                finally:
                    tmp_path.unlink(missing_ok=True)

    except zipfile.BadZipFile:
        errors.append("bad zip file")

    return saved, errors


def regenerate_index(config: UploadConfig) -> tuple[bool, str | None]:
    try:
        subprocess.run(config.index_command, check=True)
        return True, None
    except Exception as e:
        return False, str(e)


def make_handler(config: UploadConfig):
    class UploadHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def send_html(self, status: int, body: str):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path

            if path not in ("/upload", "/upload/"):
                self.send_error(404)
                return

            self.send_html(200, f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AIs Upload</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: sans-serif; margin: 24px; max-width: 760px; }}
input, button {{ font-size: 16px; margin-top: 10px; }}
.note {{ color: #555; margin-top: 12px; }}
</style>
</head>
<body>
<h1>AIs Upload</h1>
<form method="post" enctype="multipart/form-data" action="{config.upload_url}">
  <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.zip,image/jpeg,image/png,application/zip">
  <br>
  <button type="submit">Upload</button>
</form>
<p class="note">Allowed: JPEG, PNG, ZIP containing JPEG/PNG.</p>
<p><a href="{config.viewer_url}">Back to viewer</a></p>
</body>
</html>
""")

        def do_POST(self):
            path = urlparse(self.path).path

            if path not in ("/upload", "/upload/"):
                self.send_error(404)
                return

            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                self.send_error(400, "Expected multipart/form-data")
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": ctype,
                },
            )

            fields = form["files"] if "files" in form else []
            if not isinstance(fields, list):
                fields = [fields]

            saved: list[str] = []
            errors: list[str] = []

            for field in fields:
                if not getattr(field, "filename", None):
                    continue

                original_name = safe_filename(field.filename)
                ext = os.path.splitext(original_name.lower())[1]

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    shutil.copyfileobj(field.file, tmp)

                try:
                    if ext == ".zip":
                        zip_saved, zip_errors = process_zip(tmp_path, config)
                        saved.extend(zip_saved)
                        errors.extend(zip_errors)
                    elif ext in ALLOWED_EXTENSIONS:
                        out_name, err = save_image_file(tmp_path, original_name, config)
                        if out_name:
                            saved.append(out_name)
                        elif err:
                            errors.append(f"{original_name}: {err}")
                    else:
                        errors.append(f"{original_name}: skipped: unsupported extension")
                finally:
                    tmp_path.unlink(missing_ok=True)

            ok, index_error = regenerate_index(config)
            if not ok:
                errors.append(f"index regeneration failed: {index_error}")

            saved_html = "".join(f"<li>{html.escape(x)}</li>" for x in saved) or "<li>Nothing saved</li>"
            errors_html = "".join(f"<li>{html.escape(x)}</li>" for x in errors) or "<li>No errors</li>"

            self.send_html(200, f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AIs Upload Result</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: sans-serif; margin: 24px; max-width: 900px; }}
</style>
</head>
<body>
<h1>Upload result</h1>
<h2>Saved</h2>
<ul>{saved_html}</ul>
<h2>Messages</h2>
<ul>{errors_html}</ul>
<p><a href="{config.viewer_url}">Open viewer</a></p>
<p><a href="{config.upload_url}">Upload more</a></p>
</body>
</html>
""")

    return UploadHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AIs image upload server.")
    parser.add_argument("--image-dir", default="/srv/ais/images", help="Directory where uploaded images are stored.")
    parser.add_argument("--index-command", default="/usr/local/bin/ais-make-index.py", help="Command used to regenerate the viewer index.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=9080, help="Bind port.")
    parser.add_argument("--viewer-url", default="/ais/", help="Viewer URL used in generated links.")
    parser.add_argument("--upload-url", default="/upload/", help="Upload URL used in generated forms.")
    args = parser.parse_args()

    config = UploadConfig()
    config.image_dir = Path(args.image_dir)
    config.index_command = args.index_command.split()
    config.host = args.host
    config.port = args.port
    config.viewer_url = args.viewer_url
    config.upload_url = args.upload_url

    config.image_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((config.host, config.port), make_handler(config))
    print(f"Listening on http://{config.host}:{config.port}/upload/")
    server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
