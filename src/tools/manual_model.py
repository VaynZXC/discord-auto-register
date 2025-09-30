"""Общая логика двухшагового распознавания плиток."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Iterable, Protocol

import cv2
from openai import OpenAI
__all__ = ["ask_model_for_tiles"]

class HasBBox(Protocol):
    bbox: Iterable[int]
    id: int


def _encode_file(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")

def ask_model_for_tiles(
    client: OpenAI,
    instruction: str,
    structure_overlay: Path,
    *,
    model: str = "gpt-4o",
    max_tiles: int | None = 3,
) -> dict:
    prompt = (
        "Ты решаешь визуальное задание. Инструкция пользователя: '"
        + instruction
        + "'.\n"
        "На изображении отмечены bounding-box тайлов с зелёными подписями tile #N."
        "Используй инструкцию и разметку, чтобы выбрать правильные tile #N."
        "Ответь строго JSON: {\"selected_ids\": [список целых], \"reason\": \"краткое объяснение почему\"}."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{_encode_file(structure_overlay)}", "detail": "high"},
                    },
                ],
            }
        ],
    )

    content = response.choices[0].message.content.strip().strip("` ")
    content = content.replace("json\n", "")
    data = json.loads(content)
    ids = data.get("selected_ids")
    if not isinstance(ids, list):
        ids = []
    selected_ids: list[int] = []
    seen: set[int] = set()
    for item in ids:
        if isinstance(item, int):
            idx = item
        elif isinstance(item, str):
            cleaned = ''.join(ch for ch in item if (ch.isdigit() or ch == '-'))
            if not cleaned or cleaned == '-':
                continue
            try:
                idx = int(cleaned)
            except ValueError:
                continue
        else:
            continue
        if idx < 0 or idx in seen:
            continue
        selected_ids.append(idx)
        seen.add(idx)
        if max_tiles and len(selected_ids) >= max_tiles:
            break
    data["selected_ids"] = selected_ids
    return data


