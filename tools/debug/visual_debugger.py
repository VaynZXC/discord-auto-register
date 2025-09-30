#!/usr/bin/env python3
"""
Визуальный отладчик координат капчи.
Создает диагностическое изображение с сеткой и размерами ячеек.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
import json


def create_visual_debug():
    """Создает визуальную диагностику координат"""
    
    # Сначала получаем свежий скриншот
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        try:
            page = browser.new_page()
            page.goto("http://127.0.0.1:5000", wait_until="load")
            
            # Активируем капчу
            page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
            checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
            checkbox_frame.locator('#checkbox').click()
            time.sleep(5)
            
            # Делаем скриншот
            challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')
            screenshot_path = Path("analysis/debug_captcha.png")
            challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
            print(f"📸 Скриншот для отладки: {screenshot_path}")
            
        except Exception as e:
            print(f"❌ Ошибка создания скриншота: {e}")
            return
        finally:
            browser.close()
    
    # Теперь рисуем диагностику
    try:
        # Загружаем изображение
        img = Image.open(screenshot_path)
        width, height = img.size
        
        print(f"📐 Размеры изображения: {width}x{height}")
        
        # Создаем копию для рисования
        debug_img = img.copy()
        draw = ImageDraw.Draw(debug_img)
        
        # Пробуем загрузить шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            big_font = ImageFont.truetype("arial.ttf", 18)
        except:
            try:
                font = ImageFont.load_default()
                big_font = ImageFont.load_default()
            except:
                font = None
                big_font = None
        
        # Новые откалиброванные координаты (финальная версия)
        grid_coords = [
            (100, 140), (250, 140), (400, 140),  # Ряд 1
            (100, 270), (250, 270), (400, 270),  # Ряд 2
            (100, 400), (250, 400), (400, 400)   # Ряд 3
        ]
        
        colors = [
            "#FF0000", "#FF8000", "#FFFF00",  # Красный, оранжевый, желтый
            "#00FF00", "#0080FF", "#8000FF",  # Зеленый, синий, фиолетовый  
            "#FF00FF", "#00FFFF", "#FF0080"   # Пурпурный, голубой, розовый
        ]
        
        # Предполагаемые размеры ячеек (на основе стандартной сетки 3x3)
        cell_width = 110   # Примерная ширина ячейки
        cell_height = 90   # Примерная высота ячейки
        
        print(f"🎯 Рисуем диагностическую сетку...")
        print(f"📏 Предполагаемый размер ячейки: {cell_width}x{cell_height}px")
        
        # Рисуем каждую ячейку
        for i, (center_x, center_y) in enumerate(grid_coords):
            color = colors[i]
            
            # Границы ячейки (прямоугольник вокруг центра)
            left = center_x - cell_width // 2
            top = center_y - cell_height // 2
            right = center_x + cell_width // 2
            bottom = center_y + cell_height // 2
            
            # Рисуем прямоугольник ячейки
            draw.rectangle([left, top, right, bottom], outline=color, width=3)
            
            # Рисуем центральную точку
            point_size = 8
            draw.ellipse([center_x-point_size, center_y-point_size, 
                         center_x+point_size, center_y+point_size], 
                        fill=color, outline="white", width=2)
            
            # Подписываем номер ячейки
            if font:
                draw.text((center_x-5, center_y-25), f"{i}", fill=color, font=big_font)
            
            # Подписываем координаты
            coord_text = f"({center_x},{center_y})"
            if font:
                draw.text((center_x-30, center_y+15), coord_text, fill=color, font=font)
            
            # Размеры ячейки
            size_text = f"{cell_width}x{cell_height}"
            if font:
                draw.text((left+5, top+5), size_text, fill=color, font=font)
            
            print(f"   [{i}] Центр: ({center_x},{center_y}) | Границы: ({left},{top})-({right},{bottom})")
        
        # Добавляем общую информацию
        if font:
            draw.text((10, 10), f"Размер изображения: {width}x{height}", fill="red", font=big_font)
            draw.text((10, height-30), f"Размер ячейки: {cell_width}x{cell_height}", fill="red", font=big_font)
        
        # Сохраняем отладочное изображение
        debug_path = Path("analysis/debug_grid.png")
        debug_img.save(debug_path)
        
        print(f"\n✅ Визуальная диагностика создана: {debug_path}")
        print(f"🔍 В файле показано:")
        print(f"   📍 Цветные точки - центры наших кликов")
        print(f"   🔲 Цветные прямоугольники - предполагаемые границы ячеек")
        print(f"   📏 Размеры каждой ячейки в пикселях")
        print(f"   📋 Координаты центров")
        
        # Сохраняем данные сетки
        grid_data = {
            "image_size": [width, height],
            "cell_size": [cell_width, cell_height], 
            "grid_coordinates": grid_coords,
            "colors": colors,
            "status": "debug_generated"
        }
        
        grid_file = Path("analysis/grid_debug.json")
        with open(grid_file, 'w') as f:
            json.dump(grid_data, f, indent=2)
        
        print(f"💾 Данные сетки сохранены: {grid_file}")
        
        print(f"\n📋 АНАЛИЗ ВИЗУАЛЬНОЙ ДИАГНОСТИКИ:")
        print(f"1. Откройте {debug_path} в любом просмотрщике изображений")
        print(f"2. Проверьте попадают ли цветные точки в центры реальных ячеек")
        print(f"3. Если нет - нужно корректировать координаты или размеры ячеек")
        print(f"4. Цветные прямоугольники показывают наши предполагаемые области клика")
        
    except Exception as e:
        print(f"❌ Ошибка создания визуальной диагностики: {e}")


def analyze_cell_sizes():
    """Анализирует реальные размеры ячеек"""
    print(f"\n🔬 АНАЛИЗ РАЗМЕРОВ ЯЧЕЕК:")
    print(f"📐 Стандартные размеры hCaptcha:")
    print(f"   Общая область: 500x430px")
    print(f"   Инструкция сверху: ~60px")
    print(f"   Рабочая область: 500x370px")
    print(f"   Сетка 3x3: ~150x120px на ячейку")
    
    # Альтернативные размеры ячеек для тестирования
    alternative_sizes = [
        (150, 120, "Стандартный"),
        (140, 110, "Компактный"),
        (160, 130, "Расширенный"),
        (130, 100, "Минимальный")
    ]
    
    print(f"\n📏 ВАРИАНТЫ РАЗМЕРОВ ЯЧЕЕК:")
    for w, h, desc in alternative_sizes:
        total_width = w * 3
        total_height = h * 3
        print(f"   {desc}: {w}x{h}px (общая сетка: {total_width}x{total_height}px)")


if __name__ == "__main__":
    print("🔍 Визуальный отладчик координат капчи")
    print("="*45)
    
    create_visual_debug()
    analyze_cell_sizes()
    
    print(f"\n💡 СЛЕДУЮЩИЕ ШАГИ:")
    print(f"1. Проверьте debug_grid.png - правильно ли расположены точки")
    print(f"2. Если нет - скорректируйте координаты в gpt_analyzer.py") 
    print(f"3. Протестируйте разные размеры ячеек если нужно")
