#!/usr/bin/env python3
"""
Умный детектор объектов для капч.
Использует CLIP для понимания содержимого ячеек по текстовым описаниям.
"""

import torch
from PIL import Image
import numpy as np
from pathlib import Path


class SmartDetector:
    """Умный детектор объектов с использованием CLIP"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.model_loaded = False
        
        print(f"🤖 Инициализация умного детектора на {self.device}")
        
    def load_clip_model(self):
        """Загружает CLIP модель для анализа изображений"""
        try:
            print("📦 Загрузка CLIP модели...")
            
            # Пробуем разные варианты CLIP
            try:
                # OpenCLIP (предпочтительно)
                import open_clip
                
                model_name = "ViT-B-32"
                pretrained = "openai"
                
                self.model, _, self.processor = open_clip.create_model_and_transforms(
                    model_name, pretrained=pretrained, device=self.device
                )
                self.tokenizer = open_clip.get_tokenizer(model_name)
                
                print(f"✅ OpenCLIP загружен: {model_name}")
                self.model_type = "openclip"
                
            except ImportError:
                # Fallback к стандартному CLIP через transformers
                from transformers import CLIPProcessor, CLIPModel
                
                model_name = "openai/clip-vit-base-patch32"
                self.model = CLIPModel.from_pretrained(model_name).to(self.device)
                self.processor = CLIPProcessor.from_pretrained(model_name)
                
                print(f"✅ Transformers CLIP загружен: {model_name}")
                self.model_type = "transformers"
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки CLIP: {e}")
            return False
    
    def analyze_cell_with_clip(self, cell_image, instruction):
        """Анализирует ячейку с помощью CLIP"""
        if not self.model_loaded:
            print("❌ CLIP модель не загружена!")
            return 0.0, "модель не загружена"
        
        try:
            # Создаем список возможных объектов на основе инструкции
            possible_objects = self._extract_target_objects(instruction)
            
            if not possible_objects:
                return 0.0, "не удалось определить целевые объекты"
            
            # Анализируем каждый возможный объект
            best_score = 0.0
            best_object = ""
            
            for obj in possible_objects:
                score = self._calculate_clip_score(cell_image, obj)
                if score > best_score:
                    best_score = score
                    best_object = obj
            
            return best_score, best_object
            
        except Exception as e:
            print(f"❌ Ошибка CLIP анализа: {e}")
            return 0.0, f"ошибка: {e}"
    
    def _extract_target_objects(self, instruction):
        """Извлекает целевые объекты из инструкции"""
        instruction_lower = instruction.lower()
        
        # Словарь ключевых слов и соответствующих объектов
        object_mapping = {
            # Мебель для сидения
            "сидеть": ["chair", "sofa", "bench", "stool", "armchair"],
            "стул": ["chair", "stool", "seat"],
            "кресло": ["armchair", "chair", "recliner"],
            
            # Транспорт
            "автомобиль": ["car", "vehicle", "automobile", "truck"],
            "машин": ["car", "vehicle", "automobile"],
            "транспорт": ["vehicle", "car", "truck", "bus"],
            
            # Природа и лес
            "лес": ["forest", "trees", "woods"],
            "дерев": ["tree", "trees", "forest"],
            "растени": ["plant", "vegetation", "flora"],
            
            # Вода и океан
            "океан": ["ocean", "sea", "water", "waves"],
            "море": ["sea", "ocean", "water"],
            "вода": ["water", "ocean", "sea", "river"],
            
            # Предметы для подвешивания
            "повесить": ["painting", "picture", "frame", "mirror", "lamp", "clock"],
            "картин": ["painting", "picture", "artwork", "frame"],
            "зеркал": ["mirror", "reflection"],
            
            # Еда
            "еда": ["food", "meal", "dish"],
            "фрукт": ["fruit", "apple", "banana", "orange"],
            
            # Животные
            "животн": ["animal", "pet", "dog", "cat", "bird"],
            "собак": ["dog", "puppy"],
            "кот": ["cat", "kitten"],
        }
        
        # Ищем совпадения
        target_objects = []
        for keyword, objects in object_mapping.items():
            if keyword in instruction_lower:
                target_objects.extend(objects)
        
        # Если не нашли специфичные объекты, пробуем общий анализ
        if not target_objects:
            # Извлекаем ключевые слова из инструкции
            words = instruction_lower.split()
            for word in words:
                if len(word) > 4:  # Только значимые слова
                    target_objects.append(word)
        
        # Убираем дубликаты и оставляем уникальные
        return list(set(target_objects))
    
    def _calculate_clip_score(self, image, object_description):
        """Вычисляет score совпадения изображения с описанием объекта"""
        try:
            if self.model_type == "openclip":
                # OpenCLIP подход
                image_tensor = self.processor(image).unsqueeze(0).to(self.device)
                text_tokens = self.tokenizer([f"a photo of {object_description}"]).to(self.device)
                
                with torch.no_grad():
                    image_features = self.model.encode_image(image_tensor)
                    text_features = self.model.encode_text(text_tokens)
                    
                    # Нормализуем и вычисляем similarity
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                    
                    similarity = torch.mm(image_features, text_features.t())
                    score = similarity.item()
            
            else:
                # Transformers CLIP подход
                inputs = self.processor(
                    text=[f"a photo of {object_description}"],
                    images=image,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits_per_image = outputs.logits_per_image
                    probs = logits_per_image.softmax(dim=1)
                    score = probs[0][0].item()
            
            return score
            
        except Exception as e:
            print(f"❌ Ошибка расчета CLIP score для '{object_description}': {e}")
            return 0.0
    
    def analyze_all_cells(self, cells_dir, instruction, threshold=0.3):
        """Анализирует все ячейки и возвращает подходящие"""
        if not self.load_clip_model():
            return []
        
        cells_path = Path(cells_dir)
        if not cells_path.exists():
            print(f"❌ Папка с ячейками не найдена: {cells_dir}")
            return []
        
        # Находим все файлы ячеек
        cell_files = sorted(list(cells_path.glob("cell_*.png")))
        
        if not cell_files:
            print("❌ Файлы ячеек не найдены")
            return []
        
        print(f"🔍 Анализируем {len(cell_files)} ячеек с помощью CLIP...")
        print(f"📋 Инструкция: '{instruction}'")
        print(f"⚡ Порог уверенности: {threshold}")
        
        matching_cells = []
        
        for cell_file in cell_files:
            try:
                # Извлекаем номер ячейки из имени файла
                cell_index = int(cell_file.stem.replace("cell_", ""))
                
                # Загружаем изображение ячейки
                cell_image = Image.open(cell_file)
                
                # Анализируем с помощью CLIP
                score, best_object = self.analyze_cell_with_clip(cell_image, instruction)
                
                print(f"   Ячейка {cell_index}: {score:.3f} ({best_object})")
                
                # Если score выше порога - ячейка подходит
                if score > threshold:
                    matching_cells.append({
                        "index": cell_index,
                        "score": score,
                        "object": best_object,
                        "file": str(cell_file)
                    })
                    print(f"   ✅ Ячейка {cell_index} подходит: {best_object} ({score:.3f})")
                
            except Exception as e:
                print(f"❌ Ошибка анализа {cell_file}: {e}")
                continue
        
        print(f"\n🎯 Найдено {len(matching_cells)} подходящих ячеек")
        
        # Сортируем по убыванию score
        matching_cells.sort(key=lambda x: x["score"], reverse=True)
        
        return matching_cells


def test_smart_detection(cells_dir="analysis/cells", instruction="Выберите то, на чём можно сидеть"):
    """Тестирует умную детекцию"""
    detector = SmartDetector()
    
    results = detector.analyze_all_cells(cells_dir, instruction)
    
    print("\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("="*40)
    
    if results:
        for result in results:
            print(f"Ячейка {result['index']}: {result['object']} (score: {result['score']:.3f})")
        
        print(f"\n🎯 РЕКОМЕНДАЦИЯ: Кликнуть на ячейки {[r['index'] for r in results]}")
    else:
        print("❌ Подходящих ячеек не найдено")
        print("🎯 РЕКОМЕНДАЦИЯ: Нажать 'Пропустить'")
    
    return results


if __name__ == "__main__":
    print("🧠 Тестирование умного детектора объектов")
    print("="*50)
    
    test_smart_detection()
