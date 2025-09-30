#!/usr/bin/env python3
"""
Семантический компаратор для поиска отличий между областями капчи.
Использует CLIP для понимания содержимого и поиска "выбивающихся" элементов.
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path
from .smart_detector import SmartDetector


class SemanticComparator:
    """Семантический анализатор для сравнения областей"""
    
    def __init__(self):
        self.detector = SmartDetector()
        self.similarity_threshold = 0.7
        
    def analyze_regions(self, region_images, instruction):
        """Анализирует все регионы и находит решение"""
        if not region_images:
            return []
        
        print(f"🧠 Семантический анализ {len(region_images)} регионов")
        print(f"📋 Инструкция: '{instruction}'")
        
        # Загружаем CLIP модель
        if not self.detector.load_clip_model():
            print("❌ Не удалось загрузить CLIP модель")
            return []
        
        # Определяем стратегию анализа по инструкции
        strategy = self._determine_strategy(instruction)
        print(f"🎯 Стратегия: {strategy}")
        
        if strategy == "find_different":
            return self._find_different_regions(region_images, instruction)
        elif strategy == "find_similar":
            return self._find_similar_regions(region_images, instruction)
        elif strategy == "find_specific":
            return self._find_specific_objects(region_images, instruction)
        else:
            print("⚠️ Неизвестная стратегия, используем поиск специфичных объектов")
            return self._find_specific_objects(region_images, instruction)
    
    def _determine_strategy(self, instruction):
        """Определяет стратегию анализа по инструкции"""
        instruction_lower = instruction.lower()
        
        # Поиск отличающихся элементов
        if any(word in instruction_lower for word in [
            "не принадлежит", "отличается", "выбивается", "другой", "отличающ",
            "different", "not belong", "odd one", "doesn't belong"
        ]):
            return "find_different"
        
        # Поиск похожих элементов
        elif any(word in instruction_lower for word in [
            "похожий", "схожий", "одинаков", "такой же", "соответств",
            "similar", "same", "matching", "like"
        ]):
            return "find_similar"
        
        # Поиск специфичных объектов
        elif any(word in instruction_lower for word in [
            "выберите", "найдите", "покажите", "укажите",
            "select", "choose", "find", "pick"
        ]):
            return "find_specific"
        
        return "find_specific"  # По умолчанию
    
    def _find_different_regions(self, region_images, instruction):
        """Находит регион, который отличается от других"""
        print("🔍 Ищем отличающийся элемент...")
        
        # Анализируем содержимое каждого региона
        region_analysis = []
        
        for region_data in region_images:
            region_image = region_data["image"]
            region_index = region_data["index"]
            
            # Получаем семантическое описание
            score, detected_object = self.detector.analyze_cell_with_clip(region_image, instruction)
            
            region_analysis.append({
                "index": region_index,
                "object": detected_object,
                "score": score,
                "center": region_data["center"],
                "bbox": region_data["bbox"]
            })
            
            print(f"   Регион {region_index}: {detected_object} (score: {score:.3f})")
        
        # Группируем по типам объектов
        object_groups = {}
        for analysis in region_analysis:
            obj_type = analysis["object"]
            if obj_type not in object_groups:
                object_groups[obj_type] = []
            object_groups[obj_type].append(analysis)
        
        print(f"\n📊 Группировка объектов:")
        for obj_type, regions in object_groups.items():
            print(f"   {obj_type}: {len(regions)} регионов")
        
        # Находим "выбивающийся" объект (который в меньшинстве)
        minority_objects = []
        
        for obj_type, regions in object_groups.items():
            if len(regions) == 1:  # Единственный в своем роде
                minority_objects.extend(regions)
                print(f"✅ Найден уникальный объект: {obj_type}")
        
        # Если нет уникальных, ищем наименьшую группу
        if not minority_objects:
            min_group_size = min(len(regions) for regions in object_groups.values())
            for obj_type, regions in object_groups.items():
                if len(regions) == min_group_size:
                    minority_objects.extend(regions)
                    print(f"🎯 Найдена наименьшая группа: {obj_type} ({len(regions)} элементов)")
                    break
        
        return minority_objects
    
    def _find_similar_regions(self, region_images, instruction):
        """Находит регионы, похожие на заданный образец"""
        print("🔍 Ищем похожие элементы...")
        
        # Анализируем все регионы
        region_analysis = []
        
        for region_data in region_images:
            region_image = region_data["image"]
            region_index = region_data["index"]
            
            score, detected_object = self.detector.analyze_cell_with_clip(region_image, instruction)
            
            region_analysis.append({
                "index": region_index,
                "object": detected_object,
                "score": score,
                "center": region_data["center"],
                "bbox": region_data["bbox"]
            })
            
            print(f"   Регион {region_index}: {detected_object} (score: {score:.3f})")
        
        # Группируем похожие объекты
        similar_groups = {}
        for analysis in region_analysis:
            obj_type = analysis["object"]
            if obj_type not in similar_groups:
                similar_groups[obj_type] = []
            similar_groups[obj_type].append(analysis)
        
        # Возвращаем самую большую группу (наиболее представленные объекты)
        if similar_groups:
            largest_group = max(similar_groups.values(), key=len)
            print(f"🎯 Найдена самая большая группа: {largest_group[0]['object']} ({len(largest_group)} элементов)")
            return largest_group
        
        return []
    
    def _find_specific_objects(self, region_images, instruction):
        """Находит специфичные объекты по инструкции"""
        print("🔍 Ищем специфичные объекты...")
        
        matching_regions = []
        
        for region_data in region_images:
            region_image = region_data["image"]
            region_index = region_data["index"]
            
            # Анализируем соответствие инструкции
            score, detected_object = self.detector.analyze_cell_with_clip(region_image, instruction)
            
            print(f"   Регион {region_index}: {detected_object} (score: {score:.3f})")
            
            # Если score выше порога - регион подходит
            if score > 0.25:
                matching_regions.append({
                    "index": region_index,
                    "object": detected_object,
                    "score": score,
                    "center": region_data["center"],
                    "bbox": region_data["bbox"]
                })
                print(f"✅ Регион {region_index} подходит: {detected_object}")
        
        # Сортируем по score
        matching_regions.sort(key=lambda x: x["score"], reverse=True)
        
        return matching_regions


def test_semantic_analysis(image_path="analysis/captcha.png", instruction="Пожалуйста, нажмите на изображение, которое не принадлежит к группе"):
    """Тестирует семантический анализ"""
    from region_detector import RegionDetector
    
    if not Path(image_path).exists():
        print(f"❌ Изображение не найдено: {image_path}")
        return
    
    print("🧠 Тестирование семантического анализа")
    print("="*50)
    
    # 1. Детекция регионов
    detector = RegionDetector()
    regions = detector.detect_regions(image_path)
    
    if not regions:
        print("❌ Регионы не найдены")
        return
    
    # 2. Извлечение изображений регионов
    region_images = detector.extract_region_images(image_path, regions)
    
    # 3. Семантический анализ
    comparator = SemanticComparator()
    results = comparator.analyze_regions(region_images, instruction)
    
    # 4. Выводим результаты
    print(f"\n🎯 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("="*30)
    
    if results:
        for result in results:
            center = result["center"]
            obj = result["object"]
            score = result.get("score", 0)
            print(f"Регион {result['index']}: {obj} (score: {score:.3f})")
            print(f"  → Координаты клика: {center}")
        
        print(f"\n🎉 РЕКОМЕНДАЦИЯ: Кликнуть на {len(results)} регионов")
        
    else:
        print("❌ Подходящих регионов не найдено")
        print("🎯 РЕКОМЕНДАЦИЯ: Нажать 'Пропустить'")


if __name__ == "__main__":
    test_semantic_analysis()
