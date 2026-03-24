from typing import Tuple


def extract_text_from_image_bytes(image_bytes: bytes) -> Tuple[str, str, list[str]]:
    """Try OCR using pytesseract if available.

    Returns:
        (text, engine, warnings)
    """
    warnings: list[str] = []

    try:
        from PIL import Image
    except Exception:
        return "", "none", ["Pillow 未安装，无法执行 OCR"]

    try:
        import pytesseract
    except Exception:
        return "", "none", ["pytesseract 未安装，无法执行 OCR"]

    try:
        import io

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        text = (pytesseract.image_to_string(image, lang="chi_sim+eng") or "").strip()
        if not text:
            warnings.append("OCR 未识别到文本，请检查截图清晰度")
        return text, "pytesseract", warnings
    except Exception as exc:
        return "", "none", [f"OCR 执行失败: {exc}"]
