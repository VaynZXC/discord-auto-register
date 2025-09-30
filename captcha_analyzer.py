#!/usr/bin/env python3
"""
Универсальный анализатор капч с использованием multimodal моделей.
Анализирует любые типы заданий hCaptcha и дает текстовое описание решения.
"""

import torch
from PIL import Image
from pathlib import Path
import json
from datetime import datetime


class CaptchaAnalyzer:
    """Универсальный анализатор капч с multimodal моделью"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = None
        self.model = None
        self.model_loaded = False
        
        print(f"🤖 Инициализация анализатора капч на {self.device}")
        
    def load_model(self, model_name="Salesforce/blip2-opt-2.7b"):
        """Загружает multimodal модель для анализа"""
        try:
            print(f"📦 Загрузка модели {model_name}...")
            
            # Определяем тип модели и выбираем соответствующий класс
            if "blip2" in model_name.lower():
                from transformers import AutoProcessor, Blip2ForConditionalGeneration
                model_class = Blip2ForConditionalGeneration
            elif "llava" in model_name.lower():
                from transformers import AutoProcessor, LlavaForConditionalGeneration  
                model_class = LlavaForConditionalGeneration
            elif "kosmos" in model_name.lower():
                from transformers import AutoProcessor, Kosmos2ForConditionalGeneration
                model_class = Kosmos2ForConditionalGeneration
            else:
                # По умолчанию пробуем универсальный подход
                from transformers import AutoProcessor, AutoModelForVision2Seq
                model_class = AutoModelForVision2Seq
            
            # Загружаем процессор
            self.processor = AutoProcessor.from_pretrained(model_name)
            
            # Используем облегченную конфигурацию для CPU/GPU
            model_kwargs = {
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            # Для GPU добавляем device_map
            if self.device == "cuda":
                model_kwargs["device_map"] = "auto"
                
                # Пробуем добавить квантизацию для экономии памяти
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16
                    )
                    model_kwargs["quantization_config"] = quantization_config
                    print("🔧 Используем 4-bit квантизацию")
                except ImportError:
                    print("⚠️ BitsAndBytesConfig недоступен, используем float16")
            
            # Загружаем модель
            self.model = model_class.from_pretrained(model_name, **model_kwargs)
            
            # Для CPU явно перемещаем модель
            if self.device == "cpu":
                self.model = self.model.to("cpu")
            
            self.model_loaded = True
            print("✅ Модель загружена успешно!")
            
        except ImportError as e:
            print(f"❌ Ошибка импорта: {e}")
            print("💡 Попробуйте: pip install transformers[torch] accelerate")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return False
            
        return True
        
    def analyze_captcha(self, image_path, prompt=None):
        """Анализирует капчу и возвращает решение"""
        if not self.model_loaded:
            print("❌ Модель не загружена!")
            return None
            
        try:
            # Загружаем изображение
            image = Image.open(image_path)
            
            # Получаем имя модели для адаптации промпта
            model_name = getattr(self.model, 'name_or_path', 'unknown')
            
            # Создаем промпт для анализа
            if prompt is None:
                prompt = self._create_analysis_prompt(model_name)
            
            # Подготавливаем промпт в зависимости от типа модели
            
            if "blip2" in model_name.lower():
                # BLIP2 использует простые промпты
                full_prompt = f"Describe this captcha challenge: {prompt}"
                inputs = self.processor(images=image, text=full_prompt, return_tensors="pt").to(self.device)
                
            elif "kosmos" in model_name.lower():
                # Kosmos-2 использует формат <image> + текст
                full_prompt = f"<image> {prompt}"
                inputs = self.processor(text=full_prompt, images=image, return_tensors="pt").to(self.device)
                
            else:
                # LLaVA и другие модели
                full_prompt = f"USER: <image>\n{prompt}\nASSISTANT:"
                inputs = self.processor(full_prompt, images=image, return_tensors="pt").to(self.device)
            
            print("🧠 Анализируем капчу...")
            
            # Генерируем ответ с адаптированными параметрами
            with torch.no_grad():
                if "blip2" in model_name.lower():
                    # BLIP2 требует особые параметры генерации
                    output = self.model.generate(
                        **inputs,
                        max_length=512,
                        num_beams=4,
                        early_stopping=True,
                        do_sample=False
                    )
                else:
                    # Для других моделей
                    output = self.model.generate(
                        **inputs,
                        max_new_tokens=512,
                        do_sample=True,
                        temperature=0.1,
                        top_p=0.9,
                        pad_token_id=self.processor.tokenizer.pad_token_id if hasattr(self.processor, 'tokenizer') else None
                    )
            
            # Декодируем результат
            generated_text = self.processor.decode(output[0], skip_special_tokens=True)
            
            print(f"🔍 Сгенерированный текст: {generated_text[:200]}...")
            
            # Извлекаем ответ в зависимости от типа модели
            if "blip2" in model_name.lower():
                # BLIP2 сразу генерирует ответ
                response = generated_text.strip()
                # Убираем промпт если он остался в начале
                if full_prompt in response:
                    response = response.replace(full_prompt, "").strip()
                    
            elif "kosmos" in model_name.lower():
                # Kosmos-2 генерирует после промпта
                response = generated_text.split(full_prompt)[-1].strip() if full_prompt in generated_text else generated_text.strip()
                
            else:
                # LLaVA - ищем ответ после ASSISTANT:
                if "ASSISTANT:" in generated_text:
                    response = generated_text.split("ASSISTANT:")[-1].strip()
                else:
                    response = generated_text.split(full_prompt)[-1].strip() if full_prompt in generated_text else generated_text.strip()
            
            # Очищаем ответ от артефактов
            response = response.replace("<|endoftext|>", "").strip()
            
            # Проверяем что ответ не пустой и не является промптом
            if not response or response == full_prompt or len(response) < 10:
                print("⚠️ Модель не сгенерировала корректный ответ")
                response = f"Модель {model_name} не смогла проанализировать изображение. Полный вывод: {generated_text}"
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")
            return None
    
    def _create_analysis_prompt(self, model_name=""):
        """Создает промпт для анализа капчи в зависимости от модели"""
        if "blip2" in model_name.lower():
            # Короткий промпт для BLIP2
            return """Analyze this captcha challenge. Describe:
