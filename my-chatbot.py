import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import os
import json
import hashlib
import base64
import random
from datetime import datetime, timedelta
from google.api_core.exceptions import ResourceExhausted

# Sayfanın genel yapılandırması
st.set_page_config(
    page_title="NotMentor Akıllı Ders Asistanı",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)


# User Authentication System
class AuthSystem:
    def __init__(self):
        # Create users directory if it doesn't exist
        if not os.path.exists("users"):
            os.makedirs("users")

        # Load session data if exists
        self.session_file = "users/session.json"
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    self.session_data = json.load(f)
            except json.JSONDecodeError:
                # JSON dosyası bozuksa varsayılan değerlerle başlat
                self.session_data = {"last_user": None}
                self.save_session()
        else:
            self.session_data = {"last_user": None}

    def save_session(self):
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"Oturum kaydedilirken hata oluştu: {e}")

    def get_last_user(self):
        return self.session_data.get("last_user")

    def set_last_user(self, username):
        self.session_data["last_user"] = username
        self.save_session()

    def register_user(self, username, password):
        user_file = f"users/{username}.json"

        # Check if user already exists
        if os.path.exists(user_file):
            return False, "Kullanıcı adı zaten alınmış."

        # Hash password
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        # Create user with proper JSON structure
        user_data = {
            "username": username,
            "password": hashed_pw,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pdfs": [],
            "progress": {},
            "marked_questions": {},
            "api_key": None
        }

        try:
            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)

            # Set as last user
            self.set_last_user(username)

            return True, "Kayıt başarılı! Şimdi giriş yapabilirsiniz."
        except Exception as e:
            st.error(f"Kullanıcı kaydedilirken hata oluştu: {e}")
            return False, "Kayıt sırasında bir hata oluştu."

    def login_user(self, username, password):
        user_file = f"users/{username}.json"

        # Check if user exists
        if not os.path.exists(user_file):
            return False, "Kullanıcı bulunamadı."

        try:
            # Get user data
            with open(user_file, "r", encoding="utf-8") as f:
                user_data = json.load(f)

            # Verify password
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            if user_data["password"] != hashed_pw:
                return False, "Şifre yanlış."

            # Set as last user
            self.set_last_user(username)

            return True, "Giriş başarılı!"
        except json.JSONDecodeError:
            st.error(f"Kullanıcı verisi okunamadı: {username}")
            return False, "Kullanıcı verisi bozuk."
        except Exception as e:
            st.error(f"Giriş sırasında hata oluştu: {e}")
            return False, "Giriş sırasında bir hata oluştu."

    def get_user_api_key(self, username):
        user_file = f"users/{username}.json"
        if os.path.exists(user_file):
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                return user_data.get("api_key")
            except json.JSONDecodeError:
                st.error(f"Kullanıcı verisi okunamadı: {username}")
                return None
        return None

    def update_user_api_key(self, username, new_api_key):
        user_file = f"users/{username}.json"
        if os.path.exists(user_file):
            with open(user_file, "r", encoding="utf-8") as f:
                user_data = json.load(f)

            user_data["api_key"] = new_api_key

            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)

            return True, "API anahtarı başarıyla güncellendi."
        return False, "Kullanıcı bulunamadı."

    def get_user_pdfs(self, username):
        user_file = f"users/{username}.json"

        if not os.path.exists(user_file):
            return []

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        return user_data.get("pdfs", [])

    def get_user_progress(self, username, pdf_id, topic):
        user_file = f"users/{username}.json"

        if not os.path.exists(user_file):
            return 0

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        progress = user_data.get("progress", {})
        pdf_progress = progress.get(pdf_id, {})
        return pdf_progress.get(topic, 0)

    def update_user_progress(self, username, pdf_id, topic, score):
        user_file = f"users/{username}.json"

        if not os.path.exists(user_file):
            return False

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if "progress" not in user_data:
            user_data["progress"] = {}

        if pdf_id not in user_data["progress"]:
            user_data["progress"][pdf_id] = {}

        user_data["progress"][pdf_id][topic] = score

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

        return True

    def add_pdf_to_user(self, username, pdf_id):
        user_file = f"users/{username}.json"

        if not os.path.exists(user_file):
            return False

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if pdf_id not in user_data.get("pdfs", []):
            if "pdfs" not in user_data:
                user_data["pdfs"] = []
            user_data["pdfs"].append(pdf_id)

            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)

        return True

    def remove_pdf_from_user(self, username, pdf_id):
        user_file = f"users/{username}.json"

        if not os.path.exists(user_file):
            return False

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if pdf_id in user_data.get("pdfs", []):
            user_data["pdfs"].remove(pdf_id)

            # Remove progress data for this PDF
            if "progress" in user_data and pdf_id in user_data["progress"]:
                del user_data["progress"][pdf_id]

            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)

        return True


