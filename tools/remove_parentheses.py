#!/usr/bin/env python3
"""
أداة لحذف جميع الأقواس () والمحتوى بداخلها (مثل التوقيتات أو الملاحظات) من ملف نصي.
"""
import re
import sys
import os

def remove_parentheses(text: str) -> str:
    """
    يحذف كل الأقواس () وما بداخلها من النص مع تنظيف المسافات الزائدة الناتجة عن الحذف.
    """
    # 1. إزالة الأقواس وما بداخلها (أي نص بين قوسين)
    # [^)]* تعني أي شيء ليس قوس إغلاق
    cleaned = re.sub(r'\s*\([^)]*\)\s*', ' ', text)
    
    # 2. تنظيف المسافات في بداية ونهاية كل سطر وتعديل المسافات المزدوجة
    cleaned_lines = []
    for line in cleaned.splitlines():
        line = re.sub(r' +', ' ', line).strip()
        if line:
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

def process_file(file_path: str, output_path: str = None):
    """
    يقرأ الملف ويحذف الأقواس ومحتواها ثم يحفظ النتيجة.
    """
    if not os.path.exists(file_path):
        print(f"الملف غير موجود: {file_path}")
        return

    # قراءة الملف بترميز UTF-8
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # معالجة النص
    result = remove_parentheses(content)

    target_file = output_path or file_path
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"تمت العملية بنجاح! تم حفظ الملف المعدل في:\n{target_file}")

if __name__ == "__main__":
    # المسار الافتراضي لملف النص
    default_file = os.path.join(
        os.path.dirname(__file__), "..", "project_content", "transcript_to_speech.txt"
    )
    
    file_to_clean = sys.argv[1] if len(sys.argv) > 1 else default_file
    process_file(file_to_clean)