- TYPE: what kind of task is this?
- INSTRUCTION: what text instruction is given?
- OBJECTS: what objects do you see?
- SOLUTION: how to solve this captcha?"""
        
        else:
            # Полный промпт для других моделей
            return """Ты эксперт по решению капч. Проанализируй это изображение капчи и ответь на следующие вопросы:

1. Какой тип задания ты видишь? (выбор изображений, текстовая капча, движущиеся объекты, математика, и т.д.)

2. Какая инструкция дана пользователю? (если есть текст инструкции)

3. Что нужно сделать для решения этой капчи?

4. Какие объекты или элементы ты видишь на изображении?

5. Дай подробное описание решения в формате:
   - ТИП: [тип капчи]
   - ИНСТРУКЦИЯ: [что написано в задании]
   - РЕШЕНИЕ: [пошаговое описание что нужно делать]
   - ОБЪЕКТЫ: [список найденных объектов]

Будь максимально точным и подробным в описании."""

    def save_analysis(self, image_path, analysis_result, solutions_dir="solutions"):
        """Сохраняет результат анализа в файл"""
        try:
            # Создаем папку для решений
            solutions_path = Path(solutions_dir)
            solutions_path.mkdir(exist_ok=True)
            
            # Используем фиксированные имена файлов (заменяются при каждом запуске)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Создаем данные для сохранения
            analysis_data = {
                "timestamp": timestamp,
                "image_path": str(image_path),
                "analysis": analysis_result,
                "model_info": {
                    "device": self.device,
                    "model_loaded": self.model_loaded
                }
            }
            
            # Сохраняем в фиксированные файлы
            json_path = solutions_path / "analysis.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            # Сохраняем в текстовый файл для удобства чтения
            txt_path = solutions_path / "solution.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"АНАЛИЗ КАПЧИ\n")
                f.write(f"{'='*50}\n")
                f.write(f"Время: {timestamp}\n")
                f.write(f"Изображение: {image_path}\n")
                f.write(f"{'='*50}\n\n")
                f.write(analysis_result)
            
            print(f"💾 Анализ сохранен:")
            print(f"   📋 JSON: {json_path}")
            print(f"   📄 TXT:  {txt_path}")
            
            return str(txt_path)
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return None


def analyze_captcha_image(image_path):
    """Удобная функция для анализа одного изображения"""
    analyzer = CaptchaAnalyzer()
    
    # Пробуем загрузить модели по порядку (от простых к сложным)
    models_to_try = [
        "Salesforce/blip2-opt-2.7b",           # Самая легкая модель
        "llava-hf/llava-1.5-7b-hf",           # Основная модель  
        "microsoft/kosmos-2-patch14-224"       # Резервная модель
    ]
    
    model_loaded = False
    for model_name in models_to_try:
        print(f"🔄 Пробуем модель: {model_name}")
        if analyzer.load_model(model_name):
            model_loaded = True
            break
        print(f"⚠️ Не удалось загрузить {model_name}, пробуем следующую...")
    
    if not model_loaded:
        print("❌ Не удалось загрузить ни одну модель!")
        return None
        
    # Анализируем изображение
    result = analyzer.analyze_captcha(image_path)
    
    if result:
        # Сохраняем результат
        solution_path = analyzer.save_analysis(image_path, result)
        return solution_path
    
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Использование: python captcha_analyzer.py <путь_к_изображению>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"❌ Файл не найден: {image_path}")
        sys.exit(1)
        
    print(f"🔍 Анализируем капчу: {image_path}")
    result = analyze_captcha_image(image_path)
    
    if result:
        print(f"✅ Анализ завершен! Результат сохранен в: {result}")
    else:
        print("❌ Анализ не удался")
