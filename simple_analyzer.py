#!/usr/bin/env python3
"""
Простой анализатор капч с использованием только OCR.
Fallback вариант если multimodal модели не работают.
"""

from pathlib import Path
from datetime import datetime
import json


def analyze_with_ocr(image_path):
    """Анализирует капчу с помощью OCR"""
    try:
        import easyocr
        import logging
        print("📖 Используем EasyOCR для анализа...")
        
        # Подавляем сообщения EasyOCR о CPU
        logging.getLogger('easyocr.easyocr').setLevel(logging.ERROR)
        
        # Создаем reader (поддерживает русский и английский)
        reader = easyocr.Reader(['ru', 'en'], gpu=False, verbose=False)  # Тихий режим
        
        # Извлекаем текст
        results = reader.readtext(str(image_path))
        
        if not results:
            return "OCR не смог найти текст на изображении капчи."
        
        # Составляем анализ на основе найденного текста
        text_analysis = "АНАЛИЗ КАПЧИ С ПОМОЩЬЮ OCR\n"
        text_analysis += "="*40 + "\n\n"
        
        # Объединяем текстовые фрагменты в полную инструкцию
        all_text = " ".join([result[1] for result in results])
        
        text_analysis += "НАЙДЕННЫЕ ТЕКСТОВЫЕ ФРАГМЕНТЫ:\n"
        for i, (bbox, text, confidence) in enumerate(results, 1):
            text_analysis += f"{i}. {text} (уверенность: {confidence:.2f})\n"
        
        text_analysis += f"\nПОЛНАЯ ИНСТРУКЦИЯ:\n"
        # Очищаем и форматируем полную инструкцию
        clean_instruction = all_text.replace(" :", "").replace(": ", " ").strip()
        text_analysis += f'"{clean_instruction}"\n\n'
        
        # Простая эвристика для определения типа задания
        all_text_lower = all_text.lower()
        
        if any(word in all_text_lower for word in ["выберите", "select", "click", "кликните", "найдите"]):
            task_type = "Задание на выбор объектов"
        elif any(word in all_text_lower for word in ["введите", "enter", "type", "напишите"]):
            task_type = "Текстовая капча"
        elif any(word in all_text_lower for word in ["автомобили", "cars", "светофоры", "traffic", "мосты", "bridges"]):
            task_type = "Визуальный выбор объектов"
        else:
            task_type = "Визуальное задание на выбор"
        
        text_analysis += f"ПРЕДПОЛАГАЕМЫЙ ТИП ЗАДАНИЯ: {task_type}\n\n"
        
        # Рекомендации
        text_analysis += "РЕКОМЕНДАЦИИ ДЛЯ РЕШЕНИЯ:\n"
        
        # Специфичные рекомендации в зависимости от содержимого инструкции
        if any(word in all_text_lower for word in ["лес", "forest", "деревья", "trees"]):
            text_analysis += "ЧТО ИСКАТЬ (лесные предметы):\n"
            text_analysis += "- 🌲 Деревья, ветки, листья, кора\n"
            text_analysis += "- 🍄 Грибы, ягоды, орехи, шишки\n" 
            text_analysis += "- 🦌 Лесные животные (олени, медведи, белки, птицы)\n"
            text_analysis += "- 🪨 Камни, пни, мох, папоротники\n"
            text_analysis += "- 🏕️ Костры, палатки (если в лесу)\n\n"
            text_analysis += "ДЕЙСТВИЕ: Кликните ТОЛЬКО на изображения с этими предметами\n"
            text_analysis += "❌ Если НЕТ подходящих изображений → нажмите 'Пропустить'\n"
            
        elif any(word in all_text_lower for word in ["автомобили", "cars", "машины"]):
            text_analysis += "- Ищите автомобили, машины, грузовики, мотоциклы\n"
            text_analysis += "- Включайте все виды транспортных средств\n"
            text_analysis += "- Кликните на все ячейки с транспортом\n"
            
        elif any(word in all_text_lower for word in ["светофоры", "traffic"]):
            text_analysis += "- Ищите светофоры и дорожные знаки\n" 
            text_analysis += "- Включайте столбы со светофорами\n"
            text_analysis += "- Кликните на все ячейки со светофорами\n"
            
        elif any(word in all_text_lower for word in ["сидеть", "стулья", "chairs"]):
            text_analysis += "- Ищите стулья, кресла, диваны, скамейки\n"
            text_analysis += "- Включайте любые предметы для сидения\n"
            text_analysis += "- Кликните на все ячейки с мебелью для сидения\n"
            
        else:
            text_analysis += "- Внимательно прочитайте инструкцию выше\n"
            text_analysis += "- Найдите изображения, соответствующие описанию\n"
            text_analysis += "- Кликните на все подходящие ячейки\n"
            text_analysis += "- Если подходящих нет → нажмите 'Пропустить'\n"
        
        return text_analysis
        
    except ImportError:
        return "EasyOCR не установлен. Установите: pip install easyocr"
    except Exception as e:
        return f"Ошибка OCR анализа: {e}"


def save_simple_analysis(image_path, analysis_result):
    """Сохраняет простой анализ"""
    try:
        # Создаем папку для решений
        solutions_path = Path("solutions")
        solutions_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Создаем данные для сохранения
        analysis_data = {
            "timestamp": timestamp,
            "image_path": str(image_path),
            "analysis": analysis_result,
            "method": "OCR_fallback"
        }
        
        # Сохраняем в файлы
        json_path = solutions_path / "analysis.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        txt_path = solutions_path / "solution.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"АНАЛИЗ КАПЧИ (OCR РЕЖИМ)\n")
            f.write(f"{'='*50}\n")
            f.write(f"Время: {timestamp}\n")
            f.write(f"Изображение: {image_path}\n")
            f.write(f"{'='*50}\n\n")
            f.write(analysis_result)
        
        print(f"💾 OCR анализ сохранен:")
        print(f"   📋 JSON: {json_path}")
        print(f"   📄 TXT:  {txt_path}")
        
        return str(txt_path)
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Использование: python simple_analyzer.py <путь_к_изображению>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"❌ Файл не найден: {image_path}")
        sys.exit(1)
        
    print(f"🔍 Простой анализ капчи: {image_path}")
    result = analyze_with_ocr(image_path)
    
    if result:
        solution_path = save_simple_analysis(image_path, result)
        print(f"✅ Анализ завершен! Результат: {solution_path}")
    else:
        print("❌ Анализ не удался")
