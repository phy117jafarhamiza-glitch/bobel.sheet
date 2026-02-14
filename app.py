import streamlit as st
from docx import Document
import random
from io import BytesIO
import re

# --- إعدادات الصفحة ---
st.set_page_config(page_title="منصة الامتحانات", layout="centered")
st.title("نظام توليد الأسئلة الامتحانية")

TEMPLATE_FILE = 'نموذج الاسئلة 30سؤال.docx' 

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
    
    # خلط الأسئلة
    random.shuffle(mcq_data)
    random.shuffle(tf_data)
    
    mcq_idx = 0
    tf_idx = 0
    
    # سنحتاج لتخزين الخيارات "المخلوطة" مؤقتاً لنضمن أن A,B,C,D,E لنفس السؤال متناسقة
    current_shuffled_opts = None
    
    for table in doc.tables:
        # فحص نوع الجدول (اختياري أم صح وخطأ)
        row_text_sample = ""
        try:
            for row in table.rows[:2]:
                for cell in row.cells: row_text_sample += cell.text
        except: pass

        # ==========================================
        # 1. معالجة جداول الاختيارات (MCQ)
        # ==========================================
        if "A" in row_text_sample and ("B" in row_text_sample or "," in row_text_sample):
            
            for row in table.rows:
                cells = row.cells
                row_text = "".join([c.text for c in cells])
                
                # أ) سطر السؤال (يحتوي نقاط كثيرة ولا يحتوي A)
                if "..." in row_text and "A" not in row_text:
                    if mcq_idx < len(mcq_data):
                        # نجهز خيارات هذا السؤال الجديد ونخلطها هنا
                        current_shuffled_opts = list(mcq_data[mcq_idx]['opts'])
                        random.shuffle(current_shuffled_opts)
                        
                        # نكتب السؤال
                        q_text = mcq_data[mcq_idx]['q']
                        for cell in cells:
                            for p in cell.paragraphs:
                                if "..." in p.text:
                                    p.text = re.sub(r'\.{3,}', q_text, p.text)
                
                # ب) سطر الخيارات (يحتوي A و B ...)
                elif "A" in row_text and current_shuffled_opts:
                    # هنا التعديل الجوهري: التعامل مع الخلايا المنفصلة
                    # ننشئ خريطة للإجابات
                    opt_map = {
                        'A': current_shuffled_opts[0],
                        'B': current_shuffled_opts[1],
                        'C': current_shuffled_opts[2],
                        'D': current_shuffled_opts[3],
                        'E': current_shuffled_opts[4]
                    }
                    
                    # نمر على الخلايا بالترتيب
                    for i in range(len(cells)):
                        cell_text = cells[i].text.strip().replace(",", "") # تنظيف النص (A, -> A)
                        
                        # إذا وجدنا حرفاً معروفاً (A, B, C...)
                        if cell_text in opt_map:
                            # نضع الإجابة في الخلية المجاورة (i + 1)
                            if i + 1 < len(cells):
                                # نتأكد أن الخلية المجاورة فيها نقاط لتستبدل
                                next_cell = cells[i+1]
                                # نمسح النقاط ونكتب الإجابة
                                next_cell.text = opt_map[cell_text]
                                # ننسق النص (اختياري: يجعله يمين لليسار)
                                for p in next_cell.paragraphs:
                                    p.alignment = 2 # 2 means RIGHT alignment usually
                    
                    # بعد الانتهاء من سطر الخيارات، ننتقل للسؤال التالي
                    mcq_idx += 1
                    current_shuffled_opts = None # تصفير المؤقت

        # ==========================================
        # 2. معالجة جداول الصح والخطأ (TF)
        # ==========================================
        else:
            # التحقق من وجود أقواس
            is_tf = False
            for row in table.rows:
                if "(" in "".join([c.text for c in row.cells]) and ")" in "".join([c.text for c in row.cells]):
                    is_tf = True; break
            
            if is_tf:
                for row in table.rows:
                    if tf_idx < len(tf_data):
                        full_row = "".join([c.text for c in row.cells])
                        if "..." in full_row and "(" in full_row:
                             for cell in row.cells:
                                for p in cell.paragraphs:
                                    if "..." in p.text:
                                        p.text = re.sub(r'\.{3,}', tf_data[tf_idx], p.text)
                             tf_idx += 1

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- الواجهة ---
uploaded_file = st.file_uploader("ارفع ملف بنك الأسئلة", type=['docx'])
if uploaded_file and st.button("توليد الامتحان"):
    mcq, tf = read_questions(uploaded_file)
    if not mcq and not tf:
        st.error("لم يتم العثور على أسئلة!")
    else:
        st.success(f"تم: {len(mcq)} اختياري، {len(tf)} صح وخطأ.")
        try:
            res = generate_exam(mcq, tf, TEMPLATE_FILE)
            st.download_button("تحميل الامتحان", res, "Exam.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"خطأ: {e}")
