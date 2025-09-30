#!/usr/bin/env python3
"""Простейший инструмент разметки изображений прямоугольниками."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import cv2


@dataclass
class Annotation:
    label: str
    bbox: List[int]  # [x, y, w, h]


@dataclass
class SampleAnnotations:
    image: str
    annotations: List[Annotation]


class LabelTool:
    def __init__(self, image_path: Path, output_json: Path):
        self.image_path = image_path
        self.output_json = output_json
        self.image = cv2.imread(str(image_path))
        if self.image is None:
            raise FileNotFoundError(image_path)
        self.clone = self.image.copy()
        self.window_name = "label_tool"
        self.start_point: Optional[tuple[int, int]] = None
        self.end_point: Optional[tuple[int, int]] = None
        self.current_label = "object"
        self.annotations: List[Annotation] = []

    def run(self) -> None:
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        self._refresh()

        print("Инструкция:")
        print(" - Зажмите левую кнопку мыши и потяните, чтобы нарисовать прямоугольник")
        print(" - Нажмите 'l', чтобы сменить текущую метку (ввести текст в консоль)")
        print(" - Нажмите 'u', чтобы удалить последнюю аннотацию")
        print(" - Нажмите 's', чтобы сохранить и выйти")
        print(" - Нажмите 'q' или ESC, чтобы выйти без сохранения")

        while True:
            key = cv2.waitKey(50) & 0xFF
            if key == ord('q') or key == 27:
                print("Выход без сохранения")
                break
            if key == ord('u'):
                if self.annotations:
                    removed = self.annotations.pop()
                    print(f"Удалено: {removed}")
                    self._refresh()
            if key == ord('l'):
                new_label = input("Введите новую метку: ").strip()
                if new_label:
                    self.current_label = new_label
                    print(f"Текущая метка: {self.current_label}")
            if key == ord('s'):
                self.save()
                print("Сохранено и выход")
                break

        cv2.destroyAllWindows()

    def _refresh(self) -> None:
        self.image = self.clone.copy()
        for ann in self.annotations:
            x, y, w, h = ann.bbox
            cv2.rectangle(self.image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(self.image, ann.label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow(self.window_name, self.image)

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start_point = (x, y)
            self.end_point = None
        elif event == cv2.EVENT_MOUSEMOVE and self.start_point is not None:
            temp = self.clone.copy()
            cv2.rectangle(temp, self.start_point, (x, y), (0, 255, 255), 2)
            for ann in self.annotations:
                ax, ay, aw, ah = ann.bbox
                cv2.rectangle(temp, (ax, ay), (ax + aw, ay + ah), (0, 255, 0), 2)
                cv2.putText(temp, ann.label, (ax, ay - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(self.window_name, temp)
        elif event == cv2.EVENT_LBUTTONUP and self.start_point is not None:
            self.end_point = (x, y)
            x0, y0 = self.start_point
            x1, y1 = self.end_point
            x_min, x_max = sorted([x0, x1])
            y_min, y_max = sorted([y0, y1])
            w = max(1, x_max - x_min)
            h = max(1, y_max - y_min)
            ann = Annotation(label=self.current_label, bbox=[x_min, y_min, w, h])
            self.annotations.append(ann)
            print(f"Добавлено: {ann}")
            self.start_point = None
            self.end_point = None
            self._refresh()

    def save(self) -> None:
        payload = SampleAnnotations(
            image=str(self.image_path.name),
            annotations=self.annotations,
        )
        with self.output_json.open("w", encoding="utf-8") as f:
            json.dump(asdict(payload), f, ensure_ascii=False, indent=2)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Утилита разметки скриншотов hCaptcha")
    parser.add_argument("image", help="Путь к изображению")
    parser.add_argument("output", help="Куда сохранить JSON с аннотациями")
    args = parser.parse_args()

    tool = LabelTool(Path(args.image), Path(args.output))
    tool.run()


if __name__ == "__main__":
    main()