# CSS stillerini ekleyelim
st.markdown("""
<style>
    /* Genel stiller */
    :root {
        --primary-color: #2563eb;
        --secondary-color: #1e40af;
        --background-color: #f1f5f9;
        --text-color: #1e293b;
        --card-bg: #ffffff;
        --border-color: #e2e8f0;
        --success-color: #10b981;
        --error-color: #ef4444;
        --warning-color: #f59e0b;
    }

    body {
        font-family: 'Inter', sans-serif;
        background-color: var(--background-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
    }

    /* Streamlit varsayılan stillerini düzenle */
    .stApp {
        background-color: var(--background-color);
    }

    .main .block-container {
        padding: 2rem 1rem;
        max-width: 100%;
    }

    /* Ana başlık */
    .main-header {
        text-align: center;
        color: var(--primary-color);
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .sub-header {
        text-align: center;
        color: var(--text-color);
        font-size: 1.2rem;
        margin-bottom: 2rem;
        opacity: 0.8;
    }

    /* Yan panel */
    .sidebar {
        background-color: var(--card-bg);
        padding: 1.5rem;
        border-right: 1px solid var(--border-color);
    }

    .sidebar-header {
        color: var(--primary-color);
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        padding-bottom: 0.8rem;
        border-bottom: 2px solid var(--border-color);
    }

    /* Kartlar */
    .card {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid var(--border-color);
        transition: all 0.3s ease;
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }

    /* Butonlar */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background-color: var(--secondary-color);
        transform: translateY(-1px);
    }

    /* Form elemanları */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 8px;
        border: 2px solid var(--border-color);
        padding: 0.6rem 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }

    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    /* Sohbet alanı */
    .chat-container {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 1.5rem;
        height: 500px;
        overflow-y: auto;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid var(--border-color);
    }

    .chat-message {
        max-width: 80%;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        position: relative;
        animation: fadeIn 0.3s ease;
        line-height: 1.5;
    }

    .user-message {
        background-color: var(--primary-color);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }

    .bot-message {
        background-color: var(--card-bg);
        color: var(--text-color);
        margin-right: auto;
        border-bottom-left-radius: 4px;
        border: 1px solid var(--border-color);
    }

    .message-time {
        font-size: 0.75rem;
        opacity: 0.7;
        margin-top: 0.5rem;
        text-align: right;
    }

    /* Tab menüsü */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        background-color: var(--card-bg);
        color: var(--text-color);
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }

    /* Bilgi kutuları */
    .info-box {
        background-color: #e0f2fe;
        border-left: 4px solid var(--primary-color);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .success-box {
        background-color: #dcfce7;
        border-left: 4px solid var(--success-color);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .warning-box {
        background-color: #fef3c7;
        border-left: 4px solid var(--warning-color);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .error-box {
        background-color: #fee2e2;
        border-left: 4px solid var(--error-color);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    /* Animasyonlar */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.3s ease forwards;
    }

    /* Responsive tasarım */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }

        .main-header {
            font-size: 2rem;
        }

        .chat-container {
            height: 400px;
        }
    }
</style>
""", unsafe_allow_html=True)

# API anahtarını saklamak için güvenli yol
API_KEY = "AIzaSyCWq0f2nQybbzl7pGg7JLPWwaYvoOidpmE"  # Buraya API anahtarınızı girin


def get_api_key():
    return API_KEY


# Animasyon dosyaları için yardımcı fonksiyon
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()


# Confetti animasyonu için JavaScript kodu
def load_confetti_js():
    return """
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
    function throwConfetti() {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    }
    </script>
    """


# Doğru cevap için animasyon çalıştır
def trigger_confetti():
    st.markdown(
        """
        <script>
        setTimeout(function() {
            throwConfetti();
        }, 500);
        </script>
        """,
        unsafe_allow_html=True
    )


# Verilerin tutulacağı klasörleri oluştur
if not os.path.exists("pdf_storage"):
    os.makedirs("pdf_storage")
if not os.path.exists("pdf_metadata"):
    os.makedirs("pdf_metadata")
if not os.path.exists("question_banks"):
    os.makedirs("question_banks")
if not os.path.exists("chat_histories"):
    os.makedirs("chat_histories")

# Auth sistemini başlat
auth = AuthSystem()

# Session state kontrolleri
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"  # login veya register

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "quiz"  # quiz veya chat

if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {
        "current_pdf": None,
        "current_topic": None,
        "current_question_index": 0,
        "total_questions": 0,
        "correct_answers": 0,
        "answered_questions": [],
        "topic_questions": [],
        "marked_questions": []  # İşaretlenen sorular için yeni alan
    }

if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

if "answer_status" not in st.session_state:
    st.session_state.answer_status = None  # correct, wrong veya None

if "selected_pdf_details" not in st.session_state:
    st.session_state.selected_pdf_details = None

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Buton durumlarını takip etmek için session state
if "last_button_click" not in st.session_state:
    st.session_state.last_button_click = {}


def check_button_cooldown(button_id):
    return True


def update_button_click_time(button_id):
    st.session_state.last_button_click[button_id] = datetime.now()


# Gemini API'yi yapılandır
@st.cache_resource
def setup_genai_model():
    api_key = get_api_key()
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            return model
        except Exception as e:
            st.sidebar.error(f"API hatası: {e}")
            return None
    return None


