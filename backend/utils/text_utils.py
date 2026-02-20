"""
한글 텍스트 렌더링 유틸리티

OpenCV의 cv2.putText는 한글을 지원하지 않으므로
Pillow를 사용하여 한글 텍스트를 이미지에 렌더링합니다.
"""

import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import os

# 한글 폰트 경로 (Windows 맑은 고딕)
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",  # 맑은 고딕 Bold
    "C:/Windows/Fonts/malgun.ttf",     # 맑은 고딕
    "C:/Windows/Fonts/gulim.ttc",      # 굴림
    "C:/Windows/Fonts/batang.ttc",     # 바탕
]

_cached_fonts = {}


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """캐시된 한글 폰트를 반환합니다."""
    if size in _cached_fonts:
        return _cached_fonts[size]

    for font_path in _FONT_CANDIDATES:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size)
            _cached_fonts[size] = font
            return font

    # 폰트를 찾지 못한 경우 기본 폰트 사용
    font = ImageFont.load_default()
    _cached_fonts[size] = font
    return font


def get_text_size(text: str, font_size: int) -> tuple:
    """
    텍스트의 렌더링 크기를 반환합니다.

    Returns:
        (width, height) 튜플
    """
    font = _get_font(font_size)
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def put_korean_text(
    img: np.ndarray,
    text: str,
    position: tuple,
    font_size: int = 20,
    color: tuple = (255, 255, 255),
) -> np.ndarray:
    """
    OpenCV 이미지에 한글 텍스트를 렌더링합니다.

    Args:
        img: OpenCV BGR 이미지 (numpy array)
        text: 렌더링할 텍스트
        position: (x, y) 텍스트 시작 좌표 (좌측 상단)
        font_size: 폰트 크기 (픽셀)
        color: BGR 색상 튜플

    Returns:
        텍스트가 렌더링된 이미지 (원본 이미지가 직접 수정됨)
    """
    # BGR -> RGB 변환 후 PIL Image로 변환
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = _get_font(font_size)

    # BGR -> RGB 색상 변환
    color_rgb = (color[2], color[1], color[0])

    draw.text(position, text, font=font, fill=color_rgb)

    # PIL Image -> OpenCV BGR로 변환
    result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    np.copyto(img, result)
    return img
