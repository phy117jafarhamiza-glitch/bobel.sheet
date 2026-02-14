import streamlit as st
from docx import Document
from docx.shared import Pt
import random
from io import BytesIO
import re

# --- إعدادات الصفحة ---
st.set_page_config(page_title="منصة الامتحانات", layout="centered")
st.title("نظام توليد الأسئلة الامتحانية")

TEMPLATE_FILE = 'نموذج الاسئلة 30سؤال.docx' 

# --- دالة لتغيير حجم الخط ---
def set_document_font_size(doc, size):
    for p in doc.paragraphs:
        for run in p.runs:
            run.font.size = Pt(size)
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
    
    # ملاحظة: الأسئلة تأتي لهذه الدالة وهي مخلوطة ومقصوصة مسبقاً حسب العدد المطلوب
    
    mcq_idx = 0
    tf_idx = 0
    current_shuffled_opts = None 
    
    for table in doc.tables:
        row_text_sample = ""
        try:
            for row in table.rows[:2]:
                for cell in row.cells: row_text_sample += cell.text
        except: pass

        # --- الاختياري ---
        if "A" in row_text_sample and ("B" in row_text_sample or "," in row_text_sample):
            for row in table.rows:
                cells = row.cells
                row_text = "".join([c.text for c in cells])
                
                # سؤال
                if "..." in row_text and "A" not in row_text:
                    if mcq_idx < len(mcq_data):
                        current_opts = mcq_data[mcq_idx]['opts']
                        current_shuffled_opts = list(current_opts)
                        random.shuffle(current_shuffled_opts)
                        
                        q_text = mcq_data[mcq_idx]['q']
                        for cell in cells:
                            for p in cell.paragraphs:
                                if "..." in p.text:
                                    p.text = re.sub(r'\.{3,}', q_text, p.text)
                
                # خيارات
                elif "A" in row_text and current_shuffled_opts:
                    opt_map = {
                        'A': current_shuffled_opts[0], 'B': current_shuffled_opts[1],
                        'C': current_shuffled_opts[2], 'D': current_shuffled_opts[3],
                        'E': current_shuffled_opts[4]
                    }
                    for i in range(len(cells)):
                        cell_text = cells[i].text.strip().replace(",", "")
                        if cell_text in opt_map:
                            if i + 1 < len(cells):
                                next_cell = cells[i+1]
                                next_cell.text = opt_map[cell_text]
                                for p in next_cell.paragraphs:
                                    p.alignment = 2 
                    
                    mcq_idx += 1
                    current_shuffled_opts = None

        # --- الصح والخطأ ---
        else:
            is_tf = False
            for row in table.rows:
                full_txt = "".join([c.text for c in row.cells])
                if "(" in full_txt and ")" in full_txt:
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

    set_document_font_size(doc, 10)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- واجهة التطبيق الرئيسية ---
st.sidebar.header("لوحة التحكم")
st.sidebar.info("قم برفع الملف أولاً لتظهر الخيارات")

uploaded_file = st.file_uploader("1. ارفع ملف بنك الأسئلة (Word)", type=['docx'])

if uploaded_file is not None:
    # نقرأ الملف فوراً لنعرف عدد الأسئلة المتوفرة
    all_mcq, all_tf = read_questions(uploaded_file)
    
    if not all_mcq and not all_tf:
        st.error("لم يتم العثور على أسئلة! تأكد من التنسيق (# اختياري / # صح وخطأ).")
    else:
        st.success(f"تم تحليل الملف: وجدنا {len(all_mcq)} سؤال اختياري و {len(all_tf)} سؤال صح وخطأ.")
        
        st.markdown("---")
        st.subheader("2. حدد عدد الأسئلة المطلوبة في الامتحان:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # حقل اختيار عدد الاختياري (الحد الأقصى هو العدد المتوفر في الملف)
            mcq_count = st.number_input(
                "عدد أسئلة الاختيارات", 
                min_value=0, 
                max_value=len(all_mcq), 
                value=min(20, len(all_mcq)) # القيمة الافتراضية 20 أو الموجود
            )
            
        with col2:
            # حقل اختيار عدد الصح والخطأ
            tf_count = st.number_input(
                "عدد أسئلة الصح والخطأ", 
                min_value=0, 
                max_value=len(all_tf), 
                value=min(10, len(all_tf)) # القيمة الافتراضية 10 أو الموجود
            )
            
        st.markdown("---")
        
        if st.button("3. توليد الامتحان"):
            # نقوم بخلط الأسئلة وقص العدد المطلوب فقط
            random.shuffle(all_mcq)
            random.shuffle(all_tf)
            
            selected_mcq = all_mcq[:mcq_count]
            selected_tf = all_tf[:tf_count]
            
            try:
                final_file = generate_exam(selected_mcq, selected_tf, TEMPLATE_FILE)
                st.balloons() # احتفال بسيط عند النجاح
                st.download_button(
                    label="📥 تحميل ورقة الامتحان",
                    data=final_file,
                    file_name="Exam_Final.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                st.success(f"تم إنشاء امتحان يحتوي على {len(selected_mcq)} سؤال اختياري و {len(selected_tf)} سؤال صح وخطأ.")
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
