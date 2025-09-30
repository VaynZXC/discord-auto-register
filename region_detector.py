#!/usr/bin/env python3
"""
Детектор реальных кликабельных областей в капчах.
Находит круги, квадраты, кнопки вместо механического деления.
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path


class RegionDetector:
    """Детектор кликабельных областей в капчах"""
    
    def __init__(self):
        self.min_area = 1000  # Минимальная площадь области
        self.regions = []
        
    def detect_regions(self, image_path):
        """Находит все кликабельные области на изображении"""
        try:
            # Загружаем изображение
            pil_image = Image.open(image_path)
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            print(f"🔍 Анализируем изображение {cv_image.shape}")
            
            # Пробуем разные методы детекции
            regions = []
            
            # 1. Детекция кругов
            circles = self._detect_circles(cv_image)
            if circles:
                regions.extend(circles)
                print(f"⭕ Найдено кругов: {len(circles)}")
            
            # 2. Детекция прямоугольников/квадратов
            rectangles = self._detect_rectangles(cv_image)
            if rectangles:
                regions.extend(rectangles)
                print(f"🔲 Найдено прямоугольников: {len(rectangles)}")
            
            # 3. Детекция контуров
            contours = self._detect_contours(cv_image)
            if contours:
                regions.extend(contours)
                print(f"🎯 Найдено контуров: {len(contours)}")
            
            # Удаляем дубликаты и слишком маленькие области
            regions = self._filter_regions(regions)
            
            print(f"✅ Итого найдено регионов: {len(regions)}")
            
            # Сохраняем области для отладки
            self._save_debug_regions(cv_image, regions, image_path)
            
            return regions
            
        except Exception as e:
            print(f"❌ Ошибка детекции регионов: {e}")
            return []
    
    def _detect_circles(self, image):
        """Детектирует круглые области"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Применяем размытие для лучшей детекции
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Детекция кругов методом Хафа
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=50,  # Минимальное расстояние между центрами
                param1=50,   # Верхний порог для детекции границ
                param2=30,   # Порог накопления для центров
                minRadius=20, # Минимальный радиус
                maxRadius=100 # Максимальный радиус
            )
            
            regions = []
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                
                for (x, y, r) in circles:
                    # Создаем прямоугольную область вокруг круга
                    left = max(0, x - r)
                    top = max(0, y - r)
                    right = min(image.shape[1], x + r)
                    bottom = min(image.shape[0], y + r)
                    
                    regions.append({
                        "type": "circle",
                        "bbox": (left, top, right, bottom),
                        "center": (x, y),
                        "radius": r,
                        "area": np.pi * r * r
                    })
            
            return regions
            
        except Exception as e:
            print(f"❌ Ошибка детекции кругов: {e}")
            return []
    
    def _detect_rectangles(self, image):
        """Детектирует прямоугольные области"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Детекция границ
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Поиск линий
            lines = cv2.HoughLinesP(
                edges, 
                rho=1, 
                theta=np.pi/180, 
                threshold=50,
                minLineLength=30,
                maxLineGap=10
            )
            
            regions = []
            
            if lines is not None:
                # Группируем линии в прямоугольники (упрощенная версия)
                # Для базовой версии просто ищем области с высокой плотностью линий
                
                # Используем морфологические операции для поиска прямоугольных областей
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
                
                # Находим контуры прямоугольных областей
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    # Аппроксимируем контур
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Если контур похож на прямоугольник (4 угла)
                    if len(approx) >= 4:
                        x, y, w, h = cv2.boundingRect(contour)
                        area = w * h
                        
                        if area > self.min_area:
                            regions.append({
                                "type": "rectangle",
                                "bbox": (x, y, x + w, y + h),
                                "center": (x + w//2, y + h//2),
                                "area": area,
                                "aspect_ratio": w/h
                            })
            
            return regions
            
        except Exception as e:
            print(f"❌ Ошибка детекции прямоугольников: {e}")
            return []
    
    def _detect_contours(self, image):
        """Детектирует области по контурам"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Применяем адаптивную пороговую фильтрацию
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Находим контуры
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            regions = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area > self.min_area:
                    # Получаем ограничивающий прямоугольник
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Вычисляем центр масс
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w//2, y + h//2
                    
                    regions.append({
                        "type": "contour",
                        "bbox": (x, y, x + w, y + h),
                        "center": (cx, cy),
                        "area": area,
                        "perimeter": cv2.arcLength(contour, True),
                        "contour": contour
                    })
            
            return regions
            
        except Exception as e:
            print(f"❌ Ошибка детекции контуров: {e}")
            return []
    
    def _filter_regions(self, regions):
        """Фильтрует и объединяет найденные регионы"""
        if not regions:
            return []
        
        # Удаляем дубликаты (регионы которые сильно пересекаются)
        filtered = []
        
        for region in regions:
            is_duplicate = False
            
            for existing in filtered:
                # Проверяем пересечение областей
                overlap = self._calculate_overlap(region["bbox"], existing["bbox"])
                
                if overlap > 0.7:  # Если пересечение > 70%
                    is_duplicate = True
                    # Оставляем регион с большей площадью
                    if region["area"] > existing["area"]:
                        filtered.remove(existing)
                        filtered.append(region)
                    break
            
            if not is_duplicate:
                filtered.append(region)
        
        # Сортируем по площади (большие первыми)
        filtered.sort(key=lambda x: x["area"], reverse=True)
        
        # Ограничиваем количество (обычно в капчах не более 12 элементов)
        return filtered[:12]
    
    def _calculate_overlap(self, bbox1, bbox2):
        """Вычисляет пересечение двух bbox в процентах"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Координаты пересечения
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        # Если нет пересечения
        if x1_i >= x2_i or y1_i >= y2_i:
            return 0.0
        
        # Площадь пересечения
        intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Площади областей
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Процент пересечения относительно меньшей области
        min_area = min(area1, area2)
        return intersection_area / min_area if min_area > 0 else 0.0
    
    def _save_debug_regions(self, image, regions, original_path):
        """Сохраняет отладочную информацию о найденных регионах"""
        try:
            debug_dir = Path("analysis/regions")
            debug_dir.mkdir(exist_ok=True)
            
            # Создаем копию изображения для аннотации
            annotated = image.copy()
            
            # Рисуем найденные регионы
            for i, region in enumerate(regions):
                bbox = region["bbox"]
                center = region["center"]
                region_type = region["type"]
                
                # Цвет в зависимости от типа
                if region_type == "circle":
                    color = (0, 255, 0)  # Зеленый для кругов
                elif region_type == "rectangle":
                    color = (255, 0, 0)  # Синий для прямоугольников  
                else:
                    color = (0, 0, 255)  # Красный для контуров
                
                # Рисуем bbox
                cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                
                # Рисуем центр
                cv2.circle(annotated, center, 5, color, -1)
                
                # Подписываем номер
                cv2.putText(annotated, f"{i}", (center[0]-10, center[1]-15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Сохраняем аннотированное изображение
            debug_path = debug_dir / "detected_regions.png"
            cv2.imwrite(str(debug_path), annotated)
            
            print(f"🔍 Отладочная информация сохранена: {debug_path}")
            
            # Сохраняем отдельные регионы
            original_pil = Image.open(original_path)
            
            for i, region in enumerate(regions):
                bbox = region["bbox"]
                region_image = original_pil.crop(bbox)
                region_path = debug_dir / f"region_{i}_{region['type']}.png"
                region_image.save(region_path)
            
            print(f"📦 Сохранено {len(regions)} отдельных регионов")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения отладки: {e}")
    
    def extract_region_images(self, image_path, regions):
        """Извлекает изображения регионов"""
        try:
            pil_image = Image.open(image_path)
            region_images = []
            
            for i, region in enumerate(regions):
                bbox = region["bbox"]
                region_image = pil_image.crop(bbox)
                
                region_data = {
                    "index": i,
                    "image": region_image,
                    "bbox": bbox,
                    "center": region["center"],
                    "type": region["type"],
                    "area": region["area"]
                }
                
                region_images.append(region_data)
            
            return region_images
            
        except Exception as e:
            print(f"❌ Ошибка извлечения регионов: {e}")
            return []


def test_region_detection(image_path="analysis/captcha.png"):
    """Тестирует детекцию регионов"""
    detector = RegionDetector()
    
    if not Path(image_path).exists():
        print(f"❌ Изображение не найдено: {image_path}")
        return
    
    print(f"🔍 Тестируем детекцию регионов на: {image_path}")
    print("="*50)
    
    regions = detector.detect_regions(image_path)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ ДЕТЕКЦИИ:")
    print("="*30)
    
    if regions:
        for i, region in enumerate(regions):
            bbox = region["bbox"] 
            center = region["center"]
            area = region["area"]
            region_type = region["type"]
            
            print(f"Регион {i}: {region_type}")
            print(f"  📍 Центр: {center}")
            print(f"  📏 Bbox: {bbox}")
            print(f"  📊 Площадь: {area}")
            print()
        
        print(f"🎯 Готово для анализа: {len(regions)} регионов")
        
    else:
        print("❌ Регионы не найдены")
        print("💡 Попробуйте другое изображение или настройте параметры")


if __name__ == "__main__":
    print("🔍 Тестирование детектора регионов")
    print("="*40)
    
    test_region_detection()
