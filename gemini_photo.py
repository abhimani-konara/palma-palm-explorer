"""Optional consent-based Gemini palm photo interpretation."""

import base64
import io
import os

import requests
from PIL import Image, ImageOps


def _prepare_photo(image_bytes):
    if not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
        raise ValueError("Invalid palm photo size")

    with Image.open(io.BytesIO(image_bytes)) as original:
        if original.width * original.height > 16_000_000:
            raise ValueError("Image resolution is too large")

        image = ImageOps.exif_transpose(original)
        image = image.convert("RGB")
        image.thumbnail((1280, 1280))

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=80)

    return {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(output.getvalue()).decode("ascii")
        }
    }


def analyze_palm_photos(left_bytes, right_bytes, consent=False):
    if consent is not True:
        return None

    if os.getenv("LLM_PROVIDER", "").lower() != "gemini":
        raise RuntimeError("Gemini mode is required")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini API key is missing")

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    instructions = (
        "You are an educational cultural palmistry guide. "
        "Describe only visible palm crease patterns and uncertainty. "
        "Explain traditional heart, head, life and fate line symbolism "
        "only when relevant. Do not claim that named palmistry lines, including simian lines, have been reliably identified. Describe visible crease shapes and positions with uncertainty. Explain traditional symbolism as hypothetical cultural stories, not factual conclusions. Do not infer personality, thoughts or emotions from images. "
        "Do not infer identity, health, lifespan, personality traits, "
        "wealth, relationships or future events as facts. "
        "This is entertainment, not scientific prediction. "
        "Keep the response under 200 words."
    )

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": "Left palm photo:"},
                _prepare_photo(left_bytes),
                {"text": "Right palm photo:"},
                _prepare_photo(right_bytes),
                {"text": instructions}
            ]
        }]
    }

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()
    text = "".join(
        part.get("text", "")
        for candidate in data.get("candidates", [])
        for part in candidate.get("content", {}).get("parts", [])
    ).strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response")

    return text
