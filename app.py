import streamlit as st
from docx import Document
from docx.shared import Pt  # هذه المكتبة المسؤولة عن حجم الخط
import random
from io import BytesIO
import re

# --- إعدادات الصفحة ---
st.set_page_config(page_title="منصة الامتحانات", layout="centered")
st.title("نظام توليد الأسئلة الامتحانية")

TEMPLATE_FILE = 'نموذج الاسئلة 30سؤال.docx' 

# --- دالة لتغيير حجم الخط في الملف بالكامل ---
def set_document_font_size(doc, size):
    # 1. تغيير حجم خط الفقرات العادية
    for p in doc.paragraphs:
        for run in p.runs:
            run.font.size = Pt(size)
            
    # 2. تغيير حجم خط الجداول (الأسئلة والخيارات)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(size)

def read_questions(file):
    doc = Document(file)
    mcq_list = []
    tf_list = []
    current_mode = None
    
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if "# اختياري" in line:
            current_mode = "MCQ"
            i += 1; continue
        elif "# صح وخطأ" in line:
            current_mode = "TF"
            i += 1; continue
            
        if current_mode == "MCQ":
            if i + 5 < len(lines):
                q = lines[i]
                opts = lines[i+1:i+6]
                if not any("#" in opt for opt in opts):
                    mcq_list.append({"q": q, "opts": opts})
                    i += 6; continue
        elif current_mode == "TF":
            tf_list.append(line)
            i += 1; continue
        i += 1
    return mcq_list, tf_list

def generate_exam(mcq_data, tf_data, template_path):
    doc = Document(template_path)
    
    random.shuffle(mcq_data)
    random.shuffle(tf_data)
    
    mcq_idx = 0
    tf_idx = 0
    current_shuffled_opts = None
    
    for table in doc.tables:
        # فحص نوع الجدول
        row_text_sample = ""
        try:
            for row in table.rows[:2]:
                for cell in row.cells: row_text_sample += cell.text
        except: pass

        # --- معالجة الاختيارات (MCQ) ---
        if "A" in row_text_sample and ("B" in row_text_sample or "," in row_text_sample):
            for row in table.rows:
                cells = row.cells
                row_text = "".join([c.text for c in cells])
                
                # أ) السؤال
                if "..." in row_text and "A" not in row_text:
                    if mcq_idx < len(mcq_data):
                        current_shuffled_opts = list(mcq_
