"""Структурный анализ hCaptcha с поддержкой обученной модели и fall-back к OpenCV."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import yaml
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.ops import nms


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class GridCell:
    id: int
    bbox: Tuple[int, int, int, int]
    center: Tuple[float, float]
    score: Optional[float] = None


@dataclass
class Region:
    kind: str
    bbox: Tuple[int, int, int, int]
    centers: List[Tuple[float, float]]
    cells: Optional[List[GridCell]] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class StructureInfo:
    image_size: Tuple[int, int]
    instruction_area: Optional[Tuple[int, int, int, int]]
    body_area: Optional[Tuple[int, int, int, int]]
    regions: List[Region]
    balls: Optional[List[GridCell]] = None  # Все найденные мячи
    target_balls: Optional[List[GridCell]] = None  # Правильные мячи


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

_MODEL: Optional[torch.nn.Module] = None
_DEVICE: Optional[torch.device] = None
_CATEGORIES: Optional[List[str]] = None


def _get_categories() -> List[str]:
    global _CATEGORIES
    if _CATEGORIES is None:
        cfg_path = Path("training/model_config.yaml")
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        _CATEGORIES = list(data["dataset"]["categories"])
    return _CATEGORIES


def _load_model() -> torch.nn.Module:
    global _MODEL, _DEVICE
    if _MODEL is not None:
        return _MODEL

    categories = _get_categories()
    num_classes = len(categories) + 1

    model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    state_path = Path("training/structure_model.pth")
    if not state_path.exists():
        raise FileNotFoundError("Не найден файл весов training/structure_model.pth")

    state_dict = torch.load(state_path, map_location="cpu")
    model.load_state_dict(state_dict)

    _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(_DEVICE)
    model.eval()
    _MODEL = model
    return model


# ---------------------------------------------------------------------------
# OpenCV fallback implementation
# ---------------------------------------------------------------------------


def _find_instruction_area(gray: np.ndarray) -> Tuple[int, int, int, int]:
    h, w = gray.shape
    top_crop = int(h * 0.35)
    upper = gray[:top_crop]
    proj = upper.mean(axis=1)
    threshold = proj.mean()
    candidate_rows = np.where(proj < threshold * 0.97)[0]
    if len(candidate_rows) == 0:
        return (0, 0, w, int(0.2 * h))
    bottom = int(candidate_rows[-1])
    bottom = min(bottom + 10, top_crop)
    return (0, 0, w, bottom)


def _detect_grid_region(binary: np.ndarray, min_area: int = 8000) -> Optional[Region]:
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    rects: List[Tuple[int, int, int, int]] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < min_area:
            continue
        rects.append((x, y, w, h))

    if len(rects) < 4:
        return None

    rects.sort(key=lambda r: (r[1], r[0]))
    median_h = np.median([r[3] for r in rects])
    row_thresh = median_h * 0.7

    rows: List[List[Tuple[int, int, int, int]]] = []
    for rect in rects:
        x, y, w, h = rect
        placed = False
        for row in rows:
            if abs(row[0][1] - y) < row_thresh:
                row.append(rect)
                placed = True
                break
        if not placed:
            rows.append([rect])

    if len(rows) < 2:
        return None

    rows = [sorted(row, key=lambda r: r[0]) for row in rows]

    rows_limited = rows[:3]

    grid_x0 = min(r[0] for row in rows_limited for r in row)
    grid_y0 = min(r[1] for row in rows_limited for r in row)
    grid_x1 = max(r[0] + r[2] for row in rows_limited for r in row)
    grid_y1 = max(r[1] + r[3] for row in rows_limited for r in row)

    centers: List[Tuple[float, float]] = []
    cells: List[GridCell] = []
    cell_id = 0
    for row in rows_limited:
        for rect in row[:3]:
            x, y, w, h = rect
            cx = x + w / 2.0
            cy = y + h / 2.0
            centers.append((cx, cy))
            cells.append(GridCell(id=cell_id, bbox=rect, center=(cx, cy)))
            cell_id += 1

    if len(cells) < 3:
        return None

    grid_bbox = (
        grid_x0,
        grid_y0,
        max(1, grid_x1 - grid_x0),
        max(1, grid_y1 - grid_y0),
    )
    cols_est = max(len(row) for row in rows_limited)
    return Region(
        kind="tile",
        bbox=grid_bbox,
        centers=centers,
        cells=cells,
        meta={"source": "opencv", "rows": len(rows_limited), "cols": cols_est},
    )


def _detect_structure_opencv(img: np.ndarray) -> StructureInfo:
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    instruction = _find_instruction_area(blur)
    body_area = _compute_body_area(instruction, w, h)

    body_y = body_area[1]
    body = blur[body_y:]

    edges = cv2.Canny(body, 30, 120)
    dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)

    grid_region = _detect_grid_region(dilated)
    regions: List[Region] = []
    if grid_region:
        cells_clipped = _clip_cells_to_body([
            GridCell(
                id=c.id,
                bbox=(c.bbox[0], c.bbox[1] + body_y, c.bbox[2], c.bbox[3]),
                center=(c.center[0], c.center[1] + body_y),
                score=c.score,
            )
            for c in (grid_region.cells or [])
        ], body_area)
        if cells_clipped:
            cells_clipped = _sort_cells_in_grid(cells_clipped)
            bbox = _enclosing_bbox_from_cells(cells_clipped) or body_area
            regions.append(Region(
                kind="tile",
                bbox=bbox,
                centers=[cell.center for cell in cells_clipped],
                cells=cells_clipped,
                meta={"source": "opencv", **(grid_region.meta or {})},
            ))

    return StructureInfo(
        image_size=(w, h),
        instruction_area=instruction,
        body_area=body_area,
        regions=regions,
        balls=None,  # OpenCV fallback пока не поддерживает ball детекцию
    )


# ---------------------------------------------------------------------------
# Model inference
# ---------------------------------------------------------------------------


def _detect_structure_model(img: np.ndarray) -> StructureInfo:
    model = _load_model()
    device = _DEVICE or torch.device("cpu")

    transform = transforms.ToTensor()
    tensor_img = transform(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).to(device)

    with torch.no_grad():
        outputs = model([tensor_img])

    output = outputs[0]
    boxes = output.get("boxes", torch.empty((0, 4))).cpu().numpy()
    labels = output.get("labels", torch.empty((0,), dtype=torch.long)).cpu().numpy()
    scores = output.get("scores", torch.empty((0,))).cpu().numpy()

    id_to_label = {idx + 1: name for idx, name in enumerate(_get_categories())}

    instruction = None
    body_area = None
    grid_cells: List[GridCell] = []

    tile_boxes_xyxy: List[Tuple[float, float, float, float]] = []
    tile_scores: List[float] = []
    ball_boxes_xyxy: List[Tuple[float, float, float, float]] = []
    ball_scores: List[float] = []
    target_ball_boxes_xyxy: List[Tuple[float, float, float, float]] = []
    target_ball_scores: List[float] = []

    for bbox, label_idx, score in zip(boxes, labels, scores):
        label = id_to_label.get(int(label_idx))
        if label not in {"instruction", "body", "tile", "ball", "target_ball"}:
            continue
        if score < 0.3:
            continue
        x1, y1, x2, y2 = bbox
        w_box = max(1, int(x2 - x1))
        h_box = max(1, int(y2 - y1))
        bbox_xywh = (int(x1), int(y1), w_box, h_box)

        if label == "instruction" and instruction is None:
            instruction = bbox_xywh
        elif label == "body" and body_area is None:
            body_area = bbox_xywh
        elif label == "tile":
            tile_boxes_xyxy.append((float(x1), float(y1), float(x2), float(y2)))
            tile_scores.append(float(score))
        elif label == "ball":
            ball_boxes_xyxy.append((float(x1), float(y1), float(x2), float(y2)))
            ball_scores.append(float(score))
        elif label == "target_ball":
            target_ball_boxes_xyxy.append((float(x1), float(y1), float(x2), float(y2)))
            target_ball_scores.append(float(score))

    img_h, img_w = img.shape[0], img.shape[1]
    if body_area is None:
        body_area = _compute_body_area(instruction, img_w, img_h)

    if tile_boxes_xyxy:
        boxes_tensor = torch.tensor(tile_boxes_xyxy, dtype=torch.float32)
        scores_tensor = torch.tensor(tile_scores, dtype=torch.float32)
        keep_idx = nms(boxes_tensor, scores_tensor, iou_threshold=0.4)
        filtered = [(tile_boxes_xyxy[i], tile_scores[i]) for i in keep_idx.tolist()]
        filtered.sort(key=lambda item: item[1], reverse=True)

        rows_est, cols_est = _estimate_grid_shape_xyxy([item[0] for item in filtered])
        if rows_est <= 3 and cols_est <= 3 and len(filtered) > 9:
            filtered = filtered[:9]

        tmp_cells: List[GridCell] = []
        for idx, (box_xyxy, score_val) in enumerate(filtered):
            x1, y1, x2, y2 = box_xyxy
            w_box = max(1, int(x2 - x1))
            h_box = max(1, int(y2 - y1))
            bbox_xywh = (int(x1), int(y1), w_box, h_box)
            center = (int(x1) + w_box / 2, int(y1) + h_box / 2)
            tmp_cells.append(GridCell(id=idx + 1, bbox=bbox_xywh, center=center, score=score_val))

        grid_cells = _clip_cells_to_body(tmp_cells, body_area)
        grid_cells = _sort_cells_in_grid(grid_cells)
        rows_est, cols_est = _estimate_grid_shape_xyxy([
            (
                cell.bbox[0],
                cell.bbox[1],
                cell.bbox[0] + cell.bbox[2],
                cell.bbox[1] + cell.bbox[3],
            )
            for cell in grid_cells
        ])
    else:
        rows_est = cols_est = 0

    regions: List[Region] = []
    if grid_cells:
        regions.append(Region(
            kind="tile",
            bbox=_enclosing_bbox_from_cells(grid_cells) or body_area,
            centers=[cell.center for cell in grid_cells],
            cells=grid_cells,
            meta={"source": "model", "rows": rows_est, "cols": cols_est},
        ))

    # Обработка ball элементов
    ball_cells: List[GridCell] = []
    if ball_boxes_xyxy:
        balls_tensor = torch.tensor(ball_boxes_xyxy, dtype=torch.float32)
        balls_scores_tensor = torch.tensor(ball_scores, dtype=torch.float32)
        keep_idx_balls = nms(balls_tensor, balls_scores_tensor, iou_threshold=0.4)
        filtered_balls = [(ball_boxes_xyxy[i], ball_scores[i]) for i in keep_idx_balls.tolist()]
        filtered_balls.sort(key=lambda item: ((item[0][1] + item[0][3]) / 2, (item[0][0] + item[0][2]) / 2))
        
        for idx, (box_xyxy, score_val) in enumerate(filtered_balls, start=1):
            x1, y1, x2, y2 = box_xyxy
            w_box = max(1, int(x2 - x1))
            h_box = max(1, int(y2 - y1))
            bbox_xywh = (int(x1), int(y1), w_box, h_box)
            center = (int(x1) + w_box / 2, int(y1) + h_box / 2)
            ball_cells.append(GridCell(id=idx, bbox=bbox_xywh, center=center, score=score_val))

    target_ball_cells: List[GridCell] = []
    if target_ball_boxes_xyxy:
        target_tensor = torch.tensor(target_ball_boxes_xyxy, dtype=torch.float32)
        target_scores_tensor = torch.tensor(target_ball_scores, dtype=torch.float32)
        keep_idx_target = nms(target_tensor, target_scores_tensor, iou_threshold=0.4)
        filtered_target = [(target_ball_boxes_xyxy[i], target_ball_scores[i]) for i in keep_idx_target.tolist()]
        filtered_target.sort(key=lambda item: ((item[0][1] + item[0][3]) / 2, (item[0][0] + item[0][2]) / 2))

        for idx, (box_xyxy, score_val) in enumerate(filtered_target, start=1):
            x1, y1, x2, y2 = box_xyxy
            w_box = max(1, int(x2 - x1))
            h_box = max(1, int(y2 - y1))
            bbox_xywh = (int(x1), int(y1), w_box, h_box)
            center = (int(x1) + w_box / 2, int(y1) + h_box / 2)
            target_ball_cells.append(GridCell(id=idx, bbox=bbox_xywh, center=center, score=score_val))

    return StructureInfo(
        image_size=(img.shape[1], img.shape[0]),
        instruction_area=instruction,
        body_area=body_area,
        regions=regions,
        balls=ball_cells if ball_cells else None,
        target_balls=target_ball_cells if target_ball_cells else None,
    )


def _ensure_structure_defaults(structure: StructureInfo, w: int, h: int) -> StructureInfo:
    instruction = structure.instruction_area or (0, 0, w, int(0.2 * h))
    body_area = structure.body_area or (0, int(0.2 * h), w, h - int(0.2 * h))

    regions = list(structure.regions)
    has_grid = any(region.kind in {"grid", "tile"} for region in regions)

    if not has_grid:
        cells: List[GridCell] = []
        x, y, width, height = body_area
        cell_w = width / 3
        cell_h = height / 3
        idx = 1
        for row in range(3):
            for col in range(3):
                cx = int(x + col * cell_w)
                cy = int(y + row * cell_h)
                bbox = (cx, cy, int(cell_w), int(cell_h))
                center = (cx + cell_w / 2, cy + cell_h / 2)
                cells.append(GridCell(id=idx, bbox=bbox, center=center))
                idx += 1
        regions.append(Region(
            kind="tile",
            bbox=body_area,
            centers=[cell.center for cell in cells],
            cells=cells,
            meta={"source": "fallback", "rows": 3, "cols": 3},
        ))
    else:
        # убедимся, что id упорядочены слева-направо, сверху-вниз
        for region in regions:
            if region.kind == "tile" and region.cells:
                region.cells = _sort_cells_in_grid(region.cells)

    return StructureInfo(
        image_size=(w, h),
        instruction_area=instruction,
        body_area=body_area,
        regions=regions,
        balls=structure.balls,  # сохраняем найденные мячи (если были)
        target_balls=structure.target_balls,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_structure(image_path: str, debug_dir: str = "analysis") -> StructureInfo:
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)

    h, w = img.shape[:2]

    try:
        structure = _detect_structure_model(img)
    except Exception as err:
        print(f"⚠️ Ошибка модельного детектора: {err}. Используем OpenCV fallback")
        structure = _detect_structure_opencv(img)

    structure = _ensure_structure_defaults(structure, w, h)

    if debug_dir:
        Path(debug_dir).mkdir(parents=True, exist_ok=True)
        debug_path = Path(debug_dir) / "structure_debug.json"
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(asdict(structure), f, ensure_ascii=False, indent=2)

    return structure


def _estimate_grid_shape_xyxy(boxes: List[Tuple[float, float, float, float]]) -> Tuple[int, int]:
    if not boxes:
        return 0, 0
    heights = [box[3] - box[1] for box in boxes]
    avg_height = float(np.mean(heights)) if heights else 1.0
    row_thresh = max(avg_height * 0.6, 6.0)

    rows: List[List[Tuple[float, float]]] = []
    for box in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
        cy = (box[1] + box[3]) / 2
        cx = (box[0] + box[2]) / 2
        placed = False
        for group in rows:
            if abs(group[0][0] - cy) <= row_thresh:
                group.append((cy, cx))
                placed = True
                break
        if not placed:
            rows.append([(cy, cx)])

    row_count = len(rows)
    col_count = max((len(group) for group in rows), default=0)
    return row_count, col_count


def _enclosing_bbox_from_cells(cells: List[GridCell]) -> Optional[Tuple[int, int, int, int]]:
    if not cells:
        return None
    xs = [cell.bbox[0] for cell in cells]
    ys = [cell.bbox[1] for cell in cells]
    xe = [cell.bbox[0] + cell.bbox[2] for cell in cells]
    ye = [cell.bbox[1] + cell.bbox[3] for cell in cells]
    return (min(xs), min(ys), max(xe) - min(xs), max(ye) - min(ys))


def _compute_body_area(
    instruction: Optional[Tuple[int, int, int, int]],
    img_width: int,
    img_height: int,
) -> Tuple[int, int, int, int]:
    if instruction:
        _, instr_y, _, instr_h = instruction
        top = int(np.clip(instr_y + instr_h, 0, img_height))
    else:
        top = int(0.2 * img_height)
    height = max(1, img_height - top)
    return (0, top, img_width, height)


def _sort_cells_in_grid(cells: List[GridCell]) -> List[GridCell]:
    if not cells:
        return []
    median_height = float(np.median([cell.bbox[3] for cell in cells])) or 1.0
    row_thresh = max(median_height * 0.6, 5.0)
    sorted_by_y = sorted(cells, key=lambda cell: cell.center[1])
    rows: List[List[GridCell]] = []
    for cell in sorted_by_y:
        placed = False
        for row in rows:
            if abs(row[0].center[1] - cell.center[1]) <= row_thresh:
                row.append(cell)
                placed = True
                break
        if not placed:
            rows.append([cell])
    rows.sort(key=lambda r: r[0].center[1])
    ordered: List[GridCell] = []
    cell_id = 1
    for row in rows:
        row.sort(key=lambda cell: cell.center[0])
        for cell in row:
            cell.id = cell_id
            ordered.append(cell)
            cell_id += 1
    return ordered


def _clip_cells_to_body(
    cells: List[GridCell],
    body: Tuple[int, int, int, int],
) -> List[GridCell]:
    body_x, body_y, body_w, body_h = body
    body_x2 = body_x + body_w
    body_y2 = body_y + body_h
    clipped: List[GridCell] = []
    for cell in cells:
        x, y, w, h = cell.bbox
        x2 = x + w
        y2 = y + h
        nx1 = max(body_x, x)
        ny1 = max(body_y, y)
        nx2 = min(body_x2, x2)
        ny2 = min(body_y2, y2)
        if nx2 <= nx1 or ny2 <= ny1:
            continue
        nw = nx2 - nx1
        nh = ny2 - ny1
        center = (nx1 + nw / 2.0, ny1 + nh / 2.0)
        clipped.append(
            GridCell(
                id=cell.id,
                bbox=(int(nx1), int(ny1), int(nw), int(nh)),
                center=center,
                score=cell.score,
            )
        )
    return clipped


