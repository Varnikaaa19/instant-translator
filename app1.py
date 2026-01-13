
import io
import csv
from datetime import datetime

import streamlit as st

# --- Ensure deep-translator is available at runtime ---
import sys, subprocess

try:
    from deep_translator import GoogleTranslator
except Exception:
    # Install at runtime if the package is missing (useful when the build ignored requirements.txt)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator
# ----------------------------
# Page config + custom styles
# ----------------------------
st.set_page_config(page_title="🌍 Language Translator", page_icon="📝", layout="centered")

# Beautiful gradient and card styling
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(135deg, #f0f4ff 0%, #fff7f0 100%);
}
h1, h2, h3, h4, h5 { font-weight: 700; }
.block-container { padding-top: 2rem; }
div.stButton > button {
  background: linear-gradient(90deg, #6a5acd, #00b4d8);
  color: white; border: 0; border-radius: 10px; padding: 0.6rem 1rem; font-weight: 600;
}
div.stDownloadButton > button, div[data-testid="stFileUploader"] > div {
  border-radius: 10px;
}
.card {
  padding: 1rem 1.2rem; border-radius: 12px; background: #ffffffee; box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
.small { font-size: 0.92rem; color: #555; }
.codebox pre { background: #f7f8fb; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Language Translator")
st.caption("Translate English text into **French**, **Spanish**, or **German**—fast and free (via deep-translator).")

# Keep session history
if "history" not in st.session_state:
    st.session_state.history = []  # [{src_text, target_lang, translated, ts}]

# ----------------------------
# Helpers
# ----------------------------
LANG_CHOICES = {
    "French": "fr",
    "Spanish": "es",
    "German": "de",
}

@st.cache_data(ttl=3600, show_spinner=False)
def translate_text_en(text: str, target_code: str) -> str:
    """
    Translate English -> target_code using deep-translator's GoogleTranslator.
    Cached to reduce API calls.
    """
    return GoogleTranslator(source="en", target=target_code).translate(text)

# ----------------------------
# Input UI
# ----------------------------
with st.container():
    st.subheader("✍️ Enter English text")
    src_text = st.text_area(
        " ",
        placeholder="Type or paste English text here...",
        height=160,
        label_visibility="collapsed",
    )

    colA, colB = st.columns([2, 1])
    with colA:
        target_label = st.selectbox("🎯 Target language", options=list(LANG_CHOICES.keys()), index=0)
    with colB:
        st.write("")  # spacing
        translate_clicked = st.button("🔁 Translate", type="primary", use_container_width=True)

# ----------------------------
# Translate
# ----------------------------
if translate_clicked:
    if not src_text.strip():
        st.error("Please enter some English text to translate.")
    else:
        code = LANG_CHOICES[target_label]
        try:
            with st.spinner(f"Translating to {target_label}…"):
                translated = translate_text_en(src_text.strip(), code)

            # Show result nicely
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("✅ Translation")
            st.markdown(f"**Target:** {target_label}")
            st.markdown('<div class="codebox">', unsafe_allow_html=True)
            st.code(translated, language="text")
            st.markdown('</div>', unsafe_allow_html=True)

            # Download translated text
            txt_bytes = io.BytesIO(translated.encode("utf-8"))
            fn_base = datetime.now().strftime("translation_%Y%m%d_%H%M%S")
            st.download_button(
                "⬇️ Download translated text (.txt)",
                data=txt_bytes,
                file_name=f"{fn_base}_{code}.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Save to history
            st.session_state.history.append({
                "src_text": src_text.strip(),
                "target_lang": target_label,
                "translated": translated,
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.toast("Translation added to history ✅")
        except Exception as e:
            st.error(f"Translation failed: {e}")

# ----------------------------
# Batch translation (CSV/TXT)
# ----------------------------
st.subheader("📦 Batch translate (English → chosen language)")
st.caption("Upload a `.txt` (one line per entry) or `.csv` (first column used or a `text` column).")
colU, colV = st.columns([2, 1])
with colU:
    batch_file = st.file_uploader("Upload file", type=["txt", "csv"], accept_multiple_files=False)
with colV:
    batch_target = st.selectbox("Target language for batch", options=list(LANG_CHOICES.keys()), index=0)

def build_csv_translations(rows: list[str], target_code: str) -> bytes:
    buff = io.StringIO()
    writer = csv.writer(buff)
    writer.writerow(["original_en", "translated", "target_lang"])
    for r in rows:
        if r.strip():
            try:
                t = translate_text_en(r.strip(), target_code)
            except Exception as e:
                t = f"[ERROR: {e}]"
            writer.writerow([r.strip(), t, target_code])
    return buff.getvalue().encode("utf-8")

if batch_file is not None:
    items = []
    try:
        if batch_file.name.lower().endswith(".txt"):
            items = batch_file.getvalue().decode("utf-8", errors="ignore").splitlines()
        else:
            content = batch_file.getvalue().decode("utf-8", errors="ignore").splitlines()
            # Try dict reader (text column), then basic csv reader (first col)
            reader = csv.DictReader(content)
            if reader.fieldnames and "text" in [f.lower() for f in reader.fieldnames]:
                key = [f for f in reader.fieldnames if f.lower() == "text"][0]
                for row in reader:
                    items.append(str(row.get(key, "")).strip())
            else:
                reader2 = csv.reader(content)
                for row in reader2:
                    if row:
                        items.append(str(row[0]).strip())
    except Exception as e:
        st.error(f"Failed to parse file: {e}")

    if items:
        st.info(f"Parsed {len(items)} lines.")
        code = LANG_CHOICES[batch_target]
        csv_bytes = build_csv_translations(items, code)
        st.download_button(
            "⬇️ Download CSV with translations",
            data=csv_bytes,
            file_name=f"translations_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("No usable lines found in the uploaded file.")

# ----------------------------
# History
# ----------------------------
st.subheader("🕘 History (this session)")
if st.session_state.history:
    clear = st.button("Clear history")
    if clear:
        st.session_state.history.clear()
        st.experimental_rerun()

    for i, item in enumerate(reversed(st.session_state.history), start=1):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"**{i}.** → **{item['target_lang']}**  \n*{item['ts']}*")
        st.markdown('<div class="codebox">', unsafe_allow_html=True)
        st.code(item["translated"], language="text")
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button(
            "Download",
            data=io.BytesIO(item["translated"].encode("utf-8")),
            file_name=f"translated_{i}.txt",
            mime="text/plain"
        )
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.caption("No translations yet. Add one above to see it here.")

