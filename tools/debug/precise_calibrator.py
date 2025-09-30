#!/usr/bin/env python3
"""
Точная калибровка координат hCaptcha с пошаговой диагностикой.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def precise_coordinate_mapping():
    """Точное определение координат сетки"""
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
            
            # Находим iframe с canvas
            challenge_frame = None
            for frame in page.frames:
                try:
                    if 'hcaptcha.com' in frame.url and 'challenge' in frame.url:
                        challenge_frame = frame
                        break
                except:
                    continue
            
            if not challenge_frame:
                print("❌ iframe не найден")
                return
            
            print("🔍 ТОЧНАЯ ДИАГНОСТИКА CANVAS")
            print("="*40)
            
            # Получаем детальную информацию
            canvas_analysis = challenge_frame.evaluate("""
                (() => {
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return {error: "Canvas не найден"};
                    
                    const rect = canvas.getBoundingClientRect();
                    const containerRect = document.querySelector('.challenge-container')?.getBoundingClientRect();
                    
                    return {
                        canvas: {
                            logical: {width: canvas.width, height: canvas.height},
                            css: {width: rect.width, height: rect.height},
                            position: {x: rect.x, y: rect.y, left: rect.left, top: rect.top}
                        },
                        container: containerRect ? {
                            width: containerRect.width,
                            height: containerRect.height,
                            x: containerRect.x,
                            y: containerRect.y
                        } : null,
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight
                        }
                    };
                })()
            """)
            
            print("📊 Canvas анализ:")
            canvas_info = canvas_analysis['canvas']
            print(f"   Логические: {canvas_info['logical']['width']}x{canvas_info['logical']['height']}")
            print(f"   CSS: {canvas_info['css']['width']}x{canvas_info['css']['height']}")
            print(f"   Позиция: ({canvas_info['position']['x']}, {canvas_info['position']['y']})")
            
            if canvas_analysis['container']:
                cont_info = canvas_analysis['container']
                print(f"📦 Container: {cont_info['width']}x{cont_info['height']} в ({cont_info['x']}, {cont_info['y']})")
            
            # Тестируем систематически каждую ячейку
            print(f"\n🎯 СИСТЕМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ СЕТКИ 3x3")
            print("="*50)
            
            # Предполагаемые координаты с учетом структуры hCaptcha
            # Учитываем что сверху есть примеры + инструкция
            
            # Основываясь на стандартной структуре hCaptcha:
            # - Инструкция: ~60px сверху  
            # - Основная область: начинается с ~100px
            # - Сетка 3x3 в области ~400x300px
            
            grid_coords = [
                # Ряд 1 (верхний)
                (83, 180),   # [0] лево-верх
                (250, 180),  # [1] центр-верх  
                (417, 180),  # [2] право-верх
                
                # Ряд 2 (средний)
                (83, 290),   # [3] лево-центр
                (250, 290),  # [4] центр-центр
                (417, 290),  # [5] право-центр ← ПРОБЛЕМНАЯ ЯЧЕЙКА
                
                # Ряд 3 (нижний)
                (83, 400),   # [6] лево-низ
                (250, 400),  # [7] центр-низ
                (417, 400),  # [8] право-низ
            ]
            
            descriptions = [
                "лево-верх", "центр-верх", "право-верх",
                "лево-центр", "центр-центр", "право-центр", 
                "лево-низ", "центр-низ", "право-низ"
            ]
            
            # Добавляем цветные отметки
            for i, ((x, y), desc) in enumerate(zip(grid_coords, descriptions)):
                try:
                    # Преобразуем в canvas координаты
                    canvas_x = x * 2  # Масштаб 2:1
                    canvas_y = y * 2
                    
                    # Цветовая схема для лучшей видимости
                    colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'cyan', 'magenta']
                    color = colors[i % len(colors)]
                    
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            
                            // Цветной круг
                            ctx.fillStyle = '{color}';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 25, 0, 2 * Math.PI);
                            ctx.fill();
                            
                            // Черная обводка
                            ctx.strokeStyle = 'black';
                            ctx.lineWidth = 3;
                            ctx.stroke();
                            
                            // Белый номер
                            ctx.fillStyle = 'white';
                            ctx.font = 'bold 20px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('{i}', {canvas_x}, {canvas_y} + 7);
                        }}
                    """)
                    
                    print(f"   [{i}] {desc}: CSS({x},{y}) → Canvas({canvas_x},{canvas_y}) → {color}")
                    
                except Exception as e:
                    print(f"❌ Ошибка отметки {i}: {e}")
            
            print(f"\n📋 АНАЛИЗ ПОЗИЦИЙ:")
            print(f"✅ Если цветные круги в центрах ячеек - координаты правильные")
            print(f"❌ Если смещены - запишите правильные позиции")
            
            input("\nПосмотрите браузер и нажмите Enter...")
            
            # Интерактивная корректировка
            print(f"\n🔧 КОРРЕКТИРОВКА КООРДИНАТ:")
            print(f"Какая ячейка смещена больше всего? (0-8, или 'ok' если все правильно): ", end="")
            
            user_input = input().strip().lower()
            
            if user_input == 'ok':
                print("✅ Координаты правильные!")
                
                # Сохраняем финальные координаты
                final_coords = {
                    "grid_3x3": grid_coords,
                    "canvas_scale": 2.0,
                    "status": "calibrated"
                }
                
                coord_file = Path("analysis/coordinates.json")
                import json
                with open(coord_file, 'w') as f:
                    json.dump(final_coords, f, indent=2)
                
                print(f"💾 Координаты сохранены в: {coord_file}")
                
            elif user_input.isdigit():
                cell_num = int(user_input)
                if 0 <= cell_num <= 8:
                    print(f"🎯 Тестируем реальный клик по ячейке {cell_num}...")
                    
                    x, y = grid_coords[cell_num]
                    
                    # Получаем абсолютные координаты для клика
                    canvas_bbox = challenge_frame.locator('canvas').bounding_box()
                    abs_x = canvas_bbox['x'] + x
                    abs_y = canvas_bbox['y'] + y
                    
                    print(f"📍 Кликаем: CSS({x},{y}) → Абсолютные({abs_x},{abs_y})")
                    
                    # Реальный клик
                    page.mouse.click(abs_x, abs_y)
                    
                    # Зеленая отметка успеха
                    canvas_x, canvas_y = x * 2, y * 2
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            ctx.fillStyle = 'lime';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 30, 0, 2 * Math.PI);
                            ctx.fill();
                            ctx.fillStyle = 'black';
                            ctx.font = 'bold 24px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('✓', {canvas_x}, {canvas_y} + 8);
                        }}
                    """)
                    
                    print(f"✅ Клик выполнен! Ячейка должна подсветиться зеленым")
                    time.sleep(2)
                    
            input("\nИсследование завершено. Нажмите Enter...")
            
        except Exception as e:
            print(f"❌ Ошибка калибровки: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    print("🔬 Точная калибровка координат hCaptcha")
    print("="*45)
    
    precise_coordinate_mapping()
