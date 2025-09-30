#!/usr/bin/env python3
"""
Модуль для автоматического решения капч через браузерную автоматизацию.
Делает скриншоты заданий hCaptcha для дальнейшей обработки нейросетями.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright


def capture_captcha():
    """Главная функция для захвата капчи"""
    with sync_playwright() as playwright:
        run_captcha_automation(playwright)


def run_captcha_automation(playwright: Playwright):
    """Запускает автоматизацию для захвата капчи"""
    # Запускаем браузер в видимом режиме (без headless)
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    
    try:
        # Создаем новую страницу
        page = browser.new_page()
        
        print("🌐 Переходим на тестовую страницу...")
        page.goto("http://127.0.0.1:5000", wait_until="load")
        
        print("🔍 Ищем чекбокс hCaptcha...")
        # Ждем появления iframe с чекбоксом hCaptcha (первый iframe с флажком)
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
        
        print("📷 Делаем скриншот капчи...")
        # Создаем папку для анализа
        analysis_dir = Path("analysis")
        analysis_dir.mkdir(exist_ok=True)
        
        # Сохраняем скриншот (один файл, заменяется)
        challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')
        screenshot_path = analysis_dir / "captcha.png"
        challenge_frame.locator('body').screenshot(path=str(screenshot_path))
        print(f"📸 Скриншот: {screenshot_path}")
        
        # Быстрый анализ DOM структуры  
        try:
            # Получаем frame object
            challenge_frames = page.frames
            challenge_frame_obj = None
            for frame in challenge_frames:
                if 'содержание испытания' in frame.title() or 'hCaptcha challenge' in frame.title():
                    challenge_frame_obj = frame
                    break
                    
            if challenge_frame_obj:
                print("🔍 Быстрый анализ DOM:")
                
                # Ищем элементы инструкций
                try:
                    instructions = challenge_frame_obj.locator('.prompt-text, .challenge-prompt, [class*="prompt"]').all()
                    if instructions:
                        for i, instruction in enumerate(instructions):
                            text = instruction.inner_text()
                            print(f"  📝 Инструкция {i+1}: {text}")
                except:
                    pass
                
                # Ищем ячейки
                try:
                    cells = challenge_frame_obj.locator('[class*="cell"], [class*="tile"], .task-image').all()
                    if cells:
                        print(f"  📦 Найдено ячеек: {len(cells)}")
                except:
                    pass
                
            else:
                print("⚠️ Не удалось найти iframe с заданием")
                
        except Exception as e:
            print(f"⚠️ Ошибка при анализе iframe: {e}")
        
        print(f"\n✅ Скриншот сохранен в: {screenshot_path}")
        
        # Анализируем капчу с помощью ИИ
        # Анализируем капчу ТОЛЬКО через GPT-4 Vision
        print("\n🤖 GPT-4 Vision анализ...")
        solution_path = None
        
        try:
            from captcha_analyzer import analyze_captcha_image
            solution_path = analyze_captcha_image(str(screenshot_path))
            
            if solution_path:
                # Проверяем что решение содержит реальный анализ, а не ошибку
                try:
                    with open(solution_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if "не смогла проанализировать" in content or len(content) < 100:
                        print("⚠️ ИИ дал неполный ответ, пробуем OCR...")
                        raise Exception("ИИ модель дала неполный ответ")
                    else:
                        print(f"🧠 ИИ анализ завершен! Решение сохранено: {solution_path}")
                except:
                    print("⚠️ Ошибка чтения решения, пробуем OCR...")
                    raise Exception("Ошибка чтения решения")
            else:
                print("⚠️ ИИ анализ не удался, пробуем OCR...")
                raise Exception("ИИ модель не сработала")
                
        except Exception as e:
            print(f"⚠️ Ошибка ИИ анализа: {e}")
            
            # Fallback к простому OCR анализу
            print("\n📖 Пробуем простой OCR анализ...")
            try:
                from simple_analyzer import analyze_with_ocr, save_simple_analysis
                
                ocr_result = analyze_with_ocr(str(screenshot_path))
                if ocr_result and "ошибка" not in ocr_result.lower():
                    solution_path = save_simple_analysis(str(screenshot_path), ocr_result)
                    print(f"📝 OCR анализ завершен! Решение сохранено: {solution_path}")
                else:
                    print(f"⚠️ OCR анализ тоже не удался: {ocr_result}")
                    
            except ImportError:
                print("❌ EasyOCR не установлен. Установите: pip install easyocr")
            except Exception as ocr_error:
                print(f"❌ Ошибка OCR анализа: {ocr_error}")
        
        # Если есть анализ, пробуем автоматически решить капчу
        if solution_path:
            print("\n🤖 Пробуем автоматически решить капчу...")
            try:
                from captcha_clicker import auto_solve_captcha
                import json
                
                # Читаем анализ и извлекаем инструкцию
                analysis_json_path = Path("solutions/analysis.json")
                if analysis_json_path.exists():
                    with open(analysis_json_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    # Пытаемся извлечь инструкцию из анализа
                    analysis_text = analysis_data.get('analysis', '')
                    
                    # Ищем строку с инструкцией
                    instruction = None
                    for line in analysis_text.split('\n'):
                        if 'ПОЛНАЯ ИНСТРУКЦИЯ:' in line:
                            # Следующая строка после "ПОЛНАЯ ИНСТРУКЦИЯ:"
                            instruction_line = analysis_text.split('ПОЛНАЯ ИНСТРУКЦИЯ:')[1].split('\n')[1]
                            # Убираем кавычки и лишний текст
                            instruction = instruction_line.strip().strip('"')
                            # Убираем "С Пропустить" и подобные артефакты
                            instruction = instruction.replace(' С Пропустить', '').replace(' Пропустить', '').strip()
                            break
                    
                    if not instruction:
                        # Fallback - ищем первую значимую инструкцию
                        lines = analysis_text.split('\n')
                        for line in lines:
                            if any(word in line.lower() for word in ['выберите', 'найдите', 'select', 'choose']):
                                instruction = line.split('(уверенность')[0].strip()
                                if instruction.endswith('.'):
                                    instruction = instruction[:-1]
                                break
                    
                    if instruction and len(instruction) > 10:
                        print(f"📋 Инструкция: {instruction}")
                        
                        # Автоматически решаем капчу
                        success = auto_solve_captcha(page, str(screenshot_path), instruction)
                        
                        if success:
                            print("🎉 Капча решена автоматически!")
                            print("⏳ Ждем результата...")
                            page.wait_for_timeout(5000)  # Ждем обработки
                        else:
                            print("⚠️ Автоматическое решение не удалось")
                    else:
                        print("⚠️ Не удалось извлечь инструкцию для автокликов")
                else:
                    print("⚠️ Файл анализа не найден")
                    
            except ImportError:
                print("⚠️ Модуль автокликов недоступен")
            except Exception as e:
                print(f"⚠️ Ошибка автоматического решения: {e}")
        
        if not solution_path:
            print("💡 Попробуйте установить зависимости: pip install -r requirements.txt")
        
        print("\n✨ Задача выполнена! Нажмите Enter для закрытия браузера...")
        input()  # Ожидаем ввод пользователя
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Убедитесь что server.py запущен на порту 5000")
    finally:
        browser.close()


if __name__ == "__main__":
    print("🤖 Автоматический захват hCaptcha")
    print("📋 Убедитесь что server.py запущен перед началом")
    print()
    capture_captcha()
