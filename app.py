import streamlit as st
import os
import json
import base64
import io
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

# تخصيص مظهر التطبيق (CSS) ليتناسب مع شاشة الجوال في الرياض
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em; 
        background-color: #FF4B4B; 
        color: white; 
        font-weight: bold; 
        border: none;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .stChatFloatingInputContainer { background-color: #0E1117; }
    .stSidebar { background-color: #161B22; }
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

# واجهة العنوان الرئيسية
st.title("AI Companion V2 🤖")
if st.button("🔔 اختبار نظام الإشعارات"):
    trigger_android_notification("تنبيه من مساعدك", "يا هلا يا سالم، نظام الإشعارات والصور يعمل بنجاح!")

# ==========================================
# 3. إعدادات المجلدات وتخزين البيانات
# ==========================================
PROJECTS_FOLDER = "projects"
API_KEY_FILE = "groq_key.txt"

# إنشاء مجلد المشاريع إذا لم يكن موجوداً
if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

# الشخصية البرمجية للمساعد
SYSTEM_PROMPT = """أنت 'مساعد سالم الشخصي'. أنت خبير مبرمج (Senior Developer) وصديق تقني ذكي. 
لديك القدرة الكاملة على تحليل الصور والملفات البرمجية. 
أجب دائماً باللغة العربية بأسلوب متميز وودود."""

# ==========================================
# 4. الدوال المساعدة (الإدارة والتحويل)
# ==========================================

def save_project_data(project_name, messages):
    """حفظ سجل المحادثة بالكامل في ملف JSON مستقل"""
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(messages, file, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"خطأ في حفظ المشروع: {e}")

def load_project_data(project_name):
    """تحميل بيانات المشروع عند الطلب"""
    file_path = os.path.join(PROJECTS_FOLDER, f"{project_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            st.error(f"خطأ في تحميل المشروع: {e}")
    return None

def save_api_key(key):
    """حفظ مفتاح Groq في ملف نصي دائم"""
    with open(API_KEY_FILE, "w", encoding="utf-8") as file:
        file.write(key)

def load_api_key():
    """تحميل المفتاح المحفوظ لضمان عدم إدخاله يدوياً كل مرة"""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""

def process_and_convert_image(image_file):
    """ضغط الصورة وتحويلها لـ Base64 لضمان قبولها في المحرك"""
    try:
        img = Image.open(image_file)
        # تصغير الصورة إذا كانت ضخمة (لأجهزة الجوال الحديثة)
        img.thumbnail((1000, 1000)) 
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"فشل في معالجة الصورة: {e}")
        return None

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
        st.success("تم التنشيط بنجاح!")
        st.rerun()

    st.divider()

    # إدارة المشاريع المتعددة
    all_files = os.listdir(PROJECTS_FOLDER)
    project_list = [f.replace(".json", "") for f in all_files if f.endswith(".json")]
    if not project_list: project_list = ["محادثة_جديدة"]
    active_project = st.selectbox("المشروع الحالي:", project_list)
    
    new_p_input = st.text_input("أنشئ مشروعاً جديداً باسم:")
    if st.button("➕ إنشاء المشروع"):
        if new_p_input.strip():
            save_project_data(new_p_input.strip(), [{"role": "system", "content": SYSTEM_PROMPT}])
            st.rerun()

    if st.button("🗑️ حذف المشروع الحالي"):
        path_to_del = os.path.join(PROJECTS_FOLDER, f"{active_project}.json")
        if os.path.exists(path_to_del):
            os.remove(path_to_del)
            st.rerun()

    st.divider()

    # أدوات الإدخال المتكاملة للجوال
    st.subheader("🛠️ أدوات الصور والملفات")
    mobile_camera = st.camera_input("التقط صورة بالكاميرا")
    uploaded_pdf = st.file_uploader("ارفع ملف PDF كمرجع:", type=["pdf"])
    uploaded_img = st.file_uploader("ارفع صورة من الاستوديو:", type=["jpg", "png", "jpeg"])
    
    # الأولوية لصورة الكاميرا إذا وجدت
    active_image = mobile_camera if mobile_camera else uploaded_img

    st.write("🎙️ الأوامر الصوتية:")
    recorded_audio = mic_recorder(
        start_prompt="تحدث الآن 🎙️", 
        stop_prompt="توقف للإرسال 📤", 
        key='my_mic'
    )
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
# 7. محرك الذكاء الاصطناعي ومعالجة المحادثة
# ==========================================

if not user_api_key:
    st.info("💡 يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
else:
    groq_client = Groq(api_key=user_api_key)

    # تهيئة الذاكرة والرسائل
    if "messages" not in st.session_state or st.session_state.get('current_p_name') != active_project:
        loaded_messages = load_project_data(active_project)
        if loaded_messages:
            st.session_state.messages = loaded_messages
        else:
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.current_p_name = active_project

    # عرض سجل الدردشة
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # استقبال مدخلات سالم (صوت أو نص)
    user_query = None
    if recorded_audio:
        with st.spinner("جاري تحليل صوتك..."):
            try:
                transcription = groq_client.audio.transcriptions.create(
                    file=("audio.wav", recorded_audio['bytes']),
                    model="whisper-large-v3",
                    language="ar"
                )
                user_query = transcription.text
            except Exception as e:
                st.error(f"خطأ في تحليل الصوت: {e}")
    else:
        user_query = st.chat_input("اسألني أي شيء يا سالم...")

    if user_query:
        # إضافة سؤال المستخدم للذاكرة
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # بناء الـ Payload الصحيح لتجنب BadRequestError
            try:
                if active_image:
                    # نظام فحص الصور (Vision)
                    model_to_use = "llama-3.2-11b-vision-preview"
                    base64_img = process_and_convert_image(active_image)
                    
                    # تحضير الرسالة بتركيبة المصفوفة المطلوبة
                    messages_payload = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"المرجع المرفق: {pdf_context}\n\nسؤال المستخدم: {user_query}"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                            ]
                        }
                    ]
                else:
                    # نظام الدردشة النصية (Text)
                    model_to_use = "llama-3.3-70b-versatile"
                    context_query = f"سياق الـ PDF:\n{pdf_context}\n\nالسؤال الحالي: {user_query}"
                    
                    # إرسال الذاكرة (آخر 10 رسائل) لضمان استقرار المحادثة
                    messages_payload = st.session_state.messages[-10:]
                    messages_payload[-1] = {"role": "user", "content": context_query}

                # طلب البث اللحظي (Streaming) لسرعة العرض
                completion_stream = groq_client.chat.completions.create(
                    messages=messages_payload,
                    model=model_to_use,
                    temperature=0.7,
                    stream=True
                )
                
                # معالجة التدفق وعرضه حرفاً بحرف
                for chunk in completion_stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                
                # حفظ الرد النهائي في الذاكرة والملف
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                save_project_data(active_project, st.session_state.messages)
                
                # إرسال إشعار تلقائي عند الردود الطويلة
                if len(full_response) > 300:
                    trigger_android_notification("تم اكتمال التحليل", "يا سالم، انتهيت من كتابة الرد المفصل لك.")

                # النطق الصوتي (TTS) إذا كان مفعلاً
                if voice_feedback:
                    try:
                        clean_text = full_response.replace("`", "").replace("*", "")
                        tts = gTTS(text=clean_text[:300], lang='ar')
                        tts.save("response.mp3")
                        st.audio("response.mp3", autoplay=True)
                    except: pass

            except Exception as e:
                st.error(f"حدث خطأ في محرك Groq: {e}")
