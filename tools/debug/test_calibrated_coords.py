#!/usr/bin/env python3
"""
Тест откалиброванных координат с визуальной проверкой.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def test_calibrated_coordinates():
    """Тестирует откалиброванные координаты"""
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
            
            # Находим iframe
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
            
            print("🎯 ТЕСТ ОТКАЛИБРОВАННЫХ КООРДИНАТ")
            print("="*40)
            
            # Новые откалиброванные координаты
            calibrated_coords = [
                (85, 130),   (250, 130),  (415, 130),   # Ряд 1
                (85, 260),   (250, 260),  (415, 260),   # Ряд 2  
                (85, 390),   (250, 390),  (415, 390)    # Ряд 3
            ]
            
            colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'cyan', 'lime']
            
            # Добавляем отметки в новые позиции
            for i, (x, y) in enumerate(calibrated_coords):
                try:
                    # Canvas координаты (x2 для логических размеров)
                    canvas_x = x * 2
                    canvas_y = y * 2
                    
                    color = colors[i]
                    
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            
                            // Большой цветной круг
                            ctx.fillStyle = '{color}';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 25, 0, 2 * Math.PI);
                            ctx.fill();
                            
                            // Белая обводка
                            ctx.strokeStyle = 'white';
                            ctx.lineWidth = 4;
                            ctx.stroke();
                            
                            // Черный номер
                            ctx.fillStyle = 'black';
                            ctx.font = 'bold 20px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('{i}', {canvas_x}, {canvas_y} + 7);
                        }}
                    """)
                    
                    print(f"   [{i}] CSS({x},{y}) → Canvas({canvas_x},{canvas_y}) → {color}")
                    
                except Exception as e:
                    print(f"❌ Ошибка отметки {i}: {e}")
            
            print(f"\n👀 ПРОВЕРКА ТОЧНОСТИ:")
            print(f"✅ Если цветные круги ТОЧНО в центрах ячеек - координаты правильные!")
            print(f"❌ Если все еще смещены - нужна дополнительная коррекция")
            
            input("\nПосмотрите результат и нажмите Enter...")
            
            # Интерактивный тест клика
            print(f"\n🖱️ ИНТЕРАКТИВНЫЙ ТЕСТ КЛИКА:")
            print(f"Введите номер ячейки для тестового клика (0-8): ", end="")
            
            try:
                test_num = int(input().strip())
                if 0 <= test_num <= 8:
                    x, y = calibrated_coords[test_num]
                    
                    print(f"🎯 Тестируем клик по ячейке {test_num} в позиции ({x}, {y})")
                    
                    # Получаем абсолютные координаты
                    canvas_bbox = challenge_frame.locator('canvas').bounding_box()
                    abs_x = canvas_bbox['x'] + x
                    abs_y = canvas_bbox['y'] + y
                    
                    print(f"📍 Абсолютные координаты: ({abs_x}, {abs_y})")
                    
                    # Выполняем клик с человеческими движениями
                    page.mouse.move(abs_x - 20, abs_y - 20)
                    page.wait_for_timeout(300)
                    page.mouse.move(abs_x, abs_y)
                    page.wait_for_timeout(200)
                    page.mouse.click(abs_x, abs_y)
                    
                    # Отмечаем место клика зеленым
                    canvas_x, canvas_y = x * 2, y * 2
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            ctx.fillStyle = 'lime';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 35, 0, 2 * Math.PI);
                            ctx.fill();
                            ctx.fillStyle = 'black';
                            ctx.font = 'bold 24px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('✓', {canvas_x}, {canvas_y} + 8);
                        }}
                    """)
                    
                    print(f"✅ Тестовый клик выполнен!")
                    print(f"🟢 Если ячейка подсветилась правильно - координаты точные")
                    
                    time.sleep(3)
                    
            except ValueError:
                print("❌ Введите число от 0 до 8")
            except Exception as e:
                print(f"❌ Ошибка тестового клика: {e}")
            
            input("\nТест завершен. Нажмите Enter...")
            
        except Exception as e:
            print(f"❌ Ошибка теста: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    print("🔬 Тест откалиброванных координат")
    print("="*35)
    
    test_calibrated_coordinates()
