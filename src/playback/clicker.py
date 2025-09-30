#!/usr/bin/env python3
"""
Модуль автоматических кликов по капче.
Анализирует каждую ячейку и кликает по правильным.
"""

import json
from pathlib import Path
from PIL import Image
import numpy as np


class CaptchaClicker:
    """Класс для автоматического решения капч кликами"""
    
    def __init__(self):
        self.grid_size = 3  # Стандартная сетка 3x3
        self.cell_predictions = []
        
    def find_task_grid_area(self, image):
        """Находит область с основной сеткой задания, исключая примеры"""
        width, height = image.size
        img_array = np.array(image)
        
        # Конвертируем в оттенки серого для анализа
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
            
        # Ищем горизонтальные разделители (линии между рядами)
        horizontal_edges = []
        
        # Проверяем каждую строку на наличие "разделительных" пикселей
        for y in range(height):
            row = gray[y, :]
            # Ищем области с низкой вариацией (фон, разделители)
            if np.std(row) < 20:  # Низкое отклонение = однородная область
                horizontal_edges.append(y)
        
        # Группируем соседние разделители
        edge_groups = []
        current_group = []
        
        for edge in horizontal_edges:
            if not current_group or edge - current_group[-1] <= 5:
                current_group.append(edge)
            else:
                if len(current_group) > 3:  # Значимая группа
                    edge_groups.append((min(current_group), max(current_group)))
                current_group = [edge]
        
        if current_group and len(current_group) > 3:
            edge_groups.append((min(current_group), max(current_group)))
        
        # Определяем области между разделителями
        if len(edge_groups) >= 2:
            # Вероятно есть примеры сверху и сетка снизу
            examples_end = edge_groups[0][1]  # Конец области примеров
            task_start = edge_groups[1][0]    # Начало основной сетки
            
            # Основная сетка - это нижняя часть изображения
            task_top = max(examples_end + 10, height // 3)  # Не выше 1/3 изображения
            task_bottom = height - 10  # Немного отступа снизу
            
            print(f"🔍 Обнаружена структура с примерами")
            print(f"   Примеры: 0-{examples_end}px")
            print(f"   Основная сетка: {task_top}-{task_bottom}px")
            
            return 0, task_top, width, task_bottom
        
        else:
            # Простая сетка без примеров - используем всю область
            print("🔍 Простая сетка без примеров сверху")
            return 0, height // 4, width, height  # Отступ сверху для текста

    def split_captcha_image(self, image_path):
        """Разделяет изображение капчи на отдельные ячейки с умным определением сетки"""
        try:
            image = Image.open(image_path)
            width, height = image.size
            
            print(f"📐 Размер исходного изображения: {width}x{height}")
            
            # Находим область основной сетки
            grid_left, grid_top, grid_right, grid_bottom = self.find_task_grid_area(image)
            
            # Вырезаем область основной сетки
            task_area = image.crop((grid_left, grid_top, grid_right, grid_bottom))
            task_width = grid_right - grid_left
            task_height = grid_bottom - grid_top
            
            print(f"📊 Область основной сетки: {task_width}x{task_height}")
            
            # Определяем размеры ячейки в рабочей области
            cell_width = task_width // self.grid_size
            cell_height = task_height // self.grid_size
            
            print(f"🔢 Размер ячейки: {cell_width}x{cell_height}")
            
            cells = []
            cell_positions = []
            
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    # Координаты ячейки в рабочей области
                    left = col * cell_width
                    top = row * cell_height
                    right = left + cell_width  
                    bottom = top + cell_height
                    
                    # Вырезаем ячейку из рабочей области
                    cell = task_area.crop((left, top, right, bottom))
                    cells.append(cell)
                    
                    # Координаты для кликов в исходном изображении
                    center_x = grid_left + left + cell_width // 2
                    center_y = grid_top + top + cell_height // 2
                    cell_positions.append((center_x, center_y))
            
            # Сохраняем области для отладки
            cells_dir = Path("analysis/cells")
            cells_dir.mkdir(exist_ok=True)
            
            # Сохраняем исходную рабочую область
            task_area.save(cells_dir / "task_area.png")
            
            for i, cell in enumerate(cells):
                cell.save(cells_dir / f"cell_{i}.png")
            
            print(f"📊 Изображение разделено на {len(cells)} ячеек")
            print(f"🔍 Ячейки сохранены в: {cells_dir}")
            
            return cells, cell_positions
            
        except Exception as e:
            print(f"❌ Ошибка разделения изображения: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def analyze_cell_content_smart(self, cell_image, cell_index, instruction):
        """Умный анализ содержимого ячейки с помощью CLIP"""
        try:
            # Пробуем использовать CLIP для умного анализа
            try:
                from smart_detector import SmartDetector
                
                if not hasattr(self, '_smart_detector'):
                    self._smart_detector = SmartDetector()
                    self._smart_detector.load_clip_model()
                
                # Анализируем ячейку с помощью CLIP
                score, best_object = self._smart_detector.analyze_cell_with_clip(cell_image, instruction)
                
                return {
                    "index": cell_index,
                    "clip_score": score,
                    "detected_object": best_object,
                    "method": "CLIP_analysis"
                }
                
            except ImportError:
                print(f"⚠️ CLIP недоступен для ячейки {cell_index}, используем базовый анализ")
                # Fallback к базовому анализу
                return self.analyze_cell_content_basic(cell_image, cell_index)
                
        except Exception as e:
            print(f"❌ Ошибка умного анализа ячейки {cell_index}: {e}")
            return {"index": cell_index, "error": str(e)}
    
    def analyze_cell_content_basic(self, cell_image, cell_index):
        """Базовый анализ содержимого ячейки (fallback)"""
        try:
            # Анализ цветов (базовый)
            img_array = np.array(cell_image)
            
            # Средние цвета RGB
            avg_colors = np.mean(img_array, axis=(0, 1))
            
            # Определяем доминирующие цвета
            is_mostly_brown = avg_colors[0] > 100 and avg_colors[1] > 80 and avg_colors[2] < 100  # Коричневый (дерево)
            is_mostly_gray = np.std(avg_colors) < 30  # Серый (металл/бетон)
            is_mostly_green = avg_colors[1] > max(avg_colors[0], avg_colors[2])  # Зеленый (растения)
            is_mostly_blue = avg_colors[2] > max(avg_colors[0], avg_colors[1])  # Синий (вода)
            
            # Собираем признаки ячейки
            cell_features = {
                "index": cell_index,
                "colors": {
                    "avg_rgb": avg_colors.tolist(),
                    "is_brown": is_mostly_brown,
                    "is_gray": is_mostly_gray, 
                    "is_green": is_mostly_green,
                    "is_blue": is_mostly_blue
                },
                "method": "basic_colors"
            }
            
            return cell_features
            
        except Exception as e:
            print(f"❌ Ошибка базового анализа ячейки {cell_index}: {e}")
            return {"index": cell_index, "error": str(e)}
    
    def match_instruction_to_cells_smart(self, instruction, cell_features_list, threshold=0.25):
        """Умное сопоставление инструкции с содержимым ячеек на основе CLIP анализа"""
        matching_cells = []
        
        print(f"🧠 Умное сопоставление для: '{instruction}'")
        print(f"⚡ Порог уверенности CLIP: {threshold}")
        
        for cell_features in cell_features_list:
            cell_index = cell_features["index"]
            
            # Приоритет для CLIP анализа
            if cell_features.get("method") == "CLIP_analysis":
                clip_score = cell_features.get("clip_score", 0.0)
                detected_object = cell_features.get("detected_object", "неизвестно")
                
                if clip_score > threshold:
                    matching_cells.append({
                        "index": cell_index,
                        "score": clip_score,
                        "reasons": [f"CLIP: {detected_object} ({clip_score:.3f})"]
                    })
                    print(f"✅ Ячейка {cell_index}: {detected_object} (CLIP score: {clip_score:.3f})")
                else:
                    print(f"   Ячейка {cell_index}: {detected_object} (слишком низкий score: {clip_score:.3f})")
            
            # Fallback к базовому анализу
            elif cell_features.get("method") == "basic_colors":
                matches = False
                reasons = []
                instruction_lower = instruction.lower()
                
                # Базовый анализ по цветам
                colors = cell_features.get("colors", {})
                
                if any(word in instruction_lower for word in ["сидеть", "стул", "chair", "кресло", "диван"]):
                    if colors.get("is_brown", False):
                        matches = True
                        reasons.append("коричневый цвет (мебель)")
                        
                elif any(word in instruction_lower for word in ["автомобил", "машин", "car", "транспорт"]):
                    if colors.get("is_gray", False):
                        matches = True
                        reasons.append("серый цвет (металл)")
                        
                elif any(word in instruction_lower for word in ["лес", "дерев", "forest", "tree"]):
                    if colors.get("is_green", False) or colors.get("is_brown", False):
                        matches = True
                        reasons.append("зеленый/коричневый (природа)")
                        
                elif any(word in instruction_lower for word in ["океан", "море", "вода", "water"]):
                    if colors.get("is_blue", False):
                        matches = True
                        reasons.append("синий цвет (вода)")
                
                if matches:
                    matching_cells.append({
                        "index": cell_index,
                        "score": 0.6,  # Базовый score для цветового анализа
                        "reasons": reasons
                    })
                    print(f"✅ Ячейка {cell_index} (базовый): {', '.join(reasons)}")
        
        return matching_cells
    
    def plan_clicks(self, image_path, instruction):
        """Планирует какие ячейки нужно кликнуть с умным анализом"""
        print(f"\n🧠 Планируем умные клики для инструкции: '{instruction}'")
        
        # Разделяем изображение на ячейки
        cells, positions = self.split_captcha_image(image_path)
        
        if not cells:
            return [], []
        
        # Анализируем каждую ячейку с умным детектором
        print("🔍 Умный анализ содержимого ячеек...")
        cell_features_list = []
        
        for i, cell in enumerate(cells):
            # Используем умный анализ с CLIP
            features = self.analyze_cell_content_smart(cell, i, instruction)
            cell_features_list.append(features)
            
            # Показываем прогресс
            if features.get("method") == "CLIP_analysis":
                obj = features.get("detected_object", "?")
                score = features.get("clip_score", 0.0)
                print(f"   Ячейка {i}: {obj} (CLIP: {score:.3f})")
            else:
                print(f"   Ячейка {i}: обработана (базовый анализ)")
        
        # Умное сопоставление с инструкцией (снижаем порог для лучших результатов)
        matching_cells = self.match_instruction_to_cells_smart(instruction, cell_features_list, threshold=0.22)
        
        # Определяем координаты для кликов (сортируем по score)
        click_positions = []
        click_indices = []
        
        # Сортируем по убыванию score для лучших результатов первыми
        matching_cells.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        for match in matching_cells:
            cell_index = match["index"]
            click_indices.append(cell_index)
            click_positions.append(positions[cell_index])
        
        print(f"\n🎯 Найдено {len(matching_cells)} подходящих ячеек: {click_indices}")
        if matching_cells:
            for match in matching_cells:
                reasons = ", ".join(match.get("reasons", []))
                print(f"   → Ячейка {match['index']}: {reasons}")
        
        return click_positions, click_indices
    
    def execute_clicks(self, page, click_positions, click_indices):
        """Выполняет клики в браузере через Playwright"""
        try:
            # Сначала находим iframe с заданием
            print("🔍 Ищем iframe с заданием капчи...")
            challenge_frame = None
            frames = page.frames
            
            for frame in frames:
                try:
                    frame_title = frame.title()
                    if 'содержание испытания' in frame_title or 'hCaptcha challenge' in frame_title or 'challenge' in frame.url:
                        challenge_frame = frame
                        print(f"✅ Найден iframe: {frame_title}")
                        break
                except Exception as e:
                    continue
            
            if not challenge_frame:
                print("❌ Не найден iframe с заданием")
                print("💡 Доступные iframe:")
                for i, frame in enumerate(frames):
                    try:
                        print(f"   {i}: {frame.title()} - {frame.url}")
                    except:
                        print(f"   {i}: [iframe без доступа]")
                return False
            
            if not click_positions:
                print("❌ Нет ячеек для клика, нажимаем 'Пропустить'")
                
                # Ищем кнопку "Пропустить" ВНУТРИ iframe
                skip_selectors = [
                    "text=Пропустить",
                    "text=Skip", 
                    ".refresh-button",
                    "[data-key='skip']",
                    "button:has-text('Пропустить')",
                    "a:has-text('Пропустить')",
                    ".challenge-refresh",
                    ".refresh"
                ]
                
                print("🔍 Ищем кнопку 'Пропустить' в iframe...")
                found_skip = False
                
                for selector in skip_selectors:
                    try:
                        print(f"   Пробуем селектор в iframe: {selector}")
                        challenge_frame.locator(selector).click(timeout=3000)
                        print("✅ Нажали 'Пропустить' в iframe")
                        found_skip = True
                        break
                    except Exception as e:
                        print(f"   ❌ Не сработал: {str(e)[:100]}...")
                        continue
                
                if not found_skip:
                    print("⚠️ Кнопка 'Пропустить' не найдена в iframe")
                    print("💡 Попробуйте нажать 'Пропустить' вручную в браузере")
                    return False
                    
                return True
            
            print(f"🖱️ Выполняем клики по {len(click_positions)} ячейкам...")
            
            for i, (x, y) in enumerate(click_positions):
                cell_index = click_indices[i]
                print(f"   Кликаем ячейку {cell_index} в позиции ({x}, {y})")
                
                # Кликаем по координатам ВНУТРИ iframe
                challenge_frame.click('body', position={'x': x, 'y': y})
                
                # Небольшая пауза между кликами
                page.wait_for_timeout(500)
            
            # Ждем немного и ищем кнопку подтверждения ВНУТРИ iframe
            page.wait_for_timeout(1000)
            
            # Пробуем найти кнопку "Проверить" в iframe
            try:
                verify_selectors = [
                    "text=Проверить",
                    "text=Verify", 
                    "text=Submit",
                    "[data-key='verify']",
                    "button[type='submit']",
                    ".verify-button",
                    ".submit-button"
                ]
                
                print("🔍 Ищем кнопку подтверждения в iframe...")
                found_verify = False
                
                for selector in verify_selectors:
                    try:
                        challenge_frame.locator(selector).click(timeout=2000)
                        print("✅ Нажали кнопку подтверждения в iframe")
                        found_verify = True
                        break
                    except:
                        continue
                
                if not found_verify:
                    print("⚠️ Кнопка подтверждения не найдена, но клики выполнены")
                
                return True
                
            except Exception as e:
                print(f"⚠️ Ошибка поиска кнопки подтверждения: {e}")
                return True  # Клики выполнены, это главное
                
        except Exception as e:
            print(f"❌ Ошибка выполнения кликов: {e}")
            return False


def auto_solve_captcha(page, image_path, instruction):
    """Автоматически решает капчу"""
    clicker = CaptchaClicker()
    
    # Планируем клики
    click_positions, click_indices = clicker.plan_clicks(image_path, instruction)
    
    # Выполняем клики
    success = clicker.execute_clicks(page, click_positions, click_indices)
    
    if success:
        print("🎉 Капча решена автоматически!")
    else:
        print("⚠️ Не удалось решить капчу автоматически")
    
    return success


if __name__ == "__main__":
    # Тестовый режим с умным анализом
    print("🧠 Тестирование умного кликера капч")
    print("="*50)
    
    clicker = CaptchaClicker()
    
    test_image = "analysis/captcha.png"
    test_instruction = "Выберите то, на чём можно сидеть"
    
    if Path(test_image).exists():
        print(f"📸 Анализируем: {test_image}")
        print(f"📋 Инструкция: {test_instruction}")
        print()
        
        positions, indices = clicker.plan_clicks(test_image, test_instruction)
        
        print("\n" + "="*50)
        print("📊 РЕЗУЛЬТАТ УМНОГО АНАЛИЗА:")
        
        if positions:
            print(f"🎯 Рекомендация: КЛИКНУТЬ на ячейки {indices}")
            print(f"🖱️ Координаты кликов: {positions}")
        else:
            print("🎯 Рекомендация: НАЖАТЬ 'Пропустить'")
            print("❌ Подходящих объектов не найдено")
        
    else:
        print(f"❌ Тестовое изображение не найдено: {test_image}")
        print("💡 Сначала запустите capture.py для создания скриншота")
