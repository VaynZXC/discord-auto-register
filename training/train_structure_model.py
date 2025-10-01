#!/usr/bin/env python3
"""Пример обучения детектора структуры на основе созданного датасета."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import List, Dict

import torch
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from PIL import Image
import yaml
from tqdm import tqdm


class StructureDataset(Dataset):
    def __init__(self, records: List[Dict], transform=None):
        self.records = records
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        rec = self.records[idx]
        image = Image.open(rec["image"]).convert("RGB")
        boxes = torch.tensor([ann["bbox"] for ann in rec["annotations"]], dtype=torch.float32)
        labels = torch.tensor([ann["category_id"] for ann in rec["annotations"]], dtype=torch.int64)
        target = {"boxes": boxes, "labels": labels}
        if self.transform:
            image = self.transform(image)
        return image, target


def load_dataset(dataset_path: Path, categories: List[str]) -> List[Dict]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    cat_to_id = {cat: i + 1 for i, cat in enumerate(categories)}

    def _convert(records_raw):
        converted = []
        for rec in records_raw:
            anns = []
            for ann in rec["annotations"]:
                cat_id = cat_to_id.get(ann["category"])
                bbox = ann.get("bbox")
                if cat_id is None or not bbox:
                    continue
                x, y, w, h = bbox
                if w <= 0 or h <= 0:
                    continue
                anns.append({
                    "bbox": [x, y, x + w, y + h],
                    "category_id": cat_id,
                })
            if not anns:
                continue
            converted.append({"image": rec["image"], "annotations": anns})
        return converted

    if isinstance(data, dict):
        train_records = _convert(data.get("train", []))
        val_records = _convert(data.get("val", [])) if data.get("val") else []
        return train_records, val_records

    # старый формат
    return _convert(data), []


def _sum_losses(loss_obj):
    if isinstance(loss_obj, dict):
        return sum(_sum_losses(v) for v in loss_obj.values())
    if isinstance(loss_obj, (list, tuple)):
        return sum(_sum_losses(v) for v in loss_obj)
    if hasattr(loss_obj, "float"):
        return loss_obj.float().mean()
    return torch.tensor(float(loss_obj))


def train(config_path: Path) -> None:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset_path = Path(cfg["dataset"]["path"])
    categories = cfg["dataset"]["categories"]

    load_result = load_dataset(dataset_path, categories)
    if isinstance(load_result, tuple):
        train_records, val_records = load_result
    else:
        train_records, val_records = load_result, []
    transform = transforms.Compose([transforms.ToTensor()])
    train_dataset = StructureDataset(train_records, transform=transform)
    if val_records:
        val_dataset = StructureDataset(val_records, transform=transform)
    else:
        val_dataset = None

    def collate_fn(batch):
        images, targets = zip(*batch)
        return list(images), list(targets)

    train_loader = DataLoader(train_dataset, batch_size=cfg["train"]["batch_size"], shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, collate_fn=collate_fn) if val_dataset else None

    num_classes = len(categories) + 1
    model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=cfg["train"]["lr"])

    for epoch in range(cfg["train"]["epochs"]):
        model.train()
        running_loss = 0.0
        
        # Прогресс-бар для батчей в эпохе
        pbar = tqdm(train_loader, desc=f"Эпоха {epoch+1}/{cfg['train']['epochs']}", unit="batch")
        
        for images, targets in pbar:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            optimizer.zero_grad()
            loss_obj = model(images, targets)
            losses = _sum_losses(loss_obj)
            losses.backward()
            optimizer.step()
            running_loss += losses.item()
            
            # Обновляем прогресс-бар
            pbar.set_postfix({'loss': f'{losses.item():.4f}'})
        
        avg_loss = running_loss / max(1, len(train_loader))

        if val_loader:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for images, targets in val_loader:
                    images = [img.to(device) for img in images]
                    targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                    loss_obj = model(images, targets)
                    losses = _sum_losses(loss_obj)
                    val_loss += losses.item()
            val_loss /= max(1, len(val_loader))
            print(f"\n✅ Эпоха {epoch+1}/{cfg['train']['epochs']} | Train loss: {avg_loss:.4f} | Val loss: {val_loss:.4f}")
        else:
            print(f"\n✅ Эпоха {epoch+1}/{cfg['train']['epochs']} | Train loss: {avg_loss:.4f}")

    save_path = Path("training/structure_model.pth")
    torch.save(model.state_dict(), save_path)
    print(f"✅ Model saved to {save_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучить модель структуры")
    parser.add_argument("--config", default="training/model_config.yaml")
    args = parser.parse_args()
    train(Path(args.config))


if __name__ == "__main__":
    main()

