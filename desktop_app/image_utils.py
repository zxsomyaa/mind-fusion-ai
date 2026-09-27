"""
Loads a photo from disk for the meal-analysis feature, and - when it can't -
says *why*, instead of a generic "couldn't read that image".

Order of attempts:
  1. Qt's own reader (handles JPEG/PNG/HEIC/WebP/etc. and applies the phone's
     rotation flag, so portrait photos aren't sideways)
  2. OpenCV (a second, independent decoder)
  3. macOS's built-in `sips` tool, which converts almost any image format
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QImage, QImageReader

IMAGE_FILE_FILTER = "Images (*.png *.jpg *.jpeg *.jfif *.heic *.heif *.webp *.bmp *.tif *.tiff *.gif)"


class ImageLoadError(Exception):
    """Raised with a message that is safe to show to the user as-is."""


def _check_file_access(path):
    """Opens the file directly so a permissions problem shows up as itself.
    On macOS, an app that hasn't been allowed into Desktop / Documents /
    Downloads gets 'Operation not permitted' here, which Qt's image reader
    would just report as a failed decode."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except PermissionError:
        raise ImageLoadError(
            "macOS is blocking access to that file. Allow Python (or your terminal / editor) under "
            "System Settings → Privacy & Security → Files and Folders (or Full Disk Access), "
            "or copy the photo to another folder and try again."
        )
    except FileNotFoundError:
        raise ImageLoadError("That file no longer exists - it may have been moved or deleted.")
    except OSError as exc:
        raise ImageLoadError(f"Couldn't open the file: {exc.strerror or exc}.")
    if not head:
        raise ImageLoadError("That file is empty.")


def _read_with_qt(path):
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)  # honour the camera's rotation flag
    image = reader.read()
    return image, reader.errorString()


def _read_with_opencv(path):
    try:
        import cv2
    except ImportError:
        return None
    array = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if array is None:
        return None
    rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()


def _read_with_sips(path):
    """macOS only: convert to a temporary JPEG, then load that."""
    if sys.platform != "darwin":
        return None
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "converted.jpg"
        try:
            subprocess.run(
                ["sips", "-s", "format", "jpeg", str(path), "--out", str(out)],
                check=True, capture_output=True, timeout=30,
            )
        except (subprocess.SubprocessError, OSError):
            return None
        image, _ = _read_with_qt(out)
        return None if image.isNull() else image


def load_image_any(path):
    """Returns a QImage, or raises ImageLoadError with a user-facing reason."""
    path = Path(path)
    _check_file_access(path)

    image, qt_reason = _read_with_qt(path)
    if not image.isNull():
        return image

    for fallback in (_read_with_opencv, _read_with_sips):
        image = fallback(path)
        if image is not None and not image.isNull():
            return image

    suffix = path.suffix or "no extension"
    raise ImageLoadError(
        f"Couldn't read this image ({suffix}): {qt_reason or 'unsupported or damaged file'}. "
        "Try saving or exporting it as a JPEG or PNG."
    )
