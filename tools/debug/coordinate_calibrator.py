#!/usr/bin/env python3
"""
Калибратор координат для точного позиционирования кликов в hCaptcha.
Интерактивная настройка системы координат.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def interactive_calibration():
    """Интерактивная калибровка координат"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        try:
            page = browser.new_page()
            
            print("🌐 Переходим на тестовую страницу...")
            page.goto("http://127.0.0.1:5000", wait_until="load")
            
            # Активируем капчу
            page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
            checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
            checkbox_frame.locator('#checkbox').click()
            
            time.sleep(5)
            
            # Находим iframe с canvas
            challenge_frame = None
            frames = page.frames
            
            for frame in frames:
                try:
                    if 'hcaptcha.com' in frame.url and 'challenge' in frame.url:
                        challenge_frame = frame
                        break
                except:
                    continue
            
            if not challenge_frame:
                print("❌ iframe не найден")
                return
            
            print("🎯 ИНТЕРАКТИВНАЯ КАЛИБРОВКА КООРДИНАТ")
            print("="*50)
            
            # Сначала тестируем наши стандартные позиции
            standard_positions = [
                (83, 150, "верх-лево [0]"),
                (250, 150, "верх-центр [1]"), 
                (417, 150, "верх-право [2]"),
                (83, 290, "центр-лево [3]"),
                (250, 290, "центр-центр [4]"),
                (417, 290, "центр-право [5]"),
                (83, 430, "низ-лево [6]"),
                (250, 430, "низ-центр [7]"),
                (417, 430, "низ-право [8]")
            ]
            
            print("📍 Добавляем отметки в стандартные позиции...")
            
            # Добавляем отметки
            for i, (x, y, desc) in enumerate(standard_positions):
                try:
                    # Конвертируем в canvas координаты (умножаем на 2)
                    canvas_x = x * 2
                    canvas_y = y * 2
                    
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            
                            // Красный круг
                            ctx.fillStyle = 'red';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 20, 0, 2 * Math.PI);
                            ctx.fill();
                            
                            // Белый номер
                            ctx.fillStyle = 'white';
                            ctx.font = 'bold 16px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('{i}', {canvas_x}, {canvas_y} + 5);
                        }}
                    """)
                    
                    print(f"   {desc}: CSS({x},{y}) → Canvas({canvas_x},{canvas_y})")
                    
                except Exception as e:
                    print(f"❌ Ошибка отметки {i}: {e}")
            
            print(f"\n👀 ПРОВЕРЬТЕ БРАУЗЕР:")
            print(f"📍 Должно быть 9 красных кругов с номерами 0-8")
            print(f"✅ Если круги ТОЧНО в центрах ячеек - координаты правильные")
            print(f"❌ Если круги смещены - нужна дополнительная корректировка")
            
            input("\nПосле проверки нажмите Enter для продолжения...")
            
            # Теперь тестируем точные клики
            print(f"\n🖱️ ТЕСТИРОВАНИЕ РЕАЛЬНЫХ КЛИКОВ:")
            print(f"Выберите номер ячейки для тестового клика (0-8): ", end="")
            
            try:
                test_cell = int(input().strip())
                if 0 <= test_cell <= 8:
                    x, y, desc = standard_positions[test_cell]
                    
                    print(f"🎯 Тестируем клик по ячейке {test_cell}: {desc}")
                    
                    # Выполняем тестовый клик
                    canvas_x = x * 2
                    canvas_y = y * 2
                    
                    # Получаем абсолютные координаты
                    canvas_info = challenge_frame.locator('canvas').bounding_box()
                    abs_x = canvas_info['x'] + x  # Используем CSS координаты для абсолютного позиционирования  
                    abs_y = canvas_info['y'] + y
                    
                    print(f"📍 Абсолютные координаты: ({abs_x}, {abs_y})")
                    
                    # Реальный клик
                    page.mouse.click(abs_x, abs_y)
                    
                    # Отмечаем место клика зеленым
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            ctx.fillStyle = 'lime';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 15, 0, 2 * Math.PI);
                            ctx.fill();
                            ctx.fillStyle = 'black';
                            ctx.font = 'bold 16px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText('✓', {canvas_x}, {canvas_y} + 5);
                        }}
                    """)
                    
                    print(f"✅ Тестовый клик выполнен!")
                    print(f"🟢 Если ячейка подсветилась - клик прошел правильно")
                    
                    time.sleep(3)  # Даем время увидеть результат
                    
                else:
                    print("❌ Неверный номер ячейки")
                    
            except ValueError:
                print("❌ Введите число от 0 до 8")
            except Exception as e:
                print(f"❌ Ошибка тестового клика: {e}")
            
            input("\nКалибровка завершена. Нажмите Enter...")
            
        except Exception as e:
            print(f"❌ Ошибка калибровки: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    print("🔧 Интерактивная калибровка координат")
    print("="*40)
    
    interactive_calibration()
