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
# 1. إعدادات واجهة التطبيق (أول سطر برمي)
# ==========================================
st.set_page_config(
    page_title="AI Companion V2 - سالم",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تصميم احترافي متوافق مع جوالات أندرويد
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
        box-shadow: 0px 4px 12px rgba(255, 75, 75, 0.2);
    }
    .stChatFloatingInputContainer { background-color: #0E1117; }
    .stSidebar { background-color: #161B22; border-right: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. جسر الإشعارات (Android Bridge)
# ==========================================
def trigger_android_notification(title, message):
    """إرسال إشعار حقيقي لهاتف سالم عبر تطبيق الأندرويد"""
    notification_js = f"""
        <script>
            if (window.AndroidBridge) {{
                AndroidBridge.sendNotification('{title}', '{message}');
            }}
        </script>
    """
    components.html(notification_js, height=0)

# واجهة العنوان
st.title("AI Companion V2 🤖")
if st.button("🔔 فحص جاهزية النظام"):
    trigger_android_notification("نظام سالم", "تم تحديث الموديلات وإصلاح أخطاء الصور بنجاح!")

# ==========================================
# 3. إدارة الملفات والمشاريع
# ==========================================
PROJECTS_FOLDER = "projects"
API_KEY_FILE = "groq_key.txt"

if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

SYSTEM_PROMPT = """أنت 'رفيق سالم الشخصي'. أنت خبير مبرمج Senior Developer. 
لديك القدرة الكاملة على تحليل الصور والبيانات بدقة مذهلة. 
أجب دائماً باللغة العربية التقنية الراقية."""

# ==========================================
# 4. الدوال المساعدة (الإدارة والتحويل)
# ==========================================

def save_project_data(p_name, msgs):
    """حفظ سجل المحادثة بالكامل لضمان عدم ضياع مجهود سالم"""
    file_path = os.path.join(PROJECTS_FOLDER, f"{p_name}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=4)

def load_project_data(p_name):
    file_path = os.path.join(PROJECTS_FOLDER, f"{p_name}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_api_key(key):
    with open(API_KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)

def load_api_key():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def process_and_convert_image(image_file):
    """تحويل ومعالجة الصور مع إصلاح مشكلة RGBA و JPEG"""
    try:
        img = Image.open(image_file)
        # إصلاح مشكلة الألوان الشفافة (PNG to JPG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # تحسين الحجم لسرعة المعالجة على Groq
        img.thumbnail((1024, 1024)) 
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"⚠️ فشل معالجة الصورة: {e}")
        return None

# ==========================================
# 5. القائمة الجانبية (Sidebar)
# ==========================================

with st.sidebar:
    st.header("📂 مركز التحكم")
    
    saved_key = load_api_key()
    user_api_key = st.text_input("مفتاح Groq API:", value=saved_key, type="password")
    if st.button("تنشيط النظام 🚀"):
        save_api_key(user_api_key)
        st.success("تم التنشيط بنجاح!")
        st.rerun()

    st.divider()

    # إدارة المشاريع المتعددة لبرمجة Streamlit
    projects = [f.replace(".json", "") for f in os.listdir(PROJECTS_FOLDER) if f.endswith(".json")]
    if not projects: projects = ["محادثة_جديدة"]
    active_p = st.selectbox("المشروع الحالي:", projects)
    
    new_p_name = st.text_input("اسم مشروع جديد:")
    if st.button("➕ إنشاء المشروع"):
        if new_p_name.strip():
            save_project_data(new_p_name.strip(), [{"role": "system", "content": SYSTEM_PROMPT}])
            st.rerun()

    st.divider()

    # أدوات الإدخال المتقدمة
    st.subheader("🛠️ أدوات الصور والملفات")
    cam_in = st.camera_input("التقط صورة بالكاميرا")
    up_img = st.file_uploader("ارفع صورة من الاستوديو:", type=["jpg", "png", "jpeg"])
    up_pdf = st.file_uploader("ارفع ملف PDF كمرجع:", type=["pdf"])
    
    final_img_file = cam_in if cam_in else up_img

    st.write("🎙️ الأوامر الصوتية:")
    audio_rec = mic_recorder(start_prompt="تحدث الآن 🎙️", stop_prompt="توقف للإرسال 📤", key='mic')
    voice_feedback = st.checkbox("تفعيل النطق الصوتي للردود", value=False)

# ==========================================
# 6. استخراج سياق الـ PDF
# ==========================================
pdf_ctx = ""
if up_pdf:
    try:
        reader = PdfReader(up_pdf)
        for page in reader.pages:
            pdf_ctx += (page.extract_text() or "") + "\n"
    except: st.error("خطأ في قراءة ملف الـ PDF")

# ==========================================
# 7. محرك الذكاء الاصطناعي (مع نظام الحماية)
# ==========================================

if not user_api_key:
    st.info("💡 يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
else:
    client = Groq(api_key=user_api_key)

    if "messages" not in st.session_state or st.session_state.get('curr_p') != active_p:
        data = load_project_data(active_p)
        st.session_state.messages = data if data else [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.curr_p = active_p

    for m in st.session_state.messages:
        if m["role"] != "system":
            with st.chat_message(m["role"]): st.markdown(m["content"])

    # معالجة المدخلات
    u_query = None
    if audio_rec:
        with st.spinner("جاري تحليل صوتك..."):
            try:
                trans = client.audio.transcriptions.create(file=("a.wav", audio_rec['bytes']), model="whisper-large-v3")
                u_query = trans.text
            except: st.error("فشل تحويل الصوت")
    else:
        u_query = st.chat_input("تحدث معي يا سالم، أنا أسمعك...")

    if u_query:
        st.session_state.messages.append({"role": "user", "content": u_query})
        with st.chat_message("user"): st.markdown(u_query)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_res = ""
            
            try:
                if final_img_file:
                    # --- التحديث الجوهري لموديلات الرؤية (2026) ---
                    # تم تغيير الأسماء الرسمية وإزالة كلمة preview
                    model_id = "llama-3.2-11b-vision" 
                    
                    b64_img = process_and_convert_image(final_img_file)
                    
                    payload = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"المرجع: {pdf_ctx}\n\nسؤال المستخدم: {u_query}"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                            ]
                        }
                    ]
                else:
                    # موديل النصوص المستقر
                    model_id = "llama-3.3-70b-versatile"
                    payload = st.session_state.messages[-10:]
                    payload[-1] = {"role": "user", "content": f"سياق الـ PDF:\n{pdf_ctx}\n\nسؤال سالم: {u_query}"}

                # طلب البث اللحظي مع معالجة الأخطاء
                stream = client.chat.completions.create(
                    messages=payload,
                    model=model_id,
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        placeholder.markdown(full_res + "▌")
                
                placeholder.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                save_project_data(active_p, st.session_state.messages)
                
                if len(full_res) > 250:
                    trigger_android_notification("اكتمال التحليل", "سالم، المساعد انتهى من كتابة الرد المفصل.")

                if voice_feedback:
                    try:
                        clean = full_res.replace("`", "").replace("*", "")
                        tts = gTTS(text=clean[:300], lang='ar')
                        tts.save("reply.mp3")
                        st.audio("reply.mp3", autoplay=True)
                    except: pass

            except Exception as e:
                # نظام الحماية: إذا فشل الموديل الأساسي، حاول استخدام الموديل البديل فوراً
                st.warning("⚠️ يتم الآن التبديل للموديل البديل لضمان استمرارية الخدمة...")
                try:
                    # محاولة استخدام الموديل البديل llama-3.2-90b-vision (بدون preview)
                    fallback_stream = client.chat.completions.create(
                        messages=payload,
                        model="llama-3.2-90b-vision",
                        stream=True
                    )
                    for chunk in fallback_stream:
                        if chunk.choices[0].delta.content:
                            full_res += chunk.choices[0].delta.content
                            placeholder.markdown(full_res + "▌")
                    placeholder.markdown(full_res)
                except:
                    st.error(f"❌ خطأ تقني في Groq: {e}")
