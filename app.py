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
# 1. إعدادات واجهة التطبيق
# ==========================================
st.set_page_config(
    page_title="AI Companion V2 - سالم",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص المظهر (CSS)
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
# 2. جسر الإشعارات مع الأندرويد
# ==========================================
def trigger_android_notification(title, message):
    """إرسال إشعار حقيقي للهاتف"""
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
if st.button("🔔 اختبار النظام"):
    trigger_android_notification("تنبيه النظام", "تم إصلاح مشكلة الصور والموديل بنجاح!")

# ==========================================
# 3. إعدادات المجلدات والملفات
# ==========================================
PROJECTS_FOLDER = "projects"
API_KEY_FILE = "groq_key.txt"

if not os.path.exists(PROJECTS_FOLDER):
    os.makedirs(PROJECTS_FOLDER)

SYSTEM_PROMPT = """أنت 'مساعد سالم الشخصي'. أنت خبير مبرمج (Senior Developer) وصديق ذكي. 
لديك القدرة الكاملة على تحليل الصور والملفات. 
أجب دائماً باللغة العربية بأسلوب متميز."""

# ==========================================
# 4. الدوال المساعدة (تم إصلاح معالجة الصور هنا)
# ==========================================

def save_project_data(p_name, msgs):
    file_path = os.path.join(PROJECTS_FOLDER, f"{p_name}.json")
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(msgs, file, ensure_ascii=False, indent=4)

def load_project_data(p_name):
    file_path = os.path.join(PROJECTS_FOLDER, f"{p_name}.json")
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

def process_and_convert_image(image_file):
    """
    إصلاح مشكلة RGBA وتحويل الصورة لـ Base64
    """
    try:
        img = Image.open(image_file)
        
        # --- الإصلاح الأول: تحويل الصور الشفافة إلى RGB ---
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # تصغير الصورة لضمان السرعة
        img.thumbnail((1000, 1000)) 
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"فشل معالجة الصورة: {e}")
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
        st.success("تم التنشيط!")
        st.rerun()

    st.divider()

    # إدارة المشاريع
    files = os.listdir(PROJECTS_FOLDER)
    p_list = [f.replace(".json", "") for f in files if f.endswith(".json")]
    if not p_list: p_list = ["محادثة_جديدة"]
    active_p = st.selectbox("المشروع الحالي:", p_list)
    
    new_p = st.text_input("اسم مشروع جديد:")
    if st.button("➕ إنشاء"):
        if new_p.strip():
            save_project_data(new_p.strip(), [{"role": "system", "content": SYSTEM_PROMPT}])
            st.rerun()

    if st.button("🗑️ حذف الحالي"):
        try:
            os.remove(os.path.join(PROJECTS_FOLDER, f"{active_p}.json"))
            st.rerun()
        except: pass

    st.divider()

    # أدوات الإدخال
    st.subheader("🛠️ أدوات الصور")
    cam = st.camera_input("التقط صورة")
    up_img = st.file_uploader("ارفع صورة:", type=["jpg", "png", "jpeg"])
    up_pdf = st.file_uploader("ملف PDF:", type=["pdf"])
    
    active_img = cam if cam else up_img

    st.write("🎙️ صوت:")
    audio = mic_recorder(start_prompt="تحدث 🎙️", stop_prompt="إرسال 📤", key='mic')
    voice_on = st.checkbox("النطق الصوتي", value=False)

# ==========================================
# 6. استخراج نص PDF
# ==========================================
pdf_txt = ""
if up_pdf:
    try:
        reader = PdfReader(up_pdf)
        for page in reader.pages:
            pdf_txt += (page.extract_text() or "") + "\n"
    except: pass

# ==========================================
# 7. المنطق الذكي (تم تحديث الموديل هنا)
# ==========================================

if not user_api_key:
    st.info("💡 أدخل مفتاح API للبدء.")
else:
    client = Groq(api_key=user_api_key)

    if "messages" not in st.session_state or st.session_state.get('curr_p') != active_p:
        data = load_project_data(active_p)
        st.session_state.messages = data if data else [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.curr_p = active_p

    for m in st.session_state.messages:
        if m["role"] != "system":
            with st.chat_message(m["role"]): st.markdown(m["content"])

    u_query = None
    if audio:
        with st.spinner("تحليل الصوت..."):
            try:
                trans = client.audio.transcriptions.create(file=("a.wav", audio['bytes']), model="whisper-large-v3")
                u_query = trans.text
            except: st.error("فشل الصوت")
    else:
        u_query = st.chat_input("اكتب سؤالك هنا...")

    if u_query:
        st.session_state.messages.append({"role": "user", "content": u_query})
        with st.chat_message("user"): st.markdown(u_query)

        with st.chat_message("assistant"):
            place = st.empty()
            full_res = ""
            
            try:
                if active_img:
                    # --- الإصلاح الثاني: استخدام الموديل الجديد ---
                    # استبدلنا 11b القديم بـ 90b الجديد والقوي
                    model_id = "llama-3.2-90b-vision-preview" 
                    
                    b64 = process_and_convert_image(active_img)
                    if b64:
                        payload = [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"المرجع: {pdf_txt}\n\nالسؤال: {u_query}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                                ]
                            }
                        ]
                    else:
                        st.error("فشل في تجهيز الصورة")
                        st.stop()
                else:
                    model_id = "llama-3.3-70b-versatile"
                    payload = st.session_state.messages[-10:]
                    payload[-1] = {"role": "user", "content": f"المرجع: {pdf_txt}\n\n{u_query}"}

                stream = client.chat.completions.create(
                    messages=payload,
                    model=model_id, # استخدام الموديل المحدث
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        place.markdown(full_res + "▌")
                
                place.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                save_project_data(active_p, st.session_state.messages)
                
                if len(full_res) > 200:
                    trigger_android_notification("تم الرد", "سالم، الإجابة جاهزة.")

                if voice_on:
                    try:
                        clean = full_res.replace("`", "").replace("*", "")
                        tts = gTTS(text=clean[:300], lang='ar')
                        tts.save("r.mp3")
                        st.audio("r.mp3", autoplay=True)
                    except: pass

            except Exception as e:
                st.error(f"حدث خطأ: {e}")