# PDF içeriğini önbelleğe alma
@st.cache_data
def extract_pdf_text(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""

        # PDF'deki her sayfayı oku
        for page in pdf_reader.pages:
            page_text = page.extract_text()

            # Başlıkları ve önemli metinleri koru
            lines = page_text.split('\n')
            for line in lines:
                # Büyük harfle yazılmış satırları koru
                if line.isupper() or line.strip().startswith(
                        ('I.', 'II.', 'III.', 'IV.', 'V.', '1.', '2.', '3.', '4.', '5.')):
                    text += line + '\n'
                # Diğer metinleri de ekle
                text += line + '\n'

        return text
    except Exception as e:
        st.error(f"PDF okuma hatası: {e}")
        return ""


# PDF metaverilerini kaydet
def save_pdf_metadata(pdf_file, konular, username):
    # PDF için benzersiz kimlik oluştur
    pdf_hash = hashlib.md5(pdf_file.getvalue()).hexdigest()

    # PDF'i kaydet
    pdf_path = f"pdf_storage/{pdf_hash}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.getvalue())

    # Metaverileri kaydet
    metadata = {
        "filename": pdf_file.name,
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topics": konular,
        "path": pdf_path,
        "owner": username
    }

    with open(f"pdf_metadata/{pdf_hash}.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    # Kullanıcı için PDF kaydet
    auth.add_pdf_to_user(username, pdf_hash)

    return pdf_hash


# Bir PDF dosyasını sil
def delete_pdf(pdf_id, username):
    # Önce metadata dosyasını kontrol et
    metadata_path = f"pdf_metadata/{pdf_id}.json"
    if os.path.exists(metadata_path):
        # Metadata içeriğini oku
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Sahibi kontrol et
        if metadata.get("owner") == username:
            # PDF dosyasını sil
            if os.path.exists(metadata["path"]):
                os.remove(metadata["path"])

            # Soru bankası dosyasını sil
            question_bank_path = f"question_banks/{pdf_id}.json"
            if os.path.exists(question_bank_path):
                os.remove(question_bank_path)

            # Sohbet geçmişi dosyasını sil
            chat_history_path = f"chat_histories/{pdf_id}.json"
            if os.path.exists(chat_history_path):
                os.remove(chat_history_path)

            # Metadata dosyasını sil
            os.remove(metadata_path)

            # Kullanıcıdan PDF'i kaldır
            auth.remove_pdf_from_user(username, pdf_id)

            return True

    return False


# PDF metadata bilgilerini yükle
def load_pdf_metadata(pdf_id):
    metadata_path = f"pdf_metadata/{pdf_id}.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# PDF içeriğini yükle
def load_pdf_content(pdf_path):
    try:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = "".join(page.extract_text() for page in pdf_reader.pages)
                return text
        return ""
    except Exception as e:
        st.error(f"PDF içerik yükleme hatası: {e}")
        return ""


# PDF'lerin konularını çıkar
def extract_topics(text):
    model = setup_genai_model()
    if not model:
        return ["Genel"]
    short_text = text[:1000]
    prompt = f"""
    Ders notundan en önemli konuları belirle (en fazla 2 konu).
    Yanıt formatı: ["Konu1", "Konu2"]
    Not: Konu sayısı 1 veya 2 olabilir, illa 2 konu olması gerekmez.
    Not: {short_text}
    """
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "")
        topics = json.loads(response_text)
        valid_topics = []
        for topic in topics:
            if len(topic.strip()) >= 3 and topic.lower() not in ["genel", "giriş", "önsöz"]:
                valid_topics.append(topic)
        if not valid_topics:
            st.warning("Geçerli konu bulunamadı.")
            return ["Genel"]
        return valid_topics[:2]
    except Exception as e:
        st.warning(f"Konu çıkarma hatası: {e}")
        return ["Genel"]


# Soru bankasını diske kaydet
def save_question_bank(pdf_id, questions_by_topic):
    question_bank = {
        "topics": {},
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    for topic, questions in questions_by_topic.items():
        question_bank["topics"][topic] = questions

    with open(f"question_banks/{pdf_id}.json", "w", encoding="utf-8") as f:
        json.dump(question_bank, f, ensure_ascii=False, indent=4)


# Soru bankasını diskten yükle
def load_question_bank(pdf_id):
    question_bank_path = f"question_banks/{pdf_id}.json"
    if os.path.exists(question_bank_path):
        with open(question_bank_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"topics": {}}


# PDF'den sorular oluştur
def generate_questions(text, topics):
    model = setup_genai_model()
    if not model:
        return {}
    short_text = text[:1000]
    topics_str = ", ".join([f'"{topic}"' for topic in topics])
    prompt = f'''
    GÖREV: Verilen konular için çoktan seçmeli sorular oluştur.

    ÇIKTI FORMATI:
    Sadece ve sadece aşağıdaki JSON formatında yanıt ver. Başka hiçbir metin veya açıklama ekleme.

    {{
        "{topics[0]}": [
            {{
                "q": "SORU_METNİ",
                "a": "A) DOĞRU_CEVAP",
                "o": [
                    "A) SEÇENEK_1",
                    "B) SEÇENEK_2", 
                    "C) SEÇENEK_3",
                    "D) SEÇENEK_4"
                ],
                "explanation": {{
                    "correct": "DOĞRU_CEVAP_AÇIKLAMASI",
                    "incorrect": {{
                        "A) SEÇENEK_1": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "B) SEÇENEK_2": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "C) SEÇENEK_3": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "D) SEÇENEK_4": "NEDEN_YANLIŞ_AÇIKLAMASI"
                    }}
                }}
            }}
        ],
        "{topics[1]}": [
            {{
                "q": "SORU_METNİ",
                "a": "A) DOĞRU_CEVAP",
                "o": [
                    "A) SEÇENEK_1",
                    "B) SEÇENEK_2", 
                    "C) SEÇENEK_3",
                    "D) SEÇENEK_4"
                ],
                "explanation": {{
                    "correct": "DOĞRU_CEVAP_AÇIKLAMASI",
                    "incorrect": {{
                        "A) SEÇENEK_1": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "B) SEÇENEK_2": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "C) SEÇENEK_3": "NEDEN_YANLIŞ_AÇIKLAMASI",
                        "D) SEÇENEK_4": "NEDEN_YANLIŞ_AÇIKLAMASI"
                    }}
                }}
            }}
        ]
    }}

    ZORUNLU KURALLAR:
    1. Yanıt SADECE JSON formatında olmalı
    2. Her konu için TAM 10 soru oluştur
    3. Her soruda TAM 4 şık olmalı (A, B, C, D)
    4. Doğru cevap her zaman "a" alanında belirtilmeli
    5. Tüm şıklar "o" dizisinde sıralı olmalı
    6. Her şık için açıklama MUTLAKA olmalı
    7. Tüm metinler Türkçe olmalı
    8. JSON sözdizimi kurallarına KESINLIKLE uy:
       - Her string çift tırnak içinde olmalı
       - Her nesne süslü parantez {{}} içinde olmalı
       - Her dizi köşeli parantez [] içinde olmalı
       - Her öğe virgülle ayrılmalı
       - Son öğeden sonra virgül OLMAMALI
    9. Belirtilen alanlar dışında ASLA yeni alan ekleme
    10. JSON formatı dışında HİÇBİR metin veya açıklama ekleme
    11. Konu başlıkları tam olarak verilen konu isimleriyle aynı olmalı
    12. Her konu için ayrı bir dizi oluştur ve her dizide 10 soru olmalı
    13. Vereceğin mesajda kesinlikle başka bir metin olmamalı
    14. Vereceğin mesajda alınan yanıt vb. mesajlar olmamalı sadece JSON formatında yanıt vereceksin

    KONU VE İÇERİK:
    Konular: {topics_str}
    İçerik: {short_text}
    '''
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # JSON formatını temizle
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

        try:
            questions_by_topic = json.loads(response_text)
        except json.JSONDecodeError as e:
            st.error(f"JSON parse hatası: {e}")
            st.error(f"Alınan yanıt: {response_text}")
            return {}

        formatted_questions = {}
        for topic, questions in questions_by_topic.items():
            valid_questions = []
            for q in questions:
                if (isinstance(q, dict) and
                        "q" in q and
                        "a" in q and
                        "o" in q and
                        "explanation" in q and
                        len(q["o"]) == 4):
                    valid_questions.append({
                        "question": q["q"],
                        "options": q["o"],
                        "correct_answer": q["a"],
                        "explanation": q["explanation"]
                    })
            if len(valid_questions) < 10:
                st.warning(f"{topic} için 10 soru oluşturulamadı, {len(valid_questions)} soru üretildi.")
            formatted_questions[topic] = valid_questions[:10]  # En fazla 10 soru
        return formatted_questions
    except Exception as e:
        st.error(f"Soru oluşturma hatası: {e}")
        return {}


# PDF kaydetme ve soru oluşturma işlemi
def save_pdf_and_generate_questions(uploaded_file, topic_options, username):
    try:
        pdf_text = extract_pdf_text(uploaded_file)
        if not pdf_text:
            st.error("PDF içeriği okunamadı!")
            return None
        pdf_id = save_pdf_metadata(uploaded_file, topic_options, username)
        if not pdf_id:
            st.error("PDF kaydedilemedi!")
            return None
        with st.spinner("Sorular oluşturuluyor..."):
            extracted_topics = extract_topics(pdf_text)
            questions_by_topic = generate_questions(pdf_text, extracted_topics)
            total_questions = sum(len(questions) for questions in questions_by_topic.values())
            if total_questions == 0:
                st.error("Hiç soru oluşturulamadı! Lütfen PDF içeriğini kontrol edin.")
                return None
            save_question_bank(pdf_id, questions_by_topic)
            return pdf_id, total_questions
    except Exception as e:
        st.error(f"PDF işleme hatası: {e}")
        return None


# Sohbet geçmişini kaydet
def save_chat_history(pdf_id, messages):
    chat_history = {"messages": messages}
    with open(f"chat_histories/{pdf_id}.json", "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=4)


# Sohbet geçmişini yükle
def load_chat_history(pdf_id):
    chat_history_path = f"chat_histories/{pdf_id}.json"
    if os.path.exists(chat_history_path):
        with open(chat_history_path, "r", encoding="utf-8") as f:
            chat_history = json.load(f)
            return chat_history.get("messages", [])
    return []


# Sohbet yanıtı oluştur
def generate_chat_response(pdf_content, messages):
    model = setup_genai_model()
    if not model:
        return "API anahtarı yapılandırması gerekiyor."

    # Sohbet geçmişini formatla
    chat_history = []
    for msg in messages[-3:]:  # Son 3 mesajı kullan
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    # Bağlamı ekle
    context = f"""
    Ders notu: {pdf_content[:500]}  # İlk 500 karakteri kullan

    Son mesaja kısa ve öz yanıt ver.
    """

    try:
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(context + "\n\nEn son mesaja yanıt ver:")
        return response.text
    except Exception as e:
        return f"Yanıt oluşturulurken bir hata oluştu: {e}"


# İşaretlenen soruları kaydet
def save_marked_question(username, question, answer, topic, explanation):
    user_file = f"users/{username}.json"
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if "marked_questions" not in user_data:
            user_data["marked_questions"] = {}

        if topic not in user_data["marked_questions"]:
            user_data["marked_questions"][topic] = []

        # Sorunun zaten işaretlenip işaretlenmediğini kontrol et
        for q in user_data["marked_questions"][topic]:
            if q["question"] == question:
                return  # Soru zaten işaretlenmiş

        user_data["marked_questions"][topic].append({
            "question": question,
            "answer": answer,
            "explanation": explanation,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)


# İşaretlenen soruları yükle
def load_marked_questions(username):
    user_file = f"users/{username}.json"
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        return user_data.get("marked_questions", {})
    return {}


# İşaretlenen soruyu güncelle
def update_marked_question(username, topic, question_index, new_topic, new_note):
    user_file = f"users/{username}.json"
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if "marked_questions" in user_data and topic in user_data["marked_questions"]:
            if 0 <= question_index < len(user_data["marked_questions"][topic]):
                # Eski konudan soruyu al
                question_data = user_data["marked_questions"][topic].pop(question_index)

                # Yeni konuya ekle
                if new_topic not in user_data["marked_questions"]:
                    user_data["marked_questions"][new_topic] = []

                question_data["note"] = new_note
                user_data["marked_questions"][new_topic].append(question_data)

                # Eski konu boşsa sil
                if not user_data["marked_questions"][topic]:
                    del user_data["marked_questions"][topic]

                with open(user_file, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, ensure_ascii=False, indent=4)
                return True
    return False


# İşaretlenen soruyu sil
def delete_marked_question(username, topic, question_index):
    user_file = f"users/{username}.json"
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if "marked_questions" in user_data and topic in user_data["marked_questions"]:
            if 0 <= question_index < len(user_data["marked_questions"][topic]):
                user_data["marked_questions"][topic].pop(question_index)

                # Konu boşsa sil
                if not user_data["marked_questions"][topic]:
                    del user_data["marked_questions"][topic]

                with open(user_file, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, ensure_ascii=False, indent=4)
                return True
    return False


# Ana uygulama mantığı
def main():
    # Yan panel
    with st.sidebar:
        st.markdown("<div class='sidebar-header'>📝 Kullanıcı Paneli</div>", unsafe_allow_html=True)

        # Kullanıcı giriş durumu
        if st.session_state.authenticated:
            st.markdown(f"""
            <div class='card'>
                <h4>👤 Kullanıcı Bilgileri</h4>
                <p><b>Kullanıcı Adı:</b> {st.session_state.username}</p>
                <p><b>Son Giriş:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Çıkış Yap", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.username = ""
                st.rerun()

    # Ana başlık
    st.markdown("<h1 class='main-header'>📘 Akıllı Ders Asistanı</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>PDF'lerinizden öğrenin, sorular sorun, bilginizi test edin</p>",
                unsafe_allow_html=True)

    # Kullanıcı giriş ekranı
    if not st.session_state.authenticated:
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)

        # Son kullanıcıyı kontrol et
        last_user = auth.get_last_user()
        if last_user:
            st.info(f"Son giriş yapan kullanıcı: {last_user}")
            if st.button("Son Kullanıcı ile Giriş Yap"):
                st.session_state.authenticated = True
                st.session_state.username = last_user
                st.session_state.api_key = auth.get_user_api_key(last_user)
                st.rerun()

        # Login-Register tab seçimi
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Giriş Yap", use_container_width=True):
                st.session_state.auth_mode = "login"
        with col2:
            if st.button("Kayıt Ol", use_container_width=True):
                st.session_state.auth_mode = "register"

        # Giriş formu
        if st.session_state.auth_mode == "login":
            st.markdown("<h3 style='text-align: center;'>Giriş Yap</h3>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Kullanıcı Adı:")
                password = st.text_input("Şifre:", type="password")
                submit_button = st.form_submit_button("Giriş Yap")

                if submit_button:
                    if username and password:
                        success, message = auth.login_user(username, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.api_key = auth.get_user_api_key(username)
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Lütfen kullanıcı adı ve şifre girin.")

        # Kayıt formu
        else:
            st.markdown("<h3 style='text-align: center;'>Kayıt Ol</h3>", unsafe_allow_html=True)
            with st.form("register_form"):
                username = st.text_input("Kullanıcı Adı:")
                password = st.text_input("Şifre:", type="password")
                password_confirm = st.text_input("Şifre Tekrar:", type="password")
                submit_button = st.form_submit_button("Kayıt Ol")

                if submit_button:
                    if username and password and password_confirm:
                        if password == password_confirm:
                            success, message = auth.register_user(username, password)
                            if success:
                                st.success(message)
                                st.session_state.auth_mode = "login"
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Şifreler eşleşmiyor!")
                    else:
                        st.warning("Lütfen tüm alanları doldurun.")

        st.markdown("</div>", unsafe_allow_html=True)
        return

    # API anahtarı kontrolü
    if not get_api_key():
        st.error("API anahtarı bulunamadı! Lütfen tekrar giriş yapın.")
        st.session_state.authenticated = False
        st.rerun()

    # Ana sayfa içeriği
    tab1, tab2, tab3, tab4 = st.tabs(["📚 PDF'lerim", "🧠 Quiz", "💬 Asistan", "📖 Soru Defteri"])

    # PDF YÖNETİMİ SAYFASI
    with tab1:
        st.markdown("<h2>📚 PDF Dosyalarım</h2>", unsafe_allow_html=True)

        # PDF yükleme bölümü
        with st.expander("Yeni PDF Yükle", expanded=True):
            uploaded_file = st.file_uploader("Bir PDF dosyası yükleyin", type="pdf")

            if uploaded_file:
                # PDF metnini çıkar
                pdf_text = extract_pdf_text(uploaded_file)

                # Konuları otomatik belirle
                with st.spinner("PDF içeriği analiz ediliyor..."):
                    extracted_topics = extract_topics(pdf_text)

                # Konu seçimi
                st.markdown("<div class='topic-selector'>", unsafe_allow_html=True)
                st.write("**PDF Konuları:**")

                # Var olan konular
                topic_options = st.multiselect(
                    "Konuları seçin veya değiştirin",
                    options=extracted_topics + ["Diğer"],
                    default=extracted_topics
                )

                # Yeni konu ekleme
                if "Diğer" in topic_options:
                    new_topic = st.text_input("Yeni konu girin:")
                    if new_topic and new_topic not in topic_options:
                        topic_options.append(new_topic)

                    # "Diğer" seçeneğini kaldır
                    if "Diğer" in topic_options:
                        topic_options.remove("Diğer")

                st.markdown("</div>", unsafe_allow_html=True)

                # PDF kaydetme butonu
                if st.button("PDF'i Kaydet ve Sorular Oluştur", key="save_pdf_button"):
                    if check_button_cooldown("save_pdf_button"):
                        with st.spinner("PDF kaydediliyor ve sorular hazırlanıyor..."):
                            result = save_pdf_and_generate_questions(uploaded_file, topic_options,
                                                                     st.session_state.username)

                            if result:
                                pdf_id, total_questions = result
                                st.success(f"PDF kaydedildi ve toplam {total_questions} soru oluşturuldu!")
                                trigger_confetti()
                                update_button_click_time("save_pdf_button")
                                st.rerun()

        # PDF listesi
        st.markdown("<h3>Yüklenen PDF'ler</h3>", unsafe_allow_html=True)
        pdf_ids = auth.get_user_pdfs(st.session_state.username)

        if not pdf_ids:
            st.info("Henüz yüklenen PDF bulunmuyor. Yukarıdan bir PDF yükleyebilirsiniz.")
        else:
            for pdf_id in pdf_ids:
                metadata = load_pdf_metadata(pdf_id)
                if metadata:
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(f"""
                        <div class='pdf-list-item'>
                            <span class='pdf-title'>{metadata["filename"]}</span>
                            <div class='topic-list'>
                                {" ".join([f"<span class='topic-tag'>{topic}</span>" for topic in metadata["topics"]])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        if st.button("🗑️", key=f"delete_{pdf_id}"):
                            delete_pdf(pdf_id, st.session_state.username)
                            st.success("PDF başarıyla silindi!")
                            st.rerun()

                    # PDF seçme butonu
                    if st.button("Bu PDF ile Çalış", key=f"select_{pdf_id}"):
                        st.session_state.selected_pdf_details = {
                            "id": pdf_id,
                            "metadata": metadata
                        }

                        # Soru bankasını yükle
                        question_bank = load_question_bank(pdf_id)

                        # Quiz durumunu ayarla
                        st.session_state.quiz_state = {
                            "current_pdf": pdf_id,
                            "current_topic": None,
                            "current_question_index": 0,
                            "total_questions": 0,
                            "correct_answers": 0,
                            "answered_questions": [],
                            "topic_questions": [],
                            "marked_questions": []
                        }

                        # Sohbet geçmişini yükle
                        st.session_state.chat_messages = load_chat_history(pdf_id)

                        st.success(f"{metadata['filename']} dosyası seçildi!")
                        st.session_state.current_tab = "quiz"
                        st.rerun()

    # QUIZ SAYFASI
    with tab2:
        st.markdown("<h2>🧠 Quiz</h2>", unsafe_allow_html=True)

        if not st.session_state.selected_pdf_details:
            st.info("Quiz başlatmak için önce PDF'lerim sekmesinden bir PDF seçin.")
        else:
            pdf_id = st.session_state.selected_pdf_details["id"]
            metadata = st.session_state.selected_pdf_details["metadata"]

            st.markdown(f"""
            <div class='card'>
                <h3>{metadata['filename']}</h3>
                <div class='topic-list'>
                    {" ".join([f"<span class='topic-tag'>{topic}</span>" for topic in metadata["topics"]])}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Soru bankasını yükle
            question_bank = load_question_bank(pdf_id)
            topics = list(question_bank["topics"].keys())

            if not topics:
                st.warning("Bu PDF için henüz soru bankası oluşturulmamış.")
            else:
                # İşaretlenen soruları yükle
                marked_questions = load_marked_questions(st.session_state.username)
                st.session_state.quiz_state["marked_questions"] = marked_questions

                # Konu seçimi
                if st.session_state.quiz_state["current_topic"] is None:
                    st.markdown("<h3>Quiz için konu seçin</h3>", unsafe_allow_html=True)

                    for topic in topics:
                        topic_questions = question_bank["topics"].get(topic, [])
                        question_count = len(topic_questions)

                        # İlerleme yüzdesini al
                        progress = auth.get_user_progress(
                            st.session_state.username,
                            st.session_state.selected_pdf_details["id"],
                            topic
                        )

                        # İlerleme çubuğu
                        st.markdown(f"""
                        <div class='topic-card'>
                            <div class='topic-header'>
                                <h4>{topic}</h4>
                                <span class='badge'>{question_count} soru</span>
                            </div>
                            <div class='progress-container'>
                                <div class='progress-bar' style='width: {progress}%;'></div>
                            </div>
                            <div class='progress-text'>İlerleme: %{progress:.1f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"{topic} ile Devam Et", key=f"topic_{topic}"):
                            st.session_state.quiz_state["current_topic"] = topic
                            st.session_state.quiz_state["topic_questions"] = topic_questions
                            st.session_state.quiz_state["total_questions"] = len(topic_questions)
                            st.session_state.quiz_state["current_question_index"] = 0
                            st.session_state.quiz_state["correct_answers"] = 0
                            st.session_state.quiz_state["answered_questions"] = []
                            st.session_state.show_answer = False
                            st.session_state.answer_status = None
                            st.rerun()

                # Quiz soruları
                else:
                    topic = st.session_state.quiz_state["current_topic"]
                    questions = st.session_state.quiz_state["topic_questions"]
                    current_index = st.session_state.quiz_state["current_question_index"]
                    total_questions = st.session_state.quiz_state["total_questions"]

                    # Quiz'i bitir butonu
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        if st.button("⬅️ Geri"):
                            st.session_state.quiz_state["current_topic"] = None
                            st.rerun()

                    # İşaretlenen sorular butonu
                    with col2:
                        if st.button("📌 İşaretlenen Sorular"):
                            st.session_state.quiz_state["current_topic"] = "marked"
                            st.rerun()

                    # İşaretlenen soruları göster
                    if st.session_state.quiz_state["current_topic"] == "marked":
                        st.markdown("<h3>📌 İşaretlenen Sorular</h3>", unsafe_allow_html=True)

                        if not marked_questions:
                            st.info("Henüz işaretlenmiş soru bulunmuyor.")
                        else:
                            for question_id in marked_questions:
                                question = next((q for q in questions if q["question"] == question_id), None)
                                if question:
                                    st.markdown(f"""
                                    <div class='card'>
                                        <h4>Soru:</h4>
                                        <p>{question["question"]}</p>
                                        <h4>Doğru Cevap:</h4>
                                        <p>{question["correct_answer"]}</p>
                                        <h4>Açıklama:</h4>
                                        <p>{question["explanation"]}</p>
                                    </div>
                                    """, unsafe_allow_html=True)

                        if st.button("Quiz'e Dön"):
                            st.session_state.quiz_state["current_topic"] = topic
                            st.rerun()

                    # Normal quiz akışı
                    else:
                        # İlerleme çubuğu
                        st.markdown(f"""
                        <div class='quiz-progress'>
                            <div class='quiz-progress-bar'>
                                <div class='quiz-progress-fill' style='width: {(current_index + 1) / total_questions * 100}%;'></div>
                            </div>
                            <div class='quiz-progress-text'>Soru {current_index + 1}/{total_questions}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if current_index < total_questions:
                            current_question = questions[current_index]

                            st.markdown(f"""
                            <div class='quiz-card'>
                                <h3>Soru {current_index + 1}:</h3>
                                <p>{current_question["question"]}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            is_marked = False
                            marked_questions = load_marked_questions(st.session_state.username)
                            for topic_questions in marked_questions.values():
                                for q in topic_questions:
                                    if q["question"] == current_question["question"]:
                                        is_marked = True
                                        break
                                if is_marked:
                                    break
                            if st.button("📌 İşaretle" if not is_marked else "❌ İşareti Kaldır",
                                         key=f"mark_{current_index}"):
                                if check_button_cooldown(f"mark_{current_index}"):
                                    if not is_marked:
                                        save_marked_question(
                                            st.session_state.username,
                                            current_question["question"],
                                            current_question["correct_answer"],
                                            st.session_state.quiz_state["current_topic"],
                                            current_question["explanation"]
                                        )
                                    else:
                                        for topic in marked_questions:
                                            marked_questions[topic] = [q for q in marked_questions[topic] if
                                                                       q["question"] != current_question["question"]]
                                        marked_questions = {k: v for k, v in marked_questions.items() if v}
                                        user_file = f"users/{st.session_state.username}.json"
                                        if os.path.exists(user_file):
                                            with open(user_file, "r", encoding="utf-8") as f:
                                                user_data = json.load(f)
                                            user_data["marked_questions"] = marked_questions
                                            with open(user_file, "w", encoding="utf-8") as f:
                                                json.dump(user_data, f, ensure_ascii=False, indent=4)
                                    update_button_click_time(f"mark_{current_index}")
                                    st.rerun()
                            answered = current_index in st.session_state.quiz_state["answered_questions"]
                            selected_option = st.session_state.get(f"selected_option_{current_index}", None)
                            for option in current_question["options"]:
                                option_text = option.strip()
                                is_selected = (selected_option == option_text)
                                is_correct = (option_text == current_question["correct_answer"])
                                if answered:
                                    if is_selected and is_correct:
                                        button_style = "background-color:#22c55e;color:white;"  # Yeşil
                                    elif is_selected and not is_correct:
                                        button_style = "background-color:#ef4444;color:white;"  # Kırmızı
                                    elif is_correct:
                                        button_style = "background-color:#22c55e;color:white;"  # Doğru şık yeşil
                                    else:
                                        button_style = "background-color:#e5e7eb;color:#222;"  # Pasif
                                else:
                                    button_style = "background-color:#2563eb;color:white;"
                                if st.button(option_text, key=f"opt_{current_index}_{option_text}", disabled=answered,
                                             use_container_width=True):
                                    if not answered and check_button_cooldown(f"opt_{current_index}_{option_text}"):
                                        st.session_state[f"selected_option_{current_index}"] = option_text
                                        st.session_state.quiz_state["answered_questions"].append(current_index)
                                        if is_correct:
                                            st.session_state.quiz_state["correct_answers"] += 1
                                            st.session_state.answer_status = "correct"
                                        else:
                                            st.session_state.answer_status = "wrong"
                                        st.session_state.show_answer = True
                                        update_button_click_time(f"opt_{current_index}_{option_text}")
                                        st.rerun()
                            if answered:
                                st.markdown("---")
                                if st.session_state.answer_status == "correct":
                                    st.success("Doğru cevap!")
                                    st.markdown(f"**Açıklama:** {current_question['explanation']['correct']}")
                                else:
                                    st.error("Yanlış cevap!")
                                    st.markdown(f"**Doğru Cevap:** {current_question['correct_answer']}")
                                    st.markdown(
                                        f"**Açıklama:** {current_question['explanation']['incorrect'][selected_option] if selected_option in current_question['explanation']['incorrect'] else current_question['explanation']['correct']}")

                                # Sonraki soru butonu
                                if current_index < total_questions - 1:
                                    if st.button("Sonraki Soru", key=f"next_{current_index}"):
                                        st.session_state.quiz_state["current_question_index"] += 1
                                        st.session_state.show_answer = False
                                        st.session_state.answer_status = None
                                        st.rerun()
                                else:
                                    # Quiz tamamlandı
                                    score_percentage = (st.session_state.quiz_state[
                                                            "correct_answers"] / total_questions) * 100

                                    # İlerlemeyi kaydet
                                    auth.update_user_progress(
                                        st.session_state.username,
                                        st.session_state.selected_pdf_details["id"],
                                        st.session_state.quiz_state["current_topic"],
                                        score_percentage
                                    )

                                    st.markdown(f"""
                                    <div class='success-box'>
                                        <h2>🎉 Quiz Tamamlandı!</h2>
                                        <p>Toplam {total_questions} sorudan {st.session_state.quiz_state["correct_answers"]} tanesini doğru cevapladınız.</p>
                                        <h3>Başarı Oranı: %{score_percentage:.1f}</h3>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    # Sonuç değerlendirmesi
                                    if score_percentage >= 90:
                                        st.markdown("""
                                        <div class='info-box'>
                                            <h3>🏆 Mükemmel!</h3>
                                            <p>Konuya çok iyi hakimsiniz! Harika bir performans gösterdiniz.</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    elif score_percentage >= 70:
                                        st.markdown("""
                                        <div class='info-box'>
                                            <h3>👍 İyi İş!</h3>
                                            <p>Konu bilginiz iyi seviyede! Biraz daha çalışarak mükemmel olabilirsiniz.</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown("""
                                        <div class='warning-box'>
                                            <h3>📚 Biraz Daha Çalışmalısınız</h3>
                                            <p>Konu bilginizi geliştirmek için daha fazla çalışmanız gerekiyor.</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Quiz'i tekrar başlat
                                    if st.button("Quiz'i Tekrar Başlat", use_container_width=True):
                                        # Topic'i koruyarak quiz'i sıfırla
                                        st.session_state.quiz_state["current_question_index"] = 0
                                        st.session_state.quiz_state["correct_answers"] = 0
                                        st.session_state.quiz_state["answered_questions"] = []
                                        st.session_state.show_answer = False
                                        st.session_state.answer_status = None
                                        st.rerun()

                                    # Başka konuya geç
                                    if st.button("Başka Bir Konu Seç", use_container_width=True):
                                        st.session_state.quiz_state["current_topic"] = None
                                        st.rerun()

                                    # Confetti efekti
                                    trigger_confetti()

    # CHAT SAYFASI
    with tab3:
        st.markdown("<h2>💬 Asistan</h2>", unsafe_allow_html=True)

        if not st.session_state.selected_pdf_details:
            st.info("Asistan ile konuşmak için önce PDF'lerim sekmesinden bir PDF seçin.")
        else:
            pdf_id = st.session_state.selected_pdf_details["id"]
            metadata = st.session_state.selected_pdf_details["metadata"]

            st.markdown(f"""
            <div class='card'>
                <h3>{metadata['filename']}</h3>
                <div class='topic-list'>
                    {" ".join([f"<span class='topic-tag'>{topic}</span>" for topic in metadata["topics"]])}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # PDF içeriğini yükle
            pdf_content = load_pdf_content(metadata["path"])

            # Sohbet mesajlarını göster
            st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

            # Karşılama mesajı
            if not st.session_state.chat_messages:
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": f"Merhaba! {metadata['filename']} hakkında sorularınızı yanıtlamaya hazırım.",
                    "time": datetime.now().strftime("%H:%M")
                })
                save_chat_history(pdf_id, st.session_state.chat_messages)

            # Mesajları göster
            if not st.session_state.chat_messages or len(st.session_state.chat_messages) == 0:
                st.markdown("<div style='text-align:center; margin-top:40px;'>", unsafe_allow_html=True)
                st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=120)
                st.markdown("<h4>Henüz bir mesaj yok. Asistan ile sohbet başlatmak için mesaj yazın.</h4>",
                            unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                for message in st.session_state.chat_messages:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class='chat-message user-message'>
                            <div>{message["content"]}</div>
                            <div class='message-time'>{message.get("time", "")}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class='chat-message bot-message'>
                            <div>{message["content"]}</div>
                            <div class='message-time'>{message.get("time", "")}</div>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Mesaj gönderme
            with st.form("chat_form", clear_on_submit=True):
                user_message = st.text_input("Mesajınız:", key="user_message",
                                             placeholder="Mesajınızı yazın...",
                                             label_visibility="collapsed")
                submit_button = st.form_submit_button("Gönder", use_container_width=True)

                if submit_button and user_message:
                    # Kullanıcı mesajını ekle
                    st.session_state.chat_messages.append({
                        "role": "user",
                        "content": user_message,
                        "time": datetime.now().strftime("%H:%M")
                    })

                    # API yanıtını al
                    with st.spinner("Asistan yanıt yazıyor..."):
                        assistant_response = generate_chat_response(pdf_content, st.session_state.chat_messages)

                        # Asistan mesajını ekle
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": assistant_response,
                            "time": datetime.now().strftime("%H:%M")
                        })

                        # Sohbet geçmişini kaydet
                        save_chat_history(pdf_id, st.session_state.chat_messages)

                    st.rerun()

            # Sohbeti temizle
            if st.button("Sohbeti Temizle", use_container_width=True):
                st.session_state.chat_messages = [{
                    "role": "assistant",
                    "content": f"Merhaba! {metadata['filename']} hakkında sorularınızı yanıtlamaya hazırım.",
                    "time": datetime.now().strftime("%H:%M")
                }]
                save_chat_history(pdf_id, st.session_state.chat_messages)
                st.rerun()

    # SORU DEFTERİ SAYFASI
    with tab4:
        st.markdown("<h2>📖 Soru Defteri</h2>", unsafe_allow_html=True)

        if not st.session_state.authenticated:
            st.info("Soru defterini görüntülemek için lütfen giriş yapın.")
        else:
            marked_questions = load_marked_questions(st.session_state.username)

            if not marked_questions:
                st.info("Henüz kaydedilmiş soru bulunmuyor.")
            else:
                # Konu seçimi
                topics = list(marked_questions.keys())
                selected_topic = st.selectbox("Konu Seçin", options=topics)

                if selected_topic:
                    questions = marked_questions[selected_topic]

                    for i, question in enumerate(questions):
                        with st.expander(f"Soru {i + 1}"):
                            st.markdown("**Soru:**")
                            st.write(question["question"])

                            st.markdown("**Şıklar:**")
                            # Tüm şıkları göster
                            options = question.get("options", [])
                            correct_answer = question["answer"]

                            for option in options:
                                if option == correct_answer:
                                    st.markdown(f"✅ {option}")
                                else:
                                    st.markdown(f"❌ {option}")

                            st.markdown("**Doğru Cevap:**")
                            st.write(correct_answer)

                            st.markdown("**Açıklama:**")
                            st.write(question["explanation"]["correct"])

                            # Konu ve not düzenleme
                            col1, col2 = st.columns(2)
                            with col1:
                                new_topic = st.text_input("Konu", value=selected_topic, key=f"topic_{i}")
                            with col2:
                                new_note = st.text_area("Not", value=question.get("note", ""), key=f"note_{i}")

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Güncelle", key=f"update_{i}"):
                                    if update_marked_question(st.session_state.username, selected_topic, i, new_topic,
                                                              new_note):
                                        st.success("Soru güncellendi!")
                                        st.rerun()
                            with col2:
                                if st.button("Sil", key=f"delete_{i}"):
                                    if delete_marked_question(st.session_state.username, selected_topic, i):
                                        st.success("Soru silindi!")
                                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()