import streamlit as st
import os
import json
import base64
from PyPDF2 import PdfReader
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from groq import Groq
from PIL import Image
import streamlit.components.v1 as components

# ==========================================
# 1. إعدادات واجهة التطبيق (يجب أن تكون أول أمر)
# ==========================================
st.set_page_config(
    page_title="AI Companion V2 - سالم",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص مظهر التطبيق ليتناسب مع شاشة الجوال
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #FF4B4B; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. جسر الإشعارات مع تطبيق الأندرويد
# ==========================================
def trigger_android_notification(title, message):
    """إرسال أمر لتطبيق الأندرويد لإظهار إشعار حقيقي"""
    notification_js = f"""
        <script>
            if (window.AndroidBridge) {{
                AndroidBridge.sendNotification('{title}', '{message}');
            }}
        </script>
    """
    components.html(notification_js, height=0)

# زر اختبار الإشعارات في أعلى الصفحة
col1, col2 = st.columns([4, 1])
with col1:
    st.title("AI Companion V2 🤖")
with col2:
    if st.button("🔔 فحص"):
        trigger_android_notification("تنبيه النظام", "يا هلا يا سالم، نظام الإشعارات يعمل بنجاح!")

# ==========================================
# 3. إعدادات المجلدات والملفات
# ==========================================
PROJECTS_FOLDER = "projects"
API_KEY_FILE = "groq_key.txt"

if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

SYSTEM_PROMPT = """أنت الآن 'رفيق ذكي متكامل'. اسمك هو 'مساعدك الشخصي'. 
مهمتك: الدردشة الودية، الخبرة البرمجية كSenior Developer، تذكر اهتمامات المستخدم، والتحدث بالعربية التقنية والودية."""

# ==========================================
# 4. الدوال المساعدة (الإدارة والتخزين)
# ==========================================

def save_project_data(project_name, messages):
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(messages, file, ensure_ascii=False, indent=4)

def load_project_data(project_name):
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return None

def save_api_key(key):
    with open(API_KEY_FILE, "w", encoding="utf-8") as file:
        file.write(key)

def load_api_key():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""

def convert_image_to_base64(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# ==========================================
# 5. بناء القائمة الجانبية (Sidebar)
# ==========================================

with st.sidebar:
    st.header("📂 مركز التحكم")
    
    # إدارة مفتاح API
    saved_key = load_api_key()
    user_api_key = st.text_input("مفتاح Groq API:", value=saved_key, type="password")
    if st.button("تنشيط النظام 🚀"):
        save_api_key(user_api_key)
        st.success("تم التنشيط!")
        st.rerun()

    st.divider()

    # إدارة المشاريع
    all_files = os.listdir(PROJECTS_FOLDER)
    project_list = [f.replace(".json", "") for f in all_files if f.endswith(".json")]
    if not project_list: project_list = ["محادثة_جديدة"]
    active_project = st.selectbox("المشروع الحالي:", project_list)
    
    new_p_name = st.text_input("اسم مشروع جديد:")
    if st.button("➕ إنشاء"):
        if new_p_name.strip():
            save_project_data(new_p_name.strip(), [{"role": "system", "content": SYSTEM_PROMPT}])
            st.rerun()

    if st.button("🗑️ حذف الحالي"):
        os.remove(os.path.join(PROJECTS_FOLDER, f"{active_project}.json"))
        st.rerun()

    st.divider()

    # أدوات الإدخال للجوال
    st.subheader("🛠️ أدوات الإدخال")
    mobile_camera = st.camera_input("الكاميرا")
    uploaded_pdf = st.file_uploader("ملف PDF مرجع:", type=["pdf"])
    uploaded_img = st.file_uploader("صورة من الاستوديو:", type=["jpg", "png", "jpeg"])
    
    active_image_file = mobile_camera if mobile_camera else uploaded_img

    st.write("🎙️ الأوامر الصوتية:")
    recorded_audio = mic_recorder(start_prompt="تحدث 🎙️", stop_prompt="إرسال 📤", key='my_mic')
    voice_feedback = st.checkbox("تفعيل النطق الصوتي للردود", value=False)

# ==========================================
# 6. استخراج البيانات والتحضير
# ==========================================
pdf_context = ""
if uploaded_pdf:
    reader = PdfReader(uploaded_pdf)
    for page in reader.pages:
        pdf_context += (page.extract_text() or "") + "\n"

# ==========================================
# 7. منطق الذكاء الاصطناعي والبث (Streaming)
# ==========================================

if not user_api_key:
    st.warning("💡 أدخل مفتاح API في الجانب للبدء.")
else:
    client = Groq(api_key=user_api_key)

    # إدارة ذاكرة الجلسة
    if "messages" not in st.session_state or st.session_state.get('p_name') != active_project:
        data = load_project_data(active_project)
        st.session_state.messages = data if data else [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.p_name = active_project

    # عرض الدردشة
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # معالجة المدخلات (صوتية أو نصية)
    user_query = None
    if recorded_audio:
        with st.spinner("تحليل الصوت..."):
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", recorded_audio['bytes']),
                model="whisper-large-v3",
                language="ar"
            )
            user_query = transcription.text
    else:
        user_query = st.chat_input("اكتب سؤالك هنا يا سالم...")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            response_area = st.empty()
            full_response = ""
            
            # تحديد الموديل بناءً على وجود صورة
            if active_image_file:
                # موديل الرؤية (Vision)
                model_name = "llama-3.2-11b-vision-preview" 
                img_b64 = convert_image_to_base64(active_image_file)
                payload = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"المرجع: {pdf_context}\nالسؤال: {user_query}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }
                ]
            else:
                # موديل الدردشة النصية العملاق
                model_name = "llama-3.3-70b-versatile"
                context_added = f"المرجع من الـ PDF: {pdf_context}\n\nسؤال المستخدم: {user_query}"
                payload = st.session_state.messages[-10:] # آخر 10 رسائل للذاكرة
                payload[-1] = {"role": "user", "content": context_added}

            # طلب البث اللحظي (Streaming) لسرعة الاستجابة
            stream = client.chat.completions.create(
                messages=payload,
                model=model_name,
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_area.markdown(full_response + "▌")
            
            response_area.markdown(full_response)
            
            # حفظ النتائج وإرسال إشعار عند اكتمال الإجابة الطويلة
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_project_data(active_project, st.session_state.messages)
            
            if len(full_response) > 200:
                trigger_android_notification("تم الانتهاء", "سالم، الإجابة الطويلة جاهزة للقراءة!")

            # النطق الصوتي (TTS)
            if voice_feedback:
                try:
                    tts = gTTS(text=full_response[:300], lang='ar')
                    tts.save("voice.mp3")
                    st.audio("voice.mp3", autoplay=True)
                except: pass
