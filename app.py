import streamlit as st
from docx import Document
import random
from io import BytesIO
import re

# --- إعدادات الصفحة ---
st.set_page_config(page_title="منصة الامتحانات - جامعة المستقبل", layout="centered")
st.title("نظام توليد الأسئلة الامتحانية")

# --- اسم ملف القالب ---
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
            i += 1
            continue
        elif "# صح وخطأ" in line:
            current_mode = "TF"
            i += 1
            continue
            
        if current_mode == "MCQ":
            if i + 5 < len(lines):
                q = lines[i]
                opts = lines[i+1:i+6]
                if not any("#" in opt for opt in opts):
                    mcq_list.append({"q": q, "opts": opts})
                    i += 6
                    continue
        elif current_mode == "TF":
            tf_list.append(line)
            i += 1
            continue
        i += 1
    return mcq_list, tf_list

def generate_exam(mcq_data, tf_data, template_path):
    doc = Document(template_path)
    
    # خلط الأسئلة
    random.shuffle(mcq_data)
    random.shuffle(tf_data)
    
    mcq_idx = 0
    tf_idx = 0
    
    for table in doc.tables:
        # فحص محتوى الجدول
        try:
            header_text = ""
            for row in table.rows[:2]:
                for cell in row.cells:
                    header_text += cell.text
        except:
            header_text = ""

        # ==========================================
        # منطق الاختياري (MCQ) - التعديل الجديد هنا
        # ==========================================
        if "A" in header_text and ("B" in header_text or "," in header_text):
            for row in table.rows:
                # نجمع النص الكامل للصف لنفهم محتواه
                row_full_text = "".join([c.text for c in row.cells])
                
                # 1. حالة سطر السؤال (نقاط كثيرة ولا يوجد A)
                if "..." in row_full_text and "A" not in row_full_text:
                    if mcq_idx < len(mcq_data):
                        q_text = mcq_data[mcq_idx]['q']
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                if "..." in p.text:
                                    # استبدال النقاط بالسؤال
                                    p.text = re.sub(r'\.{3,}', q_text, p.text)
                
                # 2. حالة سطر الخيارات (يحتوي A, B, C...)
                elif "A" in row_full_text and ("..." in row_full_text or "E" in row_full_text):
                    if mcq_idx < len(mcq_data):
                        # نجلب خيارات السؤال الحالي
                        opts = mcq_data[mcq_idx]['opts']
                        random.shuffle(opts) # خلط الإجابات
                        
                        # نربط كل حرف بإجابة
                        opt_map = {
                            'A': opts[0], 
                            'B': opts[1], 
                            'C': opts[2], 
                            'D': opts[3], 
                            'E': opts[4]
                        }
                        
                        # نمر على كل خلية وفقرة ونستبدل بالكامل
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                txt = p.text.strip()
                                # نبحث عن الحرف في الفقرة
                                # التعديل: نمسح النص القديم ونكتب الجديد فوراً
                                for letter, answer in opt_map.items():
                                    # إذا كانت الفقرة تحتوي على الحرف (مثل "A" أو "A,")
                                    if letter in txt:
                                        # شرط إضافي: نتأكد أنها ليست كلمة تحتوي الحرف، بل الحرف كخيار
                                        # (عادة يكون الحرف مع نقاط أو مسافة أو فاصلة)
                                        if len(txt) < 20 or "..." in txt: 
                                            # نعيد صياغة الفقرة: الحرف + الإجابة
                                            p.text = f"{letter}  {answer}"
                                            # نضع مسافة لتجنب تكرار الاستبدال في نفس الفقرة
                                            break 
                        
                        mcq_idx += 1 # ننتقل للسؤال التالي

        # ==========================================
        # منطق الصح والخطأ (TF)
        # ==========================================
        else:
            is_tf_row = False
            for row in table.rows:
                rt = "".join([c.text for c in row.cells])
                if "(" in rt and ")" in rt:
                    is_tf_row = True
                    break
            
            if is_tf_row:
                for row in table.rows:
                    rt = "".join([c.text for c in row.cells])
                    if "..." in rt and "(" in rt:
                        if tf_idx < len(tf_data):
                            q_text = tf_data[tf_idx]
                            for cell in row.cells:
                                for p in cell.paragraphs:
                                    if "..." in p.text:
                                        p.text = re.sub(r'\.{3,}', q_text, p.text)
                            tf_idx += 1

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- التشغيل ---
uploaded_file = st.file_uploader("ارفع ملف بنك الأسئلة (Word)", type=['docx'])

if uploaded_file is not None:
    if st.button("توليد الامتحان"):
        mcq, tf = read_questions(uploaded_file)
        if not mcq and not tf:
            st.error("لم يتم العثور على أسئلة!")
        else:
            st.success(f"تم قراءة: {len(mcq)} سؤال اختياري و {len(tf)} سؤال صح وخطأ.")
            try:
                final_file = generate_exam(mcq, tf, TEMPLATE_FILE)
                st.download_button("📥 تحميل الامتحان", final_file, "Exam_Final.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            except Exception as e:
                st.error(f"خطأ: {e}")
