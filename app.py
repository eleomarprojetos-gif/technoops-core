# ==============================
# CONFIGURAR PÁGINA (FORÇA DARK)
# ==============================
import streamlit as st
st.set_page_config(
    page_title="TechnoOps Core",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# FORÇA DARK MODE SEMPRE
# ==============================
st.markdown("""
<style>
:root { color-scheme: dark !important; }
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: #0F0F0F !important;
  color: #FFFFFF !important;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(126,45,127,0.85), rgba(15,15,15,1)) !important;
}
label, p, span, div, small, strong, li, a, h1,h2,h3,h4,h5,h6 {
  color: #FFFFFF !important;
}
[data-testid="stSidebar"] * {
  color: #FFFFFF !important;
}
textarea, input {
    border: 2px solid #FFC107 !important;
    color: white !important;
    background-color: #1E1E1E !important;
}
.stButton>button {
    background-color: #A64D9A;
    color: white;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)
