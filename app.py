import streamlit as st
from docx import Document
import random
from io import BytesIO
import re  # مكتبة مهمة للتعامل مع النصوص والنقاط

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
    
    # قراءة الأسطر وتنظيفها
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # اكتشاف العناوين
        if "# اختياري" in line:
            current_mode = "MCQ"
            i += 1
            continue
        elif "# صح وخطأ" in line:
            current_mode = "TF"
            i += 1
            continue
            
        if current_mode == "MCQ":
            # نتوقع السؤال + 5 خيارات
            if i + 5 < len(lines):
                q = lines[i]
                opts = lines[i+1:i+6]
                # التأكد أن الأسطر ليست عناوين جديدة
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

def clean_text(text):
    """دالة مساعدة لإزالة المسافات الزائدة"""
    return text.strip()

def generate_exam(mcq_data, tf_data, template_path):
    doc = Document(template_path)
    random.shuffle(mcq_data)
    random.shuffle(tf_data)
    
    mcq_idx = 0
    tf_idx = 0
    
    # التكرار عبر الجداول
    for table in doc.tables:
        # محاولة فهم نوع الجدول من أول صفين
        try:
            # نجمع نص أول صفين لنعرف المحتوى
            header_text = ""
            for row in table.rows[:2]:
                for cell in row.cells:
                    header_text += cell.text
        except:
            header_text = ""

        # --- منطق الاختياري (MCQ) ---
        # نعرفه إذا كان الجدول يحتوي على حروف A, B
        if "A" in header_text and ("B" in header_text or "," in header_text):
            for row in table.rows:
                # ندمج نص الخلايا في الصف للبحث
                row_full_text = "".join([c.text for c in row.cells])
                
                # 1. تعبئة السؤال:
                # الشرط: يحتوي على نقاط كثيرة، ولا يحتوي على A,
                if "..." in row_full_text and "A" not in row_full_text:
                    if mcq_idx < len(mcq_data):
                        q_text = mcq_data[mcq_idx]['q']
                        
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                if "..." in p.text:
                                    # السحر هنا: استبدال أي سلسلة نقاط (3 فأكثر) بنص السؤال
                                    # re.sub(pattern, replacement, string)
                                    p.text = re.sub(r'\.{3,}', q_text, p.text)
                
                # 2. تعبئة الخيارات:
                elif "A" in row_full_text and "..." in row_full_text:
                    if mcq_idx < len(mcq_data):
                        opts = mcq_data[mcq_idx]['opts']
                        random.shuffle(opts) # خلط الإجابات
                        
                        # نمر على الخلايا ونبحث عن الأنماط A,.... B,....
                        # ملاحظة: سنقوم بمسح محتوى الخلية وكتابة الخيار الجديد بتنسيق نظيف
                        # لأن استبدال النقاط هنا صعب بسبب تداخل الحروف
                        
                        # سنفترض أن كل خلية قد تحتوي على خيار أو أكثر
                        # لكن الأضمن هو البحث داخل الفقرات
                        
                        current_opt_map = {
                            'A': opts[0], 'B': opts[1], 'C': opts[2], 'D': opts[3], 'E': opts[4]
                        }
                        
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                txt = p.text
                                # نبحث عن الحروف A, B, C, D, E متبوعة بأي شيء
                                # ونستبدلها بالخيار
                                
                                # طريقة بسيطة: إذا وجدنا "A," نستبدل السطر كله
                                if "A," in txt or "A" in txt and "..." in txt:
                                     # نحاول الحفاظ على التنسيق عبر الاستبدال الذكي
                                     # استبدال (حرف + فاصلة + نقاط) بـ (حرف + فاصلة + الإجابة)
                                     
                                     # A
                                     if "A" in txt:
                                         txt = re.sub(r'A\s*[,،]?\s*\.{2,}', f'A, {opts[0]}', txt)
                                     # B
                                     if "B" in txt:
                                         txt = re.sub(r'B\s*[,،]?\s*\.{2,}', f'B, {opts[1]}', txt)
                                     # C
                                     if "C" in txt:
                                         txt = re.sub(r'C\s*[,،]?\s*\.{2,}', f'C, {opts[2]}', txt)
                                     # D
                                     if "D" in txt:
                                         txt = re.sub(r'D\s*[,،]?\s*\.{2,}', f'D, {opts[3]}', txt)
                                     # E
                                     if "E" in txt:
                                         txt = re.sub(r'E\s*[,،]?\s*\.{2,}', f'E, {opts[4]}', txt)
                                         
                                     p.text = txt
                        
                        mcq_idx += 1 # ننتقل للسؤال التالي بعد إتمام الصف

        # --- منطق الصح والخطأ (TF) ---
        else:
            # نعرفه بوجود القوسين ( )
            is_tf_row = False
            for row in table.rows:
                row_txt = "".join([c.text for c in row.cells])
                if "(" in row_txt and ")" in row_txt:
                    is_tf_row = True
                    break
            
            if is_tf_row:
                for row in table.rows:
                    row_txt = "".join([c.text for c in row.cells])
                    # إذا وجدنا نقاط وقوسين، هذا سؤال
                    if "..." in row_txt and "(" in row_txt and ")" in row_txt:
                        if tf_idx < len(tf_data):
                            q_text = tf_data[tf_idx]
                            for cell in row.cells:
                                for p in cell.paragraphs:
                                    # نبحث عن الفقرة التي فيها نقاط (السؤال)
                                    if "..." in p.text:
                                        # نستبدل النقاط بالسؤال
                                        p.text = re.sub(r'\.{3,}', q_text, p.text)
                                        # نتأكد أن القوسين لم يمسحا، وإن مسحا نعيدهما (أحيانا تكون في نفس الفقرة)
                            tf_idx += 1

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- واجهة التطبيق ---
uploaded_file = st.file_uploader("ارفع ملف بنك الأسئلة (Word)", type=['docx'])

if uploaded_file is not None:
    if st.button("توليد الامتحان"):
        mcq, tf = read_questions(uploaded_file)
        
        # عرض معلومات للتأكد من أن الأسئلة تمت قراءتها
        if len(mcq) == 0 and len(tf) == 0:
            st.error("لم يتم العثور على أي أسئلة! تأكد أنك كتبت '# اختياري' و '# صح وخطأ' في ملف البنك.")
        else:
            st.success(f"تم قراءة: {len(mcq)} سؤال اختياري و {len(tf)} سؤال صح وخطأ.")
            
            try:
                final_file = generate_exam(mcq, tf, TEMPLATE_FILE)
                st.download_button(
                    label="📥 تحميل الامتحان",
                    data=final_file,
                    file_name="Exam_Final.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء الكتابة في القالب: {e}")
