import streamlit as st
from docx import Document
from docx.shared import Pt  # للتحكم بحجم الخط
import random
from io import BytesIO
import re

# --- إعدادات الصفحة ---
st.set_page_config(page_title="منصة الامتحانات", layout="centered")
st.title("نظام توليد الأسئلة الامتحانية")

TEMPLATE_FILE = 'نموذج الاسئلة 30سؤال.docx' 

# --- دالة لتغيير حجم الخط لكامل الملف ---
def set_document_font_size(doc, size):
    # للفقرات العادية
    for p in doc.paragraphs:
        for run in p.runs:
            run.font.size = Pt(size)
    # للجداول (الأسئلة والخيارات)
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
    
    # قراءة الأسطر وتنظيف الفراغات
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # تحديد نوع السؤال
        if "# اختياري" in line:
            current_mode = "MCQ"
            i += 1; continue
        elif "# صح وخطأ" in line:
            current_mode = "TF"
            i += 1; continue
            
        # تخزين الأسئلة حسب النوع
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
    current_shuffled_opts = None # متغير لتخزين الخيارات مؤقتاً
    
    for table in doc.tables:
        # محاولة قراءة أول صفين لمعرفة نوع الجدول
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
                
                # حالة (أ): سطر السؤال (نقاط ولا يوجد حروف)
                if "..." in row_text and "A" not in row_text:
                    if mcq_idx < len(mcq_data):
                        # هنا كان الخطأ سابقاً: ننسخ القائمة ونخلطها
                        current_opts = mcq_data[mcq_idx]['opts']
                        current_shuffled_opts = list(current_opts)
                        random.shuffle(current_shuffled_opts)
                        
                        # كتابة نص السؤال
                        q_text = mcq_data[mcq_idx]['q']
                        for cell in cells:
                            for p in cell.paragraphs:
                                if "..." in p.text:
                                    p.text = re.sub(r'\.{3,}', q_text, p.text)
                
                # حالة (ب): سطر الخيارات (يحتوي A)
                elif "A" in row_text and current_shuffled_opts:
                    # خريطة تربط الحرف بالإجابة المخلوطة
                    opt_map = {
                        'A': current_shuffled_opts[0],
                        'B': current_shuffled_opts[1],
                        'C': current_shuffled_opts[2],
                        'D': current_shuffled_opts[3],
                        'E': current_shuffled_opts[4]
                    }
                    
                    # المرور على الخلايا للبحث عن الحرف ووضع الإجابة بجانبه
                    for i in range(len(cells)):
                        # تنظيف النص من الفواصل والمسافات
                        cell_text = cells[i].text.strip().replace(",", "")
                        
                        if cell_text in opt_map:
                            # إذا وجدنا الحرف، نكتب الإجابة في الخلية التالية
                            if i + 1 < len(cells):
                                next_cell = cells[i+1]
                                next_cell.text = opt_map[cell_text]
                                # محاذاة لليمين
                                for p in next_cell.paragraphs:
                                    p.alignment = 2 
                    
                    # الانتقال للسؤال التالي بعد إكمال الخيارات
                    mcq_idx += 1
                    current_shuffled_opts = None

        # ==========================================
        # 2. معالجة جداول الصح والخطأ (TF)
        # ==========================================
        else:
            is_tf = False
            # فحص وجود أقواس ( )
            for row in table.rows:
                full_txt = "".join([c.text for c in row.cells])
                if "(" in full_txt and ")" in full_txt:
                    is_tf = True; break
            
            if is_tf:
                for row in table.rows:
                    if tf_idx < len(tf_data):
                        full_row = "".join([c.text for c in row.cells])
                        # شرط: وجود نقاط وقوسين
                        if "..." in full_row and "(" in full_row:
                             for cell in row.cells:
                                for p in cell.paragraphs:
                                    if "..." in p.text:
                                        p.text = re.sub(r'\.{3,}', tf_data[tf_idx], p.text)
                             tf_idx += 1

    # === تغيير حجم الخط إلى 10 ===
    set_document_font_size(doc, 10)

    # الحفظ في الذاكرة
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- واجهة التطبيق ---
uploaded_file = st.file_uploader("ارفع ملف بنك الأسئلة (Word)", type=['docx'])

if uploaded_file is not None:
    if st.button("توليد الامتحان"):
        mcq, tf = read_questions(uploaded_file)
        
        if not mcq and not tf:
            st.error("لم يتم العثور على أسئلة! تأكد من كتابة '# اختياري' و '# صح وخطأ' في الملف.")
        else:
            st.success(f"تم قراءة: {len(mcq)} سؤال اختياري و {len(tf)} سؤال صح وخطأ.")
            try:
                final_file = generate_exam(mcq, tf, TEMPLATE_FILE)
                st.download_button(
                    label="📥 تحميل ورقة الامتحان",
                    data=final_file,
                    file_name="Exam_Final.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء التوليد: {e}")
