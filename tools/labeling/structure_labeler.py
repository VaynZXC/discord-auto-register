#!/usr/bin/env python3
"""Интерактивная разметка структуры капч."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import cv2
import numpy as np
import shutil

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vision import detect_structure


TRAIN_DIR_NAME = "train"
VAL_DIR_NAME = "val"

LABEL_LIST = [
    "instruction",
    "body",
    "tile",
    "ball",
    "target_ball",
]

LABEL_KEYS: Dict[int, str] = {
    ord('1'): "instruction",
    ord('2'): "body",
    ord('3'): "tile",
    ord('4'): "ball",
    ord('5'): "target_ball",
}


@dataclass
class Annotation:
    label: str
    bbox: List[int]  # [x, y, w, h]
    origin: str = "manual"  # manual or model
    meta: Dict[str, str] | None = None


@dataclass
class AnnotationFile:
    image: str
    annotations: List[Annotation]


class AnnotationSession:
    def __init__(self, image_path: Path, output_path: Path, split_root: Optional[Path] = None):
        self.image_path = image_path
        self.output_path = output_path
        self.split_root = split_root
        self.image = cv2.imread(str(image_path))
        if self.image is None:
            raise FileNotFoundError(image_path)
        self.base = self.image.copy()
        self.annotations: List[Annotation] = []
        self.current_index = 2  # default tile (можно поменять на 3 для ball)
        self.current_label = LABEL_LIST[self.current_index]
        self.window_name = f"annotate: {image_path.name}"
        self.start_point: Optional[tuple[int, int]] = None

        self.image_height, self.image_width = self.image.shape[:2]
        self.toolbar_buttons: List[tuple[int, int, int, int, str]] = []
        self.submit_button: Optional[tuple[int, int, int, int]] = None
        self.button_height = 36
        self.button_spacing = 12
        self.padding = 18
        base_height = (
            self.padding * 2
            + len(LABEL_LIST) * self.button_height
            + max(0, len(LABEL_LIST) - 1) * self.button_spacing
        )
        self.panel_height = base_height + self.button_height + self.padding * 2
        self.display_image: Optional[np.ndarray] = None
        self.submit_clicked = False

        self.overlay = self._load_overlay()
        self.overlay_gap = 10 if self.overlay is not None else 0
        if self.overlay is not None and self.overlay.shape[0] != self.image_height:
            overlay_w = int(self.overlay.shape[1] * (self.image_height / self.overlay.shape[0]))
            self.overlay = cv2.resize(self.overlay, (overlay_w, self.image_height))
        self.overlay_width = self.overlay.shape[1] if self.overlay is not None else 0

        self.model_shapes: List[Annotation] = []
        self.selected_index: Optional[int] = None
        self.drag_start: Optional[tuple[int, int]] = None
        self.drag_bbox: Optional[List[int]] = None
        self.resize_mode: Optional[str] = None
        self.resize_start: Optional[tuple[int, int]] = None
        self.drag_mode: Optional[str] = None

        self.current_split: Optional[str] = None
        if split_root:
            self.current_split = self._detect_current_split()

        self._load_existing()

    def _load_existing(self) -> None:
        if not self.output_path.exists():
            return
        try:
            data = json.loads(self.output_path.read_text(encoding="utf-8"))
            anns = data.get("annotations", [])
            for item in anns:
                bbox = item.get("bbox")
                label = item.get("label")
                origin = item.get("origin", "manual")
                if isinstance(bbox, list) and label:
                    self.annotations.append(Annotation(label=label, bbox=[int(v) for v in bbox], origin=origin))
        except Exception:
            pass

    def run(self) -> str:
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        self._refresh()

        self._print_help()

        result = "next"
        while True:
            key = cv2.waitKey(50) & 0xFF
            if key == 255:
                if self.submit_clicked:
                    result = "next"
                    break
                continue
            if key == ord('^'):
                self.ctrl_down = True
            if key in (27, ord('q')):
                result = "exit"
                break
            if key == ord('n'):
                self.save()
                result = "next"
                break
            if key == ord('k'):
                result = "skip"
                break
            if key == ord('s'):
                self.save()
                print("Сохранено")
            if key == ord('u'):
                if self.annotations:
                    removed = self.annotations.pop()
                    print(f"Удалено: {removed.label} {removed.bbox}")
                    self._refresh()
            if key in LABEL_KEYS:
                self.current_label = LABEL_KEYS[key]
                if self.current_label in LABEL_LIST:
                    self.current_index = LABEL_LIST.index(self.current_label)
                print(f"Текущая метка: {self.current_label}")
                self._refresh()
            if key == ord('t'):
                self.current_index = (self.current_index + 1) % len(LABEL_LIST)
                self.current_label = LABEL_LIST[self.current_index]
                print(f"Текущая метка: {self.current_label}")
                self._refresh()

        cv2.destroyWindow(self.window_name)
        return result

    def _print_help(self) -> None:
        print("\n=== Разметка изображения ===")
        print(f"Файл: {self.image_path}")
        print("Управление:")
        print(" - ЛКМ: создать прямоугольник")
        print(" - Перетащить рамку: ЛКМ + drag")
        print(" - Изменить размер: потянуть за кружок в углу рамки")
        print(" - Колесо нажать: удалить выбранную рамку")
        print(" - 1..4: быстрый выбор метки (1=instruction, 2=body, 3=tile, 4=ball)")
        print(" - t: переключить метку по циклу")
        print(" - u: удалить последнюю аннотацию")
        print(" - s: сохранить (остаться на изображении)")
        print(" - n: сохранить и перейти к следующему")
        print(" - k: пропустить изображение")
        print(" - q или ESC: выход из программы")

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_RBUTTONDOWN:
            if self.selected_index is not None and 0 <= self.selected_index < len(self.annotations):
                removed = self.annotations.pop(self.selected_index)
                print(f"Удалено (ПКМ): {removed.label} {removed.bbox}")
                self.selected_index = None
                self._refresh()
            elif self.annotations:
                removed = self.annotations.pop()
                print(f"Удалено (ПКМ): {removed.label} {removed.bbox}")
                self._refresh()
            return

        if event == cv2.EVENT_MBUTTONDOWN and self.selected_index is not None:
            removed = self.annotations.pop(self.selected_index)
            print(f"Удалено (колесо): {removed.label} {removed.bbox}")
            self.selected_index = None
            self._refresh()
            return

        # Клики по панели инструментов
        if y >= self.image_height:
            if event == cv2.EVENT_LBUTTONDOWN:
                action = self._handle_toolbar_click(x, y - self.image_height)
                if action == "label":
                    self._refresh()
                elif action == "submit":
                    self.save()
                    print("Отправлено. Переход к следующему изображению.")
                    self.submit_clicked = True
                    return
                elif action in {"auto", "clear"}:
                    self._refresh()
            return

        overlay_start = self.image_width + (self.overlay_gap if self.overlay is not None else 0)
        if self.overlay is not None and x >= overlay_start:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            idx = self._find_annotation_at(x, y)
            ctrl_pressed = bool(flags & cv2.EVENT_FLAG_CTRLKEY)
            if idx is not None and ctrl_pressed:
                self.selected_index = idx
                self.drag_mode = "move"
                self.drag_start = (x, y)
                self.drag_bbox = self.annotations[idx].bbox.copy()
                print(f"Перемещение #{idx}: {self.annotations[idx].label} {self.annotations[idx].bbox}")
                return
            if idx is not None:
                handle = self._hit_resize_handle(self.annotations[idx].bbox, x, y)
                if handle:
                    self.selected_index = idx
                    self.resize_mode = handle
                    self.resize_start = (x, y)
                    self.drag_bbox = self.annotations[idx].bbox.copy()
                    print(f"Режим изменения размера #{idx} ({handle})")
                    return
            self.selected_index = idx if idx is not None else None
            self.drag_mode = None
            self.drag_start = None
            self.drag_bbox = None
            self.resize_mode = None
            self.resize_start = None
            self.start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and self.drag_mode == "move" and self.selected_index is not None and self.drag_start is not None and (flags & cv2.EVENT_FLAG_LBUTTON):
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            x0, y0, w, h = self.drag_bbox
            new_bbox = [
                int(np.clip(x0 + dx, 0, self.image_width - w)),
                int(np.clip(y0 + dy, 0, self.image_height - h)),
                w,
                h,
            ]
            self.annotations[self.selected_index].bbox = new_bbox
            self._refresh()

        elif event == cv2.EVENT_LBUTTONUP and self.drag_mode == "move":
            self.drag_mode = None
            self.drag_start = None
            self.drag_bbox = None
            self._refresh()

        elif event == cv2.EVENT_MOUSEMOVE and self.drag_start is not None and self.selected_index is not None and (flags & cv2.EVENT_FLAG_LBUTTON):
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            x0, y0, w, h = self.drag_bbox
            new_bbox = [
                int(np.clip(x0 + dx, 0, self.image_width - w)),
                int(np.clip(y0 + dy, 0, self.image_height - h)),
                w,
                h,
            ]
            self.annotations[self.selected_index].bbox = new_bbox
            self._refresh()
        elif event == cv2.EVENT_MOUSEMOVE and self.resize_mode and self.selected_index is not None and self.resize_start is not None:
            self._resize_selected(x, y)
            self._refresh()
        elif event == cv2.EVENT_LBUTTONUP and self.drag_start is not None and self.selected_index is not None:
            self.drag_start = None
            self.drag_bbox = None
            self._refresh()
        elif event == cv2.EVENT_LBUTTONUP and self.resize_mode and self.selected_index is not None:
            self.resize_mode = None
            self.resize_start = None
            self.drag_bbox = None
            self._refresh()
        elif event == cv2.EVENT_MOUSEMOVE and self.start_point is not None:
            x_clamped = int(np.clip(x, 0, self.image_width - 1))
            y_clamped = int(np.clip(y, 0, self.image_height - 1))
            temp = self.display_image.copy()
            cv2.rectangle(temp, self.start_point, (x_clamped, y_clamped), (0, 255, 255), 2)
            cv2.imshow(self.window_name, temp)
        elif event == cv2.EVENT_LBUTTONUP and self.start_point is not None:
            x0, y0 = self.start_point
            x1 = int(np.clip(x, 0, self.image_width - 1))
            y1 = int(np.clip(y, 0, self.image_height - 1))
            x_min, x_max = sorted([x0, x1])
            y_min, y_max = sorted([y0, y1])
            w = max(1, x_max - x_min)
            h = max(1, y_max - y_min)
            bbox = [int(x_min), int(y_min), int(w), int(h)]
            ann = Annotation(label=self.current_label, bbox=bbox)
            self.annotations.append(ann)
            if self.current_label == "target_ball":
                self._ensure_single_target()
            print(f"Добавлено: {ann.label} {ann.bbox}")
            self.start_point = None
            self._refresh()

    def _find_annotation_at(self, x: int, y: int) -> Optional[int]:
        for idx in reversed(range(len(self.annotations))):
            ax, ay, aw, ah = self.annotations[idx].bbox
            if ax <= x <= ax + aw and ay <= y <= ay + ah:
                return idx
        return None

    def run_auto_detection(self) -> None:
        print("🔍 Авторазметка через detect_structure...")
        structure = detect_structure(str(self.image_path))
        auto_anns: List[Annotation] = []
        if structure.instruction_area:
            auto_anns.append(Annotation("instruction", list(map(int, structure.instruction_area)), origin="model"))
        if structure.body_area:
            auto_anns.append(Annotation("body", list(map(int, structure.body_area)), origin="model"))
        for region in getattr(structure, "regions", []):
            if region.kind == "grid" and region.cells:
                for cell in region.cells:
                    auto_anns.append(Annotation("tile", list(map(int, cell.bbox)), origin="model"))
        
        # Добавляем ball элементы если есть
        balls = getattr(structure, "balls", None) or []
        for ball in balls:
            auto_anns.append(Annotation("ball", list(map(int, ball.bbox)), origin="model"))
        if auto_anns:
            # удаляем предыдущие модельные
            self.annotations = [ann for ann in self.annotations if ann.origin != "model"] + auto_anns
            self.selected_index = None
            print(f"Добавлено модельных боксов: {len(auto_anns)}")
        else:
            print("⚠️ Модель не нашла тайлы")

    def clear_model_annotations(self) -> None:
        before = len(self.annotations)
        self.annotations = [ann for ann in self.annotations if ann.origin == "manual"]
        self.selected_index = None
        print(f"Удалено модельных боксов: {before - len(self.annotations)}")
        self._refresh()

    def _draw_annotations(self, img):
        for idx, ann in enumerate(self.annotations):
            x, y, w, h = ann.bbox
            color = self._label_color(ann.label)
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            label = ann.label if ann.origin == "manual" else f"{ann.label} ({ann.origin})"
            cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            if idx == self.selected_index:
                self._draw_resize_handles(img, ann.bbox, color)

    def _draw_resize_handles(self, img, bbox: List[int], color):
        x, y, w, h = bbox
        handles = self._get_handles(x, y, w, h)
        for hx, hy in handles.values():
            cv2.circle(img, (hx, hy), 5, color, -1)

    def _get_handles(self, x: int, y: int, w: int, h: int) -> Dict[str, Tuple[int, int]]:
        return {
            "tl": (x, y),
            "tr": (x + w, y),
            "bl": (x, y + h),
            "br": (x + w, y + h),
        }

    def _hit_resize_handle(self, bbox: List[int], x: int, y: int) -> Optional[str]:
        x0, y0, w, h = bbox
        for name, (hx, hy) in self._get_handles(x0, y0, w, h).items():
            if abs(x - hx) <= 8 and abs(y - hy) <= 8:
                return name
        return None

    def _resize_selected(self, x: int, y: int) -> None:
        if self.selected_index is None or self.resize_mode is None or self.drag_bbox is None:
            return
        x0, y0, w, h = self.drag_bbox
        if self.resize_mode == "tl":
            new_x0 = int(np.clip(x, 0, x0 + w - 1))
            new_y0 = int(np.clip(y, 0, y0 + h - 1))
            w = (x0 + w) - new_x0
            h = (y0 + h) - new_y0
            x0, y0 = new_x0, new_y0
        elif self.resize_mode == "tr":
            new_x1 = int(np.clip(x, x0 + 1, self.image_width - 1))
            new_y0 = int(np.clip(y, 0, y0 + h - 1))
            w = new_x1 - x0
            h = (y0 + h) - new_y0
            y0 = new_y0
        elif self.resize_mode == "bl":
            new_x0 = int(np.clip(x, 0, x0 + w - 1))
            new_y1 = int(np.clip(y, y0 + 1, self.image_height - 1))
            w = (x0 + w) - new_x0
            h = new_y1 - y0
            x0 = new_x0
        elif self.resize_mode == "br":
            new_x1 = int(np.clip(x, x0 + 1, self.image_width - 1))
            new_y1 = int(np.clip(y, y0 + 1, self.image_height - 1))
            w = new_x1 - x0
            h = new_y1 - y0
        w = max(1, w)
        h = max(1, h)
        self.annotations[self.selected_index].bbox = [x0, y0, w, h]

    def _label_color(self, label: str):
        palette = {
            "instruction": (255, 149, 0),
            "body": (90, 200, 255),
            "tile": (80, 230, 110),
            "ball": (255, 100, 100),  # Красный цвет для мячика
            "button": (255, 45, 185),
            "other": (255, 214, 10),
        }
        return palette.get(label, (150, 150, 150))

    def _refresh(self) -> None:
        annotated = self.image.copy()
        self._draw_annotations(annotated)

        total_width = self.image_width + (self.overlay_width + self.overlay_gap if self.overlay is not None else 0)
        display_height = self.image_height + self.panel_height
        composed = np.zeros((display_height, total_width, 3), dtype=np.uint8)
        composed[:] = (24, 24, 30)
        composed[: self.image_height, : self.image_width, :] = annotated

        if self.overlay is not None:
            overlay_x = self.image_width + self.overlay_gap
            composed[: self.image_height, overlay_x: overlay_x + self.overlay_width] = self.overlay

        self.display_image = composed
        panel = composed[self.image_height :, :, :]
        panel[:] = (28, 28, 36)
        self._draw_toolbar(panel)

        cv2.imshow(self.window_name, composed)

    def _draw_toolbar(self, panel: np.ndarray) -> None:
        padding = self.padding
        total_width = self.image_width + (self.overlay_width + self.overlay_gap if self.overlay is not None else 0)
        column_width = min(200, (total_width - padding * 2) // 2)
        button_h = self.button_height
        spacing = 8
        x_positions = [padding, padding + column_width + spacing]
        y = padding
        self.toolbar_buttons = []

        actions = [(label, "label") for label in LABEL_LIST]
        actions.extend([
            ("Auto detect", "auto"),
            ("Clear model", "clear"),
            ("Delete selected", "delete_selected"),
        ])
        if self.split_root:
            actions.append((f"Split: {self.current_split or 'none'}", "split_info"))
            actions.append(("Mark train", "set_train"))
            actions.append(("Mark val", "set_val"))

        for i, (label, kind) in enumerate(actions):
            col = i % 2
            row = i // 2
            x0 = x_positions[col]
            y0 = padding + row * (button_h + spacing)
            x1 = x0 + column_width
            y1 = y0 + button_h
            color = self._label_color(label) if kind == "label" else (90, 200, 255)
            if kind == "split_info":
                color = (180, 180, 180)
            active = kind == "label" and LABEL_LIST.index(label) == self.current_index if kind == "label" else False
            cv2.rectangle(panel, (x0, y0), (x1, y1), (38, 38, 48), -1)
            cv2.rectangle(panel, (x0, y0), (x1, y1), color, 2 if not active else 3)
            cv2.putText(panel, label, (x0 + 10, y1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            self.toolbar_buttons.append((x0, y0, x1, y1, kind, label))

        submit_y = padding + ((len(actions) + 1) // 2) * (button_h + spacing)
        submit_x0 = padding
        submit_x1 = submit_x0 + column_width * 2 + spacing
        submit_y1 = submit_y + button_h
        self.submit_button = (submit_x0, submit_y, submit_x1, submit_y1)
        cv2.rectangle(panel, (submit_x0, submit_y), (submit_x1, submit_y1), (80, 220, 120), -1)
        cv2.putText(panel, "Submit", (submit_x0 + 24, submit_y1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (24, 24, 30), 2)

        info_y = submit_y1 + spacing + button_h // 2
        info_text = f"Current: {self.current_label}"
        if self.selected_index is not None:
            info_text += f" | Selected bbox #{self.selected_index}"
        cv2.putText(panel, info_text, (padding, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)

    def _handle_toolbar_click(self, x: int, y: int) -> Optional[str]:
        if self.submit_button and self._point_in_rect(x, y, self.submit_button):
            self.submit_clicked = True
            self.save()
            print("Сохранено (submit)")
            return
        if self.submit_button and self._point_in_rect(x, y, self.submit_button):
            return "submit"
        for idx, (x0, y0, x1, y1, kind, label) in enumerate(self.toolbar_buttons):
            if x0 <= x <= x1 and y0 <= y <= y1:
                if kind == "label":
                    self.current_index = LABEL_LIST.index(label)
                    self.current_label = label
                    print(f"Текущая метка: {self.current_label}")
                elif kind == "auto":
                    self.run_auto_detection()
                elif kind == "clear":
                    self.clear_model_annotations()
                elif kind == "delete_selected":
                    self._delete_selected()
                    return "delete"
                elif kind == "set_train":
                    self._change_split(TRAIN_DIR_NAME)
                elif kind == "set_val":
                    self._change_split(VAL_DIR_NAME)
                return kind if kind != "split_info" else None
        return None

    def save(self) -> None:
        payload = AnnotationFile(
            image=self.image_path.name,
            annotations=self.annotations,
        )
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(asdict(payload), f, ensure_ascii=False, indent=2)

    def _detect_current_split(self) -> Optional[str]:
        assert self.split_root is not None
        try:
            rel = self.image_path.relative_to(self.split_root)
        except ValueError:
            return None
        parts = rel.parts
        if not parts:
            return None
        if parts[0] == TRAIN_DIR_NAME:
            return TRAIN_DIR_NAME
        if parts[0] == VAL_DIR_NAME:
            return VAL_DIR_NAME
        return None

    def _change_split(self, target_split: str) -> None:
        if not self.split_root:
            return
        target_dir = self.split_root / target_split
        target_dir.mkdir(parents=True, exist_ok=True)
        image_target = target_dir / self.image_path.name
        anno_target = target_dir / self.output_path.name
        if image_target == self.image_path:
            return
        print(f"➡️ Перемещение в {target_split}: {self.image_path.name}")
        image_target.parent.mkdir(parents=True, exist_ok=True)
        anno_target.parent.mkdir(parents=True, exist_ok=True)
        if self.image_path.exists():
            shutil.move(str(self.image_path), str(image_target))
        if self.output_path.exists():
            shutil.move(str(self.output_path), str(anno_target))
        self.image_path = image_target
        self.output_path = anno_target
        self.image = cv2.imread(str(self.image_path))
        if self.image is not None:
            self.base = self.image.copy()
        self.current_split = target_split
        self._refresh()

    def _load_overlay(self) -> Optional[np.ndarray]:
        search_paths = [
            self.image_path.with_name(self.image_path.stem + "_overlay.png"),
            self.image_path.with_name(self.image_path.stem + "_gpt_overlay.png"),
            self.image_path.with_name(self.image_path.stem + "_gpt_view_overlay.png"),
        ]
        analysis_dir = Path("analysis")
        if analysis_dir.exists():
            search_paths.extend([
                analysis_dir / f"{self.image_path.stem}_overlay.png",
                analysis_dir / f"{self.image_path.stem}_gpt_overlay.png",
                analysis_dir / f"{self.image_path.stem}_gpt_view_overlay.png",
                analysis_dir / "gpt_view_overlay.png",
            ])
            glob_match = next(analysis_dir.glob(f"**/{self.image_path.stem}*overlay*.png"), None)
            if glob_match:
                search_paths.append(glob_match)
        for cand in search_paths:
            if cand.exists():
                overlay = cv2.imread(str(cand))
                if overlay is not None:
                    return overlay
        return None

    def _ctrl_pressed(self) -> bool:
        return False

    def _override_last_annotation_label(self, new_label: str) -> None:
        if not self.annotations:
            return
        last = self.annotations[-1]
        if last.origin == "manual":
            last.label = new_label
        else:
            self.annotations.append(Annotation(label=new_label, bbox=last.bbox.copy()))

    def mark_last_as_ball(self) -> None:
        self._override_last_annotation_label("ball")

    def mark_last_as_target(self) -> None:
        self._override_last_annotation_label("target_ball")
        self._ensure_single_target()

    def _ensure_single_target(self) -> None:
        target_found = False
        for ann in self.annotations:
            if ann.label == "target_ball":
                if not target_found:
                    target_found = True
                else:
                    ann.label = "ball"

    @staticmethod
    def _point_in_rect(px: int, py: int, rect: tuple[int, int, int, int]) -> bool:
        x0, y0, x1, y1 = rect
        return x0 <= px <= x1 and y0 <= py <= y1

    def _delete_selected(self) -> None:
        if self.selected_index is None:
            if self.annotations:
                removed = self.annotations.pop()
                print(f"Удалено: {removed.label} {removed.bbox}")
        elif 0 <= self.selected_index < len(self.annotations):
            removed = self.annotations.pop(self.selected_index)
            print(f"Удалено: {removed.label} {removed.bbox}")
            self.selected_index = None
        self._refresh()


def iterate_images(dataset_dir: Path, pattern: str) -> List[Path]:
    return sorted(dataset_dir.glob(pattern))


def main() -> None:
    parser = argparse.ArgumentParser(description="Интерактивная разметка структуры скринов")
    parser.add_argument("--dataset", default="dataset/screens", help="Папка со скринами")
    parser.add_argument("--pattern", default="*.png", help="Шаблон выбора файлов")
    parser.add_argument("--output-suffix", default="_structure.json", help="Суффикс файла аннотаций")
    parser.add_argument("--overwrite", action="store_true", help="Переписывать существующие аннотации")
    parser.add_argument("--start", type=int, default=0, help="Индекс, с которого начать")
    parser.add_argument("--split-root", help="Корневая папка со split-подпапками train/val для раскладывания файлов")
    parser.add_argument("--only-with", nargs="*", help="Отбирать только изображения, где уже размечены указанные классы (по существующим annotation-файлам)")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    split_root = Path(args.split_root) if args.split_root else None
    images = iterate_images(dataset_dir, args.pattern)
    if not images:
        print("❌ Файлы не найдены")
        return

    filtered_images = images[args.start:]

    if args.only_with:
        filtered = []
        required = set(args.only_with)
        for image_path in filtered_images:
            ann_path = image_path.with_suffix("")
            ann_path = ann_path.with_name(ann_path.name + args.output_suffix)
            if not ann_path.exists():
                continue
            try:
                data = json.loads(ann_path.read_text(encoding="utf-8"))
                labels = {item.get("label") for item in data.get("annotations", [])}
                if required.issubset(labels):
                    filtered.append(image_path)
            except Exception:
                continue
        filtered_images = filtered

    if not filtered_images:
        print("❌ Нет изображений, удовлетворяющих фильтру")
        return

    for idx, image_path in enumerate(filtered_images, start=args.start):
        output_path = image_path.with_suffix("")
        output_path = output_path.with_name(output_path.name + args.output_suffix)

        if output_path.exists() and not args.overwrite:
            print(f"Пропуск (есть аннотация): {image_path.name}")
            continue

        print(f"\n[{idx+1}/{len(images)}] Разметка {image_path.name}")
        session = AnnotationSession(image_path, output_path, split_root=split_root)
        result = session.run()
        if result == "exit":
            print("Выход по запросу пользователя")
            break
        if result == "skip":
            print("Пропущено")
            continue
        print("Готово")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

