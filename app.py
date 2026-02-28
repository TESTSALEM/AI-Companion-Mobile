import streamlit as st
import os
import json
import base64
from PyPDF2 import PdfReader
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from groq import Groq
from PIL import Image

# ==========================================
# 1. إعدادات واجهة التطبيق (Mobile-Ready)
# ==========================================
st.set_page_config(
    page_title="AI Multi-Project Companion",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إنشاء مجلد المشاريع لضمان عدم حدوث خطأ عند أول تشغيل
PROJECTS_FOLDER = "projects"
if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

# الملفات الخاصة بالإعدادات
API_KEY_FILE = "groq_key.txt"

# ==========================================
# 2. الشخصية المتكاملة (الدردشة + البرمجة)
# ==========================================
SYSTEM_PROMPT = """أنت الآن 'رفيق ذكي متكامل'. 
اسمك هو 'مساعدك الشخصي'. 
مهمتك:
1. الدردشة الودية: إذا سألك المستخدم عن حالك، أو اسمه، أو مواضيع عامة، أجب كصديق ذكي ولبق.
2. الخبرة البرمجية: إذا طلب المستخدم كوداً، تحول إلى مبرمج Senior وقدم أفضل الحلول.
3. الذاكرة: تذكر دائماً ما يقوله المستخدم عن نفسه في هذه المحادثة (اسمه، اهتماماته) وتفاعل معها.
4. اللغة: تحدث باللغة العربية بأسلوب تقني وودي في نفس الوقت."""

# ==========================================
# 3. الدوال المساعدة (الإدارة والتخزين)
# ==========================================

def save_project_data(project_name, messages):
    """حفظ سجل المحادثة في ملف JSON مستقل لكل مشروع"""
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(messages, file, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"خطأ أثناء حفظ المشروع: {e}")

def load_project_data(project_name):
    """تحميل سجل المحادثة من الملف عند اختيار المشروع"""
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            st.error(f"خطأ أثناء تحميل المشروع: {e}")
            return None
    return None

def save_api_key(key):
    """حفظ مفتاح Groq في ملف نصي دائم"""
    with open(API_KEY_FILE, "w", encoding="utf-8") as file:
        file.write(key)

def load_api_key():
    """تحميل المفتاح المحفوظ"""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""

def convert_image_to_base64(image_file):
    """تحويل ملف الصورة إلى نص base64 لإرساله للمحرك"""
    try:
        return base64.b64encode(image_file.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"خطأ في معالجة الصورة: {e}")
        return ""

# ==========================================
# 4. بناء القائمة الجانبية (Sidebar)
# ==========================================

with st.sidebar:
    st.title("📂 مركز التحكم")
    
    # إدارة مفتاح API
    saved_key = load_api_key()
    user_api_key = st.text_input("مفتاح Groq API:", value=saved_key, type="password")
    
    if st.button("حفظ المفتاح وتنشيط النظام"):
        save_api_key(user_api_key)
        st.success("تم التنشيط بنجاح!")
        st.rerun()

    st.divider()

    # إدارة المشاريع
    st.subheader("🏗️ إدارة المشاريع")
    
    all_files = os.listdir(PROJECTS_FOLDER)
    project_list = [f.replace(".json", "") for f in all_files if f.endswith(".json")]
            
    if not project_list:
        project_list = ["محادثة_جديدة"]
        
    active_project = st.selectbox("اختر المشروع الحالي:", project_list)
    
    new_project_input = st.text_input("إنشاء مشروع جديد باسم:")
    if st.button("➕ إنشاء"):
        if new_project_name := new_project_input.strip():
            new_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
            save_project_data(new_project_name, new_msgs)
            st.success(f"تم إنشاء {new_project_name}")
            st.rerun()

    if st.button("🗑️ حذف المشروع المختار"):
        path_to_del = os.path.join(PROJECTS_FOLDER, f"{active_project}.json")
        if os.path.exists(path_to_del):
            os.remove(path_to_del)
            st.warning(f"تم حذف {active_project}")
            st.rerun()

    st.divider()

    # أدوات إضافية مطورة للجوال
    st.subheader("🛠️ أدوات الإدخال")
    
    # ميزة كاميرا الجوال [جديد]
    mobile_camera = st.camera_input("التقط صورة كود/تصميم (كاميرا الهاتف)")
    
    uploaded_pdf = st.file_uploader("ارفع ملف PDF كمرجع:", type=["pdf"])
    uploaded_img = st.file_uploader("ارفع صورة من الاستوديو:", type=["jpg", "png", "jpeg"])
    
    # تحديد الصورة النشطة (سواء من الكاميرا أو الرفع)
    active_image_file = mobile_camera if mobile_camera else uploaded_img

    st.write("🎙️ الأوامر الصوتية:")
    recorded_audio = mic_recorder(
        start_prompt="اضغط للتحدث 🎙️",
        stop_prompt="توقف للإرسال 📤",
        key='my_mic'
    )
    
    voice_feedback = st.checkbox("تفعيل النطق الصوتي للردود", value=False)

# ==========================================
# 5. استخراج البيانات والتحضير
# ==========================================

pdf_context_text = ""
if uploaded_pdf:
    try:
        reader = PdfReader(uploaded_pdf)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                pdf_context_text += extracted_text + "\n"
    except Exception as e:
        st.error(f"خطأ في قراءة الـ PDF: {e}")

# ==========================================
# 6. منطق المحادثة والذكاء الاصطناعي (البث اللحظي)
# ==========================================

if not user_api_key:
    st.info("💡 يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
else:
    groq_client = Groq(api_key=user_api_key)

    if "messages" not in st.session_state or st.session_state.get('current_p_name') != active_project:
        loaded_messages = load_project_data(active_project)
        if loaded_messages:
            st.session_state.messages = loaded_messages
        else:
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.current_p_name = active_project

    # عرض سجل المحادثة
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    final_user_query = None
    
    if recorded_audio:
        with st.spinner("جاري تحليل صوتك..."):
            try:
                transcription = groq_client.audio.transcriptions.create(
                    file=("audio.wav", recorded_audio['bytes']),
                    model="whisper-large-v3",
                    language="ar"
                )
                final_user_query = transcription.text
            except Exception as e:
                st.error(f"خطأ في التعرف على الصوت: {e}")
    else:
        final_user_query = st.chat_input("تحدث معي، أنا أسمعك وأفهمك...")

    if final_user_query:
        st.session_state.messages.append({"role": "user", "content": final_user_query})
        with st.chat_message("user"):
            st.markdown(final_user_query)

        with st.chat_message("assistant"):
            # منطقة عرض البث اللحظي (Streaming) [جديد]
            response_placeholder = st.empty()
            full_ai_response = ""
            
            with st.spinner("جاري التفكير والتحليل..."):
                try:
                    # تحضير المحتوى والموديل
                    if active_image_file:
                        selected_model = "meta-llama/llama-4-scout-17b-16e-instruct"
                        base64_data = convert_image_to_base64(active_image_file)
                        
                        prompt_msg = f"المرجع المرفق: {pdf_context_text}\n\nالسؤال: {final_user_query}"
                        
                        api_payload = [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt_msg},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_data}"}}
                                ]
                            }
                        ]
                    else:
                        selected_model = "llama-3.3-70b-versatile"
                        # دمج السياق في الطلب الأخير
                        context_query = f"المرجع: {pdf_context_text}\n\nالسؤال: {final_user_query}"
                        api_payload = st.session_state.messages[-10:] # إرسال آخر 10 رسائل للذاكرة
                        api_payload[-1] = {"role": "user", "content": context_query}

                    # طلب البث اللحظي (Streaming) لضمان عدم الانقطاع [جديد]
                    completion_stream = groq_client.chat.completions.create(
                        messages=api_payload,
                        model=selected_model,
                        temperature=0.7,
                        stream=True # تفعيل خاصية البث
                    )
                    
                    for chunk in completion_stream:
                        if chunk.choices[0].delta.content:
                            full_ai_response += chunk.choices[0].delta.content
                            # تحديث واجهة المستخدم لحظياً
                            response_placeholder.markdown(full_ai_response + "▌")
                    
                    # عرض الإجابة النهائية كاملة
                    response_placeholder.markdown(full_ai_response)
                    
                    # حفظ الرد في الذاكرة والملف
                    st.session_state.messages.append({"role": "assistant", "content": full_ai_response})
                    save_project_data(active_project, st.session_state.messages)

                    # النطق الصوتي
                    if voice_feedback:
                        try:
                            clean_text = full_ai_response.replace("`", "").replace("*", "")
                            tts = gTTS(text=clean_text[:300], lang='ar')
                            tts.save("reply_voice.mp3")
                            st.audio("reply_voice.mp3", autoplay=True)
                        except:
                            pass

                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالمحرك: {e}")