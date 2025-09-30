#!/usr/bin/env python3
"""
Утилита для очистки старых файлов анализа.
Удаляет файлы с timestamp и оставляет только фиксированные.
"""

import os
import glob
from pathlib import Path


def cleanup_analysis_folder():
    """Очищает папку analysis от старых файлов с timestamp"""
    analysis_dir = Path("analysis")
    
    if not analysis_dir.exists():
        print("📁 Папка analysis не найдена")
        return
        
    # Паттерны старых файлов
    patterns = [
        "captcha_*.png",
        "main_page_*.html", 
        "challenge_frame_*.html",
        "selectors_*.txt"
    ]
    
    removed_count = 0
    
    for pattern in patterns:
        files = list(analysis_dir.glob(pattern))
        for file in files:
            try:
                file.unlink()
                print(f"🗑️ Удален: {file.name}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Не удалось удалить {file.name}: {e}")
    
    print(f"\n✅ Очистка завершена! Удалено файлов: {removed_count}")
    
    # Проверяем что осталось
    remaining = list(analysis_dir.glob("*"))
    if remaining:
        print(f"📋 Остались файлы:")
        for file in remaining:
            print(f"   - {file.name}")
    else:
        print("📋 Папка analysis пуста")


def cleanup_solutions_folder():
    """Очищает папку solutions от старых файлов с timestamp"""
    solutions_dir = Path("solutions")
    
    if not solutions_dir.exists():
        print("📁 Папка solutions не найдена")
        return
        
    # Паттерны старых файлов
    patterns = [
        "analysis_*.json",
        "solution_*.txt"
    ]
    
    removed_count = 0
    
    for pattern in patterns:
        files = list(solutions_dir.glob(pattern))
        for file in files:
            try:
                file.unlink()
                print(f"🗑️ Удален: {file.name}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Не удалось удалить {file.name}: {e}")
    
    print(f"\n✅ Очистка solutions завершена! Удалено файлов: {removed_count}")
    
    # Проверяем что осталось
    remaining = list(solutions_dir.glob("*"))
    if remaining:
        print(f"📋 Остались файлы:")
        for file in remaining:
            print(f"   - {file.name}")
    else:
        print("📋 Папка solutions пуста")


if __name__ == "__main__":
    print("🧹 Очистка старых файлов анализа...")
    print("="*40)
    
    cleanup_analysis_folder()
    print()
    cleanup_solutions_folder()
    
    print("\n✨ Очистка завершена!")
