#!/usr/bin/env python3
"""
Отладка координат canvas для понимания реальной системы координат hCaptcha
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def debug_canvas_coordinates():
    """Отлаживает систему координат canvas"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        try:
            page = browser.new_page()
            
            print("🌐 Переходим на тестовую страницу...")
            page.goto("http://127.0.0.1:5000", wait_until="load")
            
            # Кликаем по чекбоксу
            page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
            checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
            checkbox_frame.locator('#checkbox').click()
            
            # Ждем задание
            time.sleep(5)
            
            # Находим iframe с canvas
            challenge_frame = None
            frames = page.frames
            
            for frame in frames:
                try:
                    if 'hcaptcha.com' in frame.url and 'challenge' in frame.url:
                        challenge_frame = frame
                        print(f"✅ Найден iframe: {frame.title()}")
                        break
                except:
                    continue
            
            if not challenge_frame:
                print("❌ iframe не найден")
                return
            
            # Детальный анализ canvas
            canvas_info = challenge_frame.evaluate("""
                (() => {
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return {error: "Canvas не найден"};
                    
                    const rect = canvas.getBoundingClientRect();
                    const style = window.getComputedStyle(canvas);
                    
                    return {
                        // Логические размеры canvas
                        width: canvas.width,
                        height: canvas.height,
                        
                        // CSS размеры
                        cssWidth: parseFloat(style.width),
                        cssHeight: parseFloat(style.height),
                        
                        // Позиция на странице
                        boundingRect: {
                            x: rect.x,
                            y: rect.y, 
                            width: rect.width,
                            height: rect.height,
                            left: rect.left,
                            top: rect.top,
                            right: rect.right,
                            bottom: rect.bottom
                        },
                        
                        // Масштабирование
                        scaleX: canvas.width / rect.width,
                        scaleY: canvas.height / rect.height
                    };
                })()
            """)
            
            print("\n📊 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О CANVAS:")
            print("="*50)
            print(f"🔢 Логические размеры: {canvas_info['width']}x{canvas_info['height']}")
            print(f"🎨 CSS размеры: {canvas_info['cssWidth']}x{canvas_info['cssHeight']}")
            print(f"📍 Позиция: ({canvas_info['boundingRect']['x']}, {canvas_info['boundingRect']['y']})")
            print(f"📏 Bounding rect: {canvas_info['boundingRect']}")
            print(f"⚖️ Масштабирование: X={canvas_info['scaleX']:.3f}, Y={canvas_info['scaleY']:.3f}")
            
            # Тестируем клики в известных позициях сетки 3x3
            test_positions = [
                (83, 150, "верх-лево"),
                (250, 150, "верх-центр"), 
                (417, 150, "верх-право"),
                (83, 290, "центр-лево"),
                (250, 290, "центр-центр"),
                (417, 290, "центр-право"),
                (83, 430, "низ-лево"),
                (250, 430, "низ-центр"),
                (417, 430, "низ-право")
            ]
            
            print(f"\n🎯 ТЕСТИРОВАНИЕ КЛИКОВ В СТАНДАРТНЫХ ПОЗИЦИЯХ:")
            print("="*50)
            
            # Добавляем отметки во все позиции для визуального анализа
            for i, (x, y, desc) in enumerate(test_positions):
                try:
                    # Рассчитываем правильные координаты с учетом масштабирования
                    if canvas_info['scaleX'] != 1.0 or canvas_info['scaleY'] != 1.0:
                        # Canvas имеет внутреннее масштабирование
                        canvas_x = int(x * canvas_info['scaleX'])
                        canvas_y = int(y * canvas_info['scaleY'])
                    else:
                        canvas_x, canvas_y = x, y
                    
                    # Добавляем визуальную отметку
                    challenge_frame.evaluate(f"""
                        const canvas = document.querySelector('canvas');
                        if (canvas) {{
                            const ctx = canvas.getContext('2d');
                            ctx.fillStyle = 'red';
                            ctx.beginPath();
                            ctx.arc({canvas_x}, {canvas_y}, 8, 0, 2 * Math.PI);
                            ctx.fill();
                            
                            ctx.fillStyle = 'white';
                            ctx.font = '12px Arial';
                            ctx.fillText('{i}', {canvas_x}-4, {canvas_y}+3);
                        }}
                    """)
                    
                    print(f"Позиция {i}: {desc} - GPT({x},{y}) → Canvas({canvas_x},{canvas_y})")
                    
                except Exception as e:
                    print(f"❌ Ошибка отметки {i}: {e}")
            
            print(f"\n🔍 Проверьте браузер - должны быть красные точки с номерами 0-8")
            print(f"💡 Если точки НЕ в центрах ячеек, координаты нужно корректировать")
            
            input("Нажмите Enter после проверки...")
            
        except Exception as e:
            print(f"❌ Ошибка отладки: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    print("🔍 Отладка координат canvas")
    print("="*30)
    
    debug_canvas_coordinates()
