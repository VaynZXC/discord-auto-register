#!/usr/bin/env python3
"""
Чистая система захвата и решения капч через GPT-4 Vision.
Без локальных нейронок - только GPT-4 для максимальной точности.
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright


def execute_gpt_solution_smart(page, gpt_solution, screenshot_path, structure_info=None):
    """Умное выполнение решения GPT-4 с масштабированием координат"""
    try:
        if not gpt_solution or "error" in gpt_solution:
            print("❌ Нет корректного решения от GPT-4")
            return False
        
        action = gpt_solution.get("recommendation", {}).get("action", "skip")
        target_elements = gpt_solution.get("recommendation", {}).get("target_ids", [])
        interactive_elements = gpt_solution.get("interactive_elements", [])
        
        print(f"🎯 GPT-4 рекомендует: {action}")
        
        if action == "skip":
            print("⏭️ Нажимаем 'Пропустить'...")
            return click_skip_button_smart(page)
        
        if action != "interact" or not target_elements:
            print("❌ Нет элементов для клика")
            return False
        
        # Находим iframe с заданием
        print("🔍 Детальный поиск iframe с canvas...")
        challenge_frame = None
        frames = page.frames
        
        print(f"📋 Всего iframe: {len(frames)}")
        
        for i, frame in enumerate(frames):
            try:
                frame_title = frame.title()
                frame_url = frame.url
                print(f"   Frame {i}: '{frame_title}' - {frame_url}")
                
                # Ищем iframe именно с заданием (по URL тоже)
                if ('содержание испытания' in frame_title or 
                    'hCaptcha challenge' in frame_title or
                    'challenge' in frame_url or
                    'hcaptcha.com' in frame_url):
                    
                    # Проверяем что в этом iframe есть canvas
                    try:
                        canvas_count = frame.locator('canvas').count()
                        print(f"     Canvas в iframe: {canvas_count}")
                        
                        if canvas_count > 0:
                            challenge_frame = frame
                            print(f"✅ Найден iframe с canvas: {frame_title}")
                            break
                        else:
                            print(f"     ❌ Canvas не найден в этом iframe")
                    except Exception as canvas_err:
                        print(f"     ❌ Ошибка проверки canvas: {canvas_err}")
                        
            except Exception as e:
                print(f"   Frame {i}: ошибка - {e}")
                continue
        
        if not challenge_frame:
            print("❌ Iframe с canvas не найден")
            return False
        
        # Получаем размеры canvas в iframe
        try:
            canvas_info = challenge_frame.locator('canvas').bounding_box()
            canvas_width = canvas_info['width']
            canvas_height = canvas_info['height']
            print(f"📐 Размеры canvas: {canvas_width}x{canvas_height}")
        except Exception as e:
            print(f"⚠️ Ошибка получения размеров canvas: {e}")
            print("   Используем стандартные размеры")
            canvas_width, canvas_height = 500, 430
            canvas_info = {"x": 0, "y": 0, "width": canvas_width, "height": canvas_height}
        
        # Дополнительно получаем размеры контейнера (от которого сделан скриншот)
        try:
            container_locator = challenge_frame.locator('.challenge-container')
            container_info = container_locator.bounding_box()
            container_width = container_info['width']
            container_height = container_info['height']
            offset_x = canvas_info['x'] - container_info['x']
            offset_y = canvas_info['y'] - container_info['y']
            print(f"🧭 Контейнер: {container_width}x{container_height}, смещение canvas: ({offset_x:.1f}, {offset_y:.1f})")
        except Exception as e:
            print(f"⚠️ Не удалось получить размеры контейнера: {e}")
            container_info = None
            container_width = img_width
            container_height = img_height
            offset_x = 0
            offset_y = 0

        # Получаем размеры исходного изображения  
        from PIL import Image
        try:
            img = Image.open(screenshot_path)
            img_width, img_height = img.size
            print(f"📐 Размеры изображения: {img_width}x{img_height}")
        except Exception as e:
            print(f"⚠️ Ошибка размеров изображения: {e}")
            img_width, img_height = container_width, container_height

        # Если GPT вернул элементы и мы работаем с сеткой, попробуем уточнить координаты по изображению
        tile_grid = None
        try:
            from PIL import Image
            img = Image.open(screenshot_path)
            img_width, img_height = img.size
            print(f"📐 Размеры изображения: {img_width}x{img_height}")
        except Exception as e:
            print(f"⚠️ Ошибка размеров изображения: {e}")
            img_width = img_height = None
            img = None

        # Вычисляем коэффициенты масштабирования
        scale_x = canvas_width / (img_width if img_width else canvas_width)
        scale_y = canvas_height / (img_height if img_height else canvas_height)
        print(f"🔧 Коэффициенты масштабирования: x={scale_x:.3f}, y={scale_y:.3f}")

        # Подготовка вспомогательной карты контурных центров и уточнение структуры
        contour_info = {}
        if img and gpt_solution.get("interactive_elements"):
            try:
                import cv2
                import numpy as np

                arr = np.array(img.convert('RGB'))
                height, width = arr.shape[:2]

                grid_cells = {}
                if structure_info:
                    for region in structure_info.regions:
                        if region.kind == "grid" and region.cells:
                            for cell in region.cells:
                                grid_cells[cell.id] = cell

                for element in gpt_solution["interactive_elements"]:
                    eid = element.get("id")
                    center = element.get("center") or {"x": element.get("x", 0), "y": element.get("y", 0)}
                    bbox = element.get("bbox") or {}

                    raw_cx = float(center.get("x", 0))
                    raw_cy = float(center.get("y", 0))

                    if eid in grid_cells:
                        cell = grid_cells[eid]
                        bx, by, bw, bh = cell.bbox
                        raw_cx, raw_cy = cell.center
                    else:
                        bw = float(bbox.get("width", 80))
                        bh = float(bbox.get("height", 80))
                        bx = float(bbox.get("x", raw_cx - bw / 2))
                        by = float(bbox.get("y", raw_cy - bh / 2))

                    x0 = int(np.clip(np.floor(bx), 0, width - 1))
                    y0 = int(np.clip(np.floor(by), 0, height - 1))
                    x1 = int(np.clip(np.ceil(bx + bw), x0 + 1, width))
                    y1 = int(np.clip(np.ceil(by + bh), y0 + 1, height))

                    roi = arr[y0:y1, x0:x1]
                    if roi.size == 0:
                        continue

                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                    edges = cv2.Canny(gray_roi, 40, 140)
                    coords = np.column_stack(np.where(edges > 0))

                    if len(coords) > 10:
                        min_y, min_x = coords.min(axis=0)
                        max_y, max_x = coords.max(axis=0)
                        center_x = x0 + (min_x + max_x) / 2.0
                        center_y = y0 + (min_y + max_y) / 2.0
                        tight_bbox = (
                            x0 + min_x,
                            y0 + min_y,
                            max(4.0, max_x - min_x),
                            max(4.0, max_y - min_y)
                        )
                        contour_info[eid] = {
                            "center": (center_x, center_y),
                            "bbox": tight_bbox
                        }
                    else:
                        contour_info[eid] = {
                            "center": (raw_cx, raw_cy),
                            "bbox": (bx, by, bw, bh)
                        }
            except Exception as e:
                print(f"⚠️ Не удалось вычислить контурные центры: {e}")

        # Сохраняем overlay с уточненными центрами и структурой
        overlay_path = None
        if img and gpt_solution.get("interactive_elements"):
            try:
                from PIL import ImageDraw, ImageFont
                overlay = img.copy().convert('RGB')
                draw = ImageDraw.Draw(overlay)
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except:
                    font = ImageFont.load_default()

                if structure_info:
                    ia = structure_info.instruction_area
                    draw.rectangle([ia[0], ia[1], ia[0] + ia[2], ia[1] + ia[3]], outline="#ffaa00", width=2)
                    ba = structure_info.body_area
                    draw.rectangle([ba[0], ba[1], ba[0] + ba[2], ba[1] + ba[3]], outline="#00ffaa", width=2)

                    for region in structure_info.regions:
                        rx, ry, rw, rh = region.bbox
                        draw.rectangle([rx, ry, rx + rw, ry + rh], outline="yellow", width=2)
                        draw.text((rx + 5, ry + 5), f"{region.kind}", fill="yellow", font=font)
                        if region.cells:
                            for cell in region.cells:
                                cx, cy, cw, ch = cell.bbox
                                draw.rectangle([cx, cy, cx + cw, cy + ch], outline="#00aaff", width=2)

                for element in gpt_solution["interactive_elements"]:
                    eid = element.get("id")
                    content = element.get("content", "?")
                    center = element.get("center") or {"x": element.get("x", 0), "y": element.get("y", 0)}
                    bbox = element.get("bbox") or {}
                    cx, cy = center.get("x", 0), center.get("y", 0)
                    bw = bbox.get("width", 80)
                    bh = bbox.get("height", 80)
                    bx = bbox.get("x", cx - bw / 2)
                    by = bbox.get("y", cy - bh / 2)

                    draw.rectangle([bx, by, bx + bw, by + bh], outline="red", width=2)
                    draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill="red")

                    contour_data = contour_info.get(eid)
                    if contour_data:
                        ccx, ccy = contour_data["center"]
                        tbx, tby, tw, th = contour_data["bbox"]
                        draw.rectangle([tbx, tby, tbx + tw, tby + th], outline="#00ff88", width=2)
                        draw.ellipse([ccx - 6, ccy - 6, ccx + 6, ccy + 6], outline="lime", width=3)

                    draw.text((bx, by - 18), f"#{eid}: {content}", fill="red", font=font)

                overlay_path = Path(screenshot_path).with_name("gpt_view_overlay.png")
                overlay.save(overlay_path)
                print(f"💾 Сохранен оверлей GPT: {overlay_path}")
            except Exception as e:
                print(f"⚠️ Не удалось создать overlay: {e}")
        
        # Кликаем по каждому целевому элементу с масштабированием
        print(f"🖱️ Выполняем клики по {len(target_elements)} элементам...")
        
        for element_id in target_elements:
            if element_id < len(interactive_elements):
                element = interactive_elements[element_id]
                center = element.get("center") or {"x": element.get("x", 0), "y": element.get("y", 0)}
                bbox = element.get("bbox")
                description = element.get("content")

                raw_x = center.get("x", 0)
                raw_y = center.get("y", 0)
                width = height = None

                if bbox:
                    bx = bbox.get("x", raw_x - bbox.get("width", 0) / 2)
                    by = bbox.get("y", raw_y - bbox.get("height", 0) / 2)
                    width = bbox.get("width")
                    height = bbox.get("height")
                    raw_x = bx + (width or 0) / 2
                    raw_y = by + (height or 0) / 2

                    contour_data = contour_info.get(element_id)
                    if contour_data:
                        print(f"   🎯 Контурный центр найден: {contour_data['center']}")
                        raw_x, raw_y = contour_data["center"]

                gpt_solution.setdefault("debug_clicks", []).append({
                    "element_id": element_id,
                    "description": description,
                    "center": center,
                    "bbox": bbox,
                    "contour_center": contour_info.get(element_id, {}).get("center"),
                    "size": [width, height]
                })

                css_x = raw_x * scale_x + offset_x
                css_y = raw_y * scale_y + offset_y

                print(f"   GPT координаты (ориг.): ({raw_x}, {raw_y})")
                print(f"   Скорректированные координаты: ({css_x:.1f}, {css_y:.1f})")
                print(f"   Кликаем: {description}")
                
                # Добавляем визуальную отладку - покажем где кликаем
                print(f"     🎯 Выполняем клик...")
                
                # Используем нативные mouse события Playwright (самые человекоподобные)
                try:
                    print(f"     🖱️ Нативный mouse клик Playwright...")
                    
                    # Получаем позицию canvas на странице (может отличаться от контейнера)
                    canvas_info = challenge_frame.locator('canvas').bounding_box()
                    
                    # Абсолютные координаты = позиция canvas + смещённые координаты внутри canvas
                    abs_x = canvas_info['x'] + css_x
                    abs_y = canvas_info['y'] + css_y
                    
                    print(f"     📍 Canvas позиция: ({canvas_info['x']}, {canvas_info['y']})")
                    print(f"     📍 CSS координаты после масштаба: ({css_x:.1f}, {css_y:.1f})")
                    print(f"     📍 Абсолютные координаты: ({abs_x:.1f}, {abs_y:.1f})")
                    
                    # Имитируем человеческое движение мыши + клик
                    page.mouse.move(abs_x - 15, abs_y - 15)  # Подводим мышь
                    page.wait_for_timeout(300)
                    
                    page.mouse.move(abs_x, abs_y)  # Наводим точно
                    page.wait_for_timeout(200)
                    
                    page.mouse.down()  # Нажимаем
                    page.wait_for_timeout(100)
                    
                    page.mouse.up()  # Отпускаем
                    page.wait_for_timeout(150)
                    
                    print(f"     ✅ Нативный mouse клик выполнен")
                    
                    # Добавляем визуальную отметку в canvas координатах
                    try:
                        # Для отметки на canvas нужно учесть масштаб
                        mark_x = raw_x * scale_x
                        mark_y = raw_y * scale_y
                        mark_label = f"✓{element_id}"

                        challenge_frame.evaluate(f"""
                            const canvas = document.querySelector('canvas');
                            if (canvas) {{
                                const ctx = canvas.getContext('2d');
                                ctx.fillStyle = '#00FF00';
                                ctx.beginPath();
                                ctx.arc({mark_x}, {mark_y}, 20, 0, 2 * Math.PI);
                                ctx.fill();
                                ctx.fillStyle = '#000';
                                ctx.font = 'bold 18px Arial';
                                ctx.textAlign = 'center';
                                ctx.fillText('{mark_label}', {mark_x}, {mark_y} + 6);
                            }}
                        """)
                        print(f"     🟢 Добавлена зеленая отметка {mark_label} в canvas({mark_x:.1f},{mark_y:.1f})")
                    except Exception as e:
                        print(f"     ⚠️ Отметка не добавлена: {e}")
                        
                except Exception as e:
                    print(f"     ❌ Ошибка нативного клика: {e}")
                    
                    # Fallback - последняя попытка через force
                    try:
                        print(f"     🔄 Последняя попытка - force клик...")
                        challenge_frame.locator('canvas').click(
                            position={'x': raw_x, 'y': raw_y}, 
                            force=True,
                            timeout=3000
                        )
                        print(f"     ✅ Force клик выполнен")
                    except Exception as e2:
                        print(f"     ❌ Все методы кликов провалились: {e2}")
                        return False
                
                # Пауза между кликами
                page.wait_for_timeout(1200)
        
        # Ждем результата
        page.wait_for_timeout(2000)
        print("✅ Все клики выполнены, ждем результата...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка умного выполнения GPT-4 решения: {e}")
        import traceback
        traceback.print_exc()
        return False


def click_skip_button_smart(page):
    """Умное нажатие кнопки Пропустить"""
    try:
        frames = page.frames
        for frame in frames:
            try:
                frame_title = frame.title()
                frame_url = frame.url
                if 'hcaptcha' in frame_url.lower() or 'hCaptcha' in frame_title:
                    skip_selectors = ["text=Пропустить", "text=Skip", ".refresh-button"]
                    for selector in skip_selectors:
                        try:
                            frame.locator(selector).click(timeout=3000)
                            print("✅ Нажали 'Пропустить'")
                            return True
                        except:
                            continue
            except:
                continue
        return False
    except:
        return False


def run_captcha_automation(playwright: Playwright):
    """Запускает автоматизацию для захвата и решения капчи через GPT-4"""
    # Запускаем браузер в видимом режиме
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    
    try:
        # Создаем новую страницу
        page = browser.new_page()
        
        print("🌐 Переходим на тестовую страницу...")
        page.goto("http://127.0.0.1:5000", wait_until="load")
        
        print("🔍 Ищем чекбокс hCaptcha...")
        # Ждем появления iframe с чекбоксом hCaptcha
        page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
        
        # Находим iframe с чекбоксом по title
        checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
        
        print("✅ Кликаем по чекбоксу hCaptcha...")
        # Кликаем по чекбоксу внутри iframe
        checkbox_frame.locator('#checkbox').click()
        
        print("⏳ Ожидаем появления задания капчи...")
        # Ждем появления второго iframe с заданием (увеличиваем timeout)
        try:
            page.wait_for_selector('iframe[title*="содержание испытания"]', timeout=20000)
            print("✅ Iframe с заданием найден")
        except:
            # Пробуем альтернативные селекторы
            try:
                page.wait_for_selector('iframe[src*="hcaptcha.com"]', timeout=10000)
                print("✅ Альтернативный iframe найден")
            except:
                print("⚠️ Iframe с заданием не найден, но продолжаем...")
        
        # Ждем дополнительное время для полной загрузки задания  
        time.sleep(5)
        
        print("📷 Делаем скриншот контейнера капчи...")
        # Создаем папку для анализа
        analysis_dir = Path("analysis")
        analysis_dir.mkdir(exist_ok=True)
        
        # Сохраняем скриншот именно контейнера с заданием
        challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')
        screenshot_path = analysis_dir / "captcha.png"
        
        # Пробуем сделать скриншот именно контейнера задания (полный)
        try:
            challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
            print(f"📸 Скриншот полного контейнера: {screenshot_path}")
        except:
            # Fallback к скриншоту всего body
            try:
                challenge_frame.locator('body').screenshot(path=str(screenshot_path))
                print(f"📸 Скриншот body (fallback): {screenshot_path}")
            except Exception as e:
                print(f"❌ Ошибка скриншота: {e}")
                return
        
        # ТОЛЬКО GPT-4 Vision анализ
        print("\n🤖 Запуск GPT-4 Vision анализа...")
        
        try:
            from src.vision import detect_structure
            structure_info = detect_structure(str(screenshot_path))
        except Exception as structure_error:
            print(f"⚠️ Не удалось определить структуру: {structure_error}")
            structure_info = None

        try:
            from src.gpt import GPTAnalyzer
            
            # Анализируем капчу через GPT-4 (полное изображение)
            gpt_analyzer = GPTAnalyzer()
            gpt_solution = gpt_analyzer.analyze_captcha(str(screenshot_path))

            # Сохраняем то, что видит GPT
            if gpt_solution:
                debug_data = {
                    "instruction": gpt_solution.get("instruction"),
                    "task_type": gpt_solution.get("task_type"),
                    "interactive_elements": gpt_solution.get("interactive_elements", []),
                    "recommendation": gpt_solution.get("recommendation", {}),
                    "image_size": None
                }
                try:
                    from PIL import Image
                    img = Image.open(screenshot_path)
                    debug_data["image_size"] = img.size
                except:
                    pass
                with open(analysis_dir / "gpt_view_debug.json", "w", encoding="utf-8") as f:
                    json.dump(debug_data, f, ensure_ascii=False, indent=2)

                # Рисуем картинку с областями, как видит GPT
                try:
                    from PIL import ImageDraw, ImageFont
                    img = Image.open(screenshot_path).convert('RGB')
                    draw = ImageDraw.Draw(img)
                    font = None
                    try:
                        font = ImageFont.truetype("arial.ttf", 18)
                    except:
                        font = ImageFont.load_default()

                    for element in gpt_solution.get("interactive_elements", []):
                        ex = element.get("x", 0)
                        ey = element.get("y", 0)
                        label = element.get("content", "?")
                        eid = element.get("id")
                        draw.ellipse((ex-8, ey-8, ex+8, ey+8), outline="red", width=2)
                        draw.text((ex+10, ey-10), f"#{eid}: {label}", fill="red", font=font)

                    for target in gpt_solution.get("recommendation", {}).get("target_ids", []):
                        for element in gpt_solution.get("interactive_elements", []):
                            if element.get("id") == target:
                                ex = element.get("x", 0)
                                ey = element.get("y", 0)
                                draw.ellipse((ex-15, ey-15, ex+15, ey+15), outline="lime", width=3)

                    img.save(analysis_dir / "gpt_view_overlay.png")
                except Exception as e:
                    print(f"⚠️ Не удалось создать gpt overlay: {e}")
            
            if gpt_solution and "error" not in gpt_solution:
                # Проверяем тип задания ПЕРЕД выполнением
                instruction = gpt_solution.get("instruction", "").lower()
                
                if any(word in instruction for word in ["перетащи", "перетащите", "drag", "перемести"]):
                    print("🚫 Задание на перетаскивание обнаружено - автопропуск")
                    success = click_skip_button_smart(page)
                    if success:
                        print("✅ Задание пропущено автоматически")
                    else:
                        print("⚠️ Не удалось нажать 'Пропустить'")
                else:
                    # Сохраняем GPT анализ
                    gpt_analyzer.save_gpt_analysis(gpt_solution, str(screenshot_path))
                    
                    # Выполняем решение от GPT-4
                    success = execute_gpt_solution_smart(page, gpt_solution, str(screenshot_path), structure_info)
                
                if success:
                    print("🎉 GPT-4 решил капчу!")
                    print("⏳ Ждем результата...")
                    page.wait_for_timeout(5000)
                else:
                    print("⚠️ GPT-4 решение не выполнилось")
            else:
                print("❌ GPT-4 не смог проанализировать")
                if gpt_solution and "raw_response" in gpt_solution:
                    print(f"📄 Ответ GPT-4: {gpt_solution['raw_response'][:100]}...")
                else:
                    print("💡 Возможно проблема с API ключом или лимитами")
                    
        except ImportError:
            print("❌ GPT-4 модуль недоступен. Установите: pip install openai")
        except Exception as gpt_error:
            print(f"❌ Ошибка GPT-4 системы: {gpt_error}")
        
        print("\n✨ Задача выполнена! Нажмите Enter для закрытия браузера...")
        input()  # Ожидаем ввод пользователя
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Убедитесь что server.py запущен на порту 5000")
    finally:
        browser.close()


def capture_captcha():
    """Главная функция для захвата капчи"""
    with sync_playwright() as playwright:
        run_captcha_automation(playwright)


if __name__ == "__main__":
    print("🤖 Автоматический захват hCaptcha + GPT-4 Vision")
    print("📋 Убедитесь что server.py запущен перед началом")
    print("🔑 GPT-4 API ключ захардкожен в gpt_analyzer.py")
    print()
    capture_captcha()
