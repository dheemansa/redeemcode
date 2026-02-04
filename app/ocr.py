import cv2
import pytesseract
import re
import os

import numpy as np

# Crop Constants (Ratios relative to image size)
CROP_HEIGHT_START = 0.70
CROP_HEIGHT_END = 0.90
CROP_WIDTH_START = 0.30
CROP_WIDTH_END = 0.75


def extract_redeem_code(image_input, debug=False):
    """
    Extracts a 16-character Google Play redeem code from an image.
    Args:
        image_input: Can be a file path (str) or a byte object (memory buffer).
    """
    img = None

    # 1. Load Image
    if isinstance(image_input, str):
        # It's a file path
        if not os.path.exists(image_input):
            print(f"Error: File '{image_input}' not found.")
            return None
        img = cv2.imread(image_input)
    elif isinstance(image_input, bytes):
        # It's raw bytes (from Telethon download)
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        print("Error: Invalid input type. Expected file path (str) or bytes.")
        return None

    if img is None:
        print("Error: Could not decode image.")
        return None

    # 2. Preprocessing
    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Crop to bottom section (Optimization: The code is usually at the bottom)
    height, width, _ = img.shape

    y_start = int(height * CROP_HEIGHT_START)
    y_end = int(height * CROP_HEIGHT_END)
    x_start = int(width * CROP_WIDTH_START)
    x_end = int(width * CROP_WIDTH_END)

    # image[ y_start : y_end , x_start : x_end ]
    img_cropped = img[y_start:y_end, x_start:x_end]

    if debug:
        # Debug: Save the cropped image
        debug_filename = "debug_crop.jpg"
        cv2.imwrite(debug_filename, img_cropped)
        print(f"DEBUG: Saved cropped image to '{debug_filename}'")

    # 3. Tesseract Configuration
    # --psm 6: Assume a single uniform block of text.
    # whitelist: Alphanumeric only (A-Z, 0-9) + common separators
    custom_config = (
        r'--psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789: ."'
    )

    try:
        # Run OCR on color image
        text = pytesseract.image_to_string(img_cropped, config=custom_config)
        if debug:
            print(f"DEBUG: Raw Text:\n{text}")
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract is not installed or not in PATH.")
        return None

    # 4. Extract Code using Regex
    # Pattern: Look for exactly 16 alphanumeric characters.
    # We replace common noise chars with space to ensure we don't merge lines unexpectedly.
    clean_text = text.replace(":", " ").replace(".", " ").replace("\n", " ")

    # Find all sequences of 16 alphanumeric characters
    # We don't use \b because the cleaning might leave it adjacent to spaces which is fine,
    # but strictly checking length 16 is key.
    candidates = re.findall(r"[A-Z0-9]{16}", clean_text)

    # Filter candidates: Usually codes have a mix of letters and numbers,
    # but strict 16 chars is the strongest signal.
    for candidate in candidates:
        # Format: XXXX-XXXX-XXXX-XXXX
        formatted_code = "-".join(
            candidate[i : i + 4] for i in range(0, len(candidate), 4)
        )
        return formatted_code

    return None
