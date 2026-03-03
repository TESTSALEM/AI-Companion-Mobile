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
# 1. إعدادات واجهة التطبيق (يجب أن يكون أول سطر برمي)
# ==========================================
st.set_page_config(
    page_title="AI Companion V2 - سالم",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص مظهر التطبيق ليتوافق مع شاشة الجوال
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; border: none; }
    .stChatFloatingInputContainer { background-color: #0E1117; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. جسر الإشعارات مع تطبيق الأندرويد
# ==========================================
def trigger_android_notification(title, message):
    """إرسال إشارة برمجية للجسر المدمج في تطبيق الأندرويد لإظهار إشعار حقيقي"""
    notification_js = f"""
        <script>
            if (window.AndroidBridge) {{
                AndroidBridge.sendNotification('{title}', '{message}');
            }}
        </script>
    """
    components.html(notification_js, height=0)

# واجهة العنوان
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("AI Companion V2 🤖")
with col_btn:
    if st.button("🔔 فحص"):
        trigger_android_notification("نظام سالم", "الإشعارات والصور تعمل بنسبة 100%")

# ==========================================
# 3. إعدادات التخزين والمشاريع
# ==========================================
PROJECTS_FOLDER = "projects"
API_KEY_FILE = "groq_key.txt"

if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

SYSTEM_PROMPT = """أنت 'رفيق ذكي متكامل' لمستخدمك 'سالم'. 
أنت خبير مبرمج (Senior Developer) وصديق تقني ودود. 
أجب دائماً باللغة العربية بأسلوب ذكي، وتذكر سياق المحادثة بدقة."""

# ==========================================
# 4. الدوال المساعدة (الإدارة والتحويل)
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
    """تحويل ملف الصورة إلى نص Base64 متوافق مع محرك Groq Vision"""
    try:
        return base64.b64encode(image_file.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"فشل معالجة الصورة: {e}")
        return None

# ==========================================
# 5. القائمة الجانبية (Sidebar)
# ==========================================

with st.sidebar:
    st.header("📂 مركز التحكم")
    
    # إدارة الـ API
    saved_key = load_api_key()
    user_api_key = st.text_input("Groq API Key:", value=saved_key, type="password")
    if st.button("تنشيط النظام 🚀"):
        save_api_key(user_api_key)
        st.success("تم التنشيط بنجاح!")
        st.rerun()

    st.divider()

    # إدارة المشاريع
    all_files = os.listdir(PROJECTS_FOLDER)
    project_list = [f.replace(".json", "") for f in all_files if f.endswith(".json")]
    if not project_list: project_list = ["محادثة_جديدة"]
    active_project = st.selectbox("المشروع الحالي:", project_list)
    
    new_p_input = st.text_input("أنشئ مشروعاً جديداً:")
    if st.button("➕ إنشاء"):
        if new_p_input.strip():
            save_project_data(new_p_input.strip(), [{"role": "system", "content": SYSTEM_PROMPT}])
            st.rerun()

    st.divider()

    # أدوات الإدخال (الكاميرا والملفات)
    st.subheader("🛠️ أدوات الصور والملفات")
    mobile_camera = st.camera_input("التقط صورة بالكاميرا")
    uploaded_pdf = st.file_uploader("ارفع ملف PDF كمرجع:", type=["pdf"])
    uploaded_img = st.file_uploader("ارفع صورة من الاستوديو:", type=["jpg", "png", "jpeg"])
    
    # تحديد الصورة التي سيتم فحصها
    active_image = mobile_camera if mobile_camera else uploaded_img

    st.write("🎙️ الأوامر الصوتية:")
    recorded_audio = mic_recorder(start_prompt="تحدث الآن 🎙️", stop_prompt="إرسال الصوت 📤", key='my_mic')
    voice_feedback = st.checkbox("تفعيل النطق الصوتي للردود", value=False)

# ==========================================
# 6. استخراج سياق الـ PDF
# ==========================================
pdf_context = ""
if uploaded_pdf:
    try:
        reader = PdfReader(uploaded_pdf)
        for page in reader.pages:
            pdf_context += (page.extract_text() or "") + "\n"
    except Exception as e:
        st.error(f"خطأ في قراءة الـ PDF: {e}")

# ==========================================
# 7. محرك الذكاء الاصطناعي ومعالجة الأخطاء
# ==========================================

if not user_api_key:
    st.info("💡 يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
else:
    groq_client = Groq(api_key=user_api_key)

    # تهيئة الذاكرة
    if "messages" not in st.session_state or st.session_state.get('current_p') != active_project:
        loaded_data = load_project_data(active_project)
        st.session_state.messages = loaded_data if loaded_data else [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.current_p = active_project

    # عرض المحادثة
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # الحصول على استفسار المستخدم
    user_query = None
    if recorded_audio:
        with st.spinner("جاري تحويل صوتك لنص..."):
            try:
                transcription = groq_client.audio.transcriptions.create(
                    file=("audio.wav", recorded_audio['bytes']),
                    model="whisper-large-v3",
                    language="ar"
                )
                user_query = transcription.text
            except Exception as e:
                st.error(f"فشل تحليل الصوت: {e}")
    else:
        user_query = st.chat_input("تحدث معي يا سالم، أنا أسمعك...")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # --- بناء الـ Payload الصحيح لتجنب BadRequestError ---
            try:
                if active_image:
                    # نظام فحص الصور (Vision System)
                    model_to_use = "llama-3.2-11b-vision-preview"
                    base64_img = convert_image_to_base64(active_image)
                    
                    # هيكل رسالة الصور الصارم
                    messages_payload = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"المرجع: {pdf_context}\n\nسؤال المستخدم: {user_query}"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                            ]
                        }
                    ]
                else:
                    # نظام الدردشة النصية (Text System)
                    model_to_use = "llama-3.3-70b-versatile"
                    # دمج سياق الـ PDF مع السؤال الأخير
                    enhanced_query = f"سياق الـ PDF:\n{pdf_context}\n\nالسؤال الحالي: {user_query}"
                    
                    messages_payload = st.session_state.messages[-10:] # آخر 10 رسائل للذاكرة
                    messages_payload[-1] = {"role": "user", "content": enhanced_query}

                # طلب البث اللحظي (Streaming)
                completion = groq_client.chat.completions.create(
                    messages=messages_payload,
                    model=model_to_use,
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                
                # حفظ الرد
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                save_project_data(active_project, st.session_state.messages)
                
                # إرسال إشعار تلقائي عند اكتمال الإجابات الطويلة
                if len(full_response) > 200:
                    trigger_android_notification("تم الانتهاء", "سالم، التحليل جاهز للقراءة في تطبيقك.")

                # النطق الصوتي (TTS)
                if voice_feedback:
                    try:
                        clean_text = full_response.replace("`", "").replace("*", "")
                        tts = gTTS(text=clean_text[:300], lang='ar')
                        tts.save("response.mp3")
                        st.audio("response.mp3", autoplay=True)
                    except: pass

            except Exception as e:
                st.error(f"حدث خطأ في طلب Groq: {e}")
                st.info("نصيحة: تأكد من صحة مفتاح الـ API ومن عدم محاولة إرسال ملفات ضخمة جداً.")
