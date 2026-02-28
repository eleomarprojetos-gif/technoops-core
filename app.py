import sqlite3
import os
import datetime as dt
import hashlib
import secrets
from dataclasses import dataclass
import pandas as pd
import streamlit as st

# ==============================
# 🎨 ESTILO GLOBAL
# ==============================
st.markdown("""
<style>

div[data-baseweb="select"] > div {
    border: 2px solid #FFC107 !important;
    border-radius: 6px !important;
    background-color: #1E1E2F !important;
    color: white !important;
    font-size: 16px !important;
}
div[data-baseweb="select"] span {
    color: white !important;
    font-size: 16px !important;
}
input[type="number"], input[type="date"] {
    border: 2px solid #FFC107 !important;
    color: white !important;
    font-size: 16px !important;
}
header[data-testid="stHeader"] {
    background-color: #A64D9A;
}
.stTextInput input {
    border: 2px solid #FFC107 !important;
    color: white !important;
    font-size: 16px !important;
    background-color: #1E1E1E !important;
}
.stTextInput input[type="password"] { color: white !important; }
.stTextInput input::placeholder { color: #CCCCCC !important; }

/* TEXTAREA - texto branco */
textarea {
    border: 2px solid #FFC107 !important;
    color: white !important;
    font-size: 15px !important;
    background-color: #1E1E1E !important;
}
textarea::placeholder { color: #CCCCCC !important; }

label {
    color: white !important;
    font-size: 16px !important;
}
.stButton>button {
    background-color: #A64D9A;
    color: white;
    font-size: 16px;
    border-radius: 6px;
}
.stSelectbox div { color: white !important; font-size: 16px !important; }

/* Cards semáforo */
.kpi-green {
    background: linear-gradient(135deg, #0d3320, #1a5c38);
    border: 1px solid #2ecc71;
    border-radius: 14px; padding: 16px 18px; margin-bottom: 8px;
}
.kpi-orange {
    background: linear-gradient(135deg, #3d2400, #6b4000);
    border: 1px solid #f39c12;
    border-radius: 14px; padding: 16px 18px; margin-bottom: 8px;
}
.kpi-red {
    background: linear-gradient(135deg, #3d0000, #6b0000);
    border: 1px solid #e74c3c;
    border-radius: 14px; padding: 16px 18px; margin-bottom: 8px;
}
.kpi-name { font-size: 1rem; color: #CFCFCF; margin-bottom: 4px; }
.kpi-avg  { font-size: 1.6rem; font-weight: 700; color: #FFFFFF; }
.kpi-detail { font-size: 0.82rem; color: #CFCFCF; margin-top: 4px; }

</style>
""", unsafe_allow_html=True)

# ==============================
# CONFIG
# ==============================
DB_PATH   = os.path.join(os.path.dirname(__file__), "technoops.db")
PRIMARY   = "#7E2D7F"
SECONDARY = "#F2B233"
BG        = "#0F0F0F"
CARD      = "#151515"
TEXT      = "#FFFFFF"
MUTED     = "#CFCFCF"

# ==============================
# SENHA
# ==============================
def _pbkdf2_hash(password: str, salt_hex: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000)
    return dk.hex()

def verify_password(stored: str, password: str) -> bool:
    try:
        algo, salt, digest = stored.split("$", 2)
        if algo != "pbkdf2_sha256":
            return False
        return _pbkdf2_hash(password, salt) == digest
    except Exception:
        return False

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _pbkdf2_hash(password, salt)
    return f"pbkdf2_sha256${salt}${digest}"

def update_user_password(company_id: int, username: str, new_password: str):
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE company_id=? AND username=?",
                 (hash_password(new_password), company_id, username))
    conn.commit()

# ==============================
# BANCO DE DADOS
# ==============================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        theme_primary TEXT, theme_secondary TEXT, created_at TEXT NOT NULL);""")
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, username TEXT NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','operator','viewer')),
        is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
        UNIQUE(company_id, username), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, name TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, name TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, name TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS service_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('ativacao','manutencao','outros')),
        default_unit_value REAL NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS monthly_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, year INTEGER NOT NULL, month INTEGER NOT NULL,
        goal_value REAL NOT NULL,
        UNIQUE(company_id, year, month), FOREIGN KEY(company_id) REFERENCES companies(id));""")
    cur.execute("""CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, entry_date TEXT NOT NULL,
        technician_id INTEGER NOT NULL, team_id INTEGER, region_id INTEGER,
        service_type_id INTEGER NOT NULL, quantity REAL NOT NULL, unit_value REAL NOT NULL,
        notes TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(technician_id) REFERENCES technicians(id),
        FOREIGN KEY(team_id) REFERENCES teams(id),
        FOREIGN KEY(region_id) REFERENCES regions(id),
        FOREIGN KEY(service_type_id) REFERENCES service_types(id));""")
    conn.commit()

    cur.execute("SELECT COUNT(*) AS n FROM companies;")
    if cur.fetchone()["n"] == 0:
        now = dt.datetime.utcnow().isoformat()
        cur.execute("INSERT INTO companies(name, theme_primary, theme_secondary, created_at) VALUES (?,?,?,?)",
                    ("Techno Mais", "#7E2D7F", "#F2B233", now))
        cid = cur.lastrowid
        cur.executemany("INSERT INTO service_types(company_id, name, category, default_unit_value, is_active) VALUES (?,?,?,?,1)",
                        [(cid, "Ativação", "ativacao", 210.0), (cid, "Manutenção", "manutencao", 135.0)])
        cur.execute("INSERT INTO regions(company_id, name, is_active) VALUES (?,?,1)", (cid, "Geral"))
        cur.execute("INSERT INTO teams(company_id, name, is_active) VALUES (?,?,1)", (cid, "Solo"))
        cur.execute("INSERT INTO users(company_id, username, password_hash, role, is_active, created_at) VALUES (?,?,?,?,1,?)",
                    (cid, "admin", hash_password("admin123"), "admin", now))
        conn.commit()
    conn.close()

# ==============================
# CSS INJECT
# ==============================
def inject_css():
    st.markdown(f"""
    <style>
      .stApp {{ background: {BG}; color: {TEXT}; }}
      .block-container {{ padding-top: 2rem; }}
      .techno-card {{
        background: {CARD}; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px; padding: 16px 18px;
      }}
      .techno-kpi {{ font-size: 1.1rem; color: {MUTED}; margin-bottom: 6px; }}
      .techno-value {{ font-size: 1.7rem; font-weight: 700; color: {TEXT}; }}
      .techno-pill {{
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        background: rgba(242,178,51,0.18); border: 1px solid rgba(242,178,51,0.35);
        color: {TEXT}; font-size: 0.85rem;
      }}
      div[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(126,45,127,0.85), rgba(15,15,15,1));
      }}
      button[kind="primary"]   {{ background: {SECONDARY} !important; color: #111 !important; border: 0 !important; }}
      button[kind="secondary"] {{ border: 1px solid rgba(255,255,255,0.18) !important; color: {TEXT} !important; }}
    </style>
    """, unsafe_allow_html=True)

# ==============================
# SESSION
# ==============================
@dataclass
class SessionUser:
    company_id: int
    company_name: str
    username: str
    role: str

def set_user(user): st.session_state["user"] = user
def get_user():     return st.session_state.get("user")

def require_login():
    if not get_user():
        st.warning("Faça login para continuar.")
        st.stop()

def require_role(roles):
    u = get_user()
    if not u or u.role not in roles:
        st.error("Você não tem permissão para acessar esta área.")
        st.stop()

def fetch_all(conn, sql, params=()):  return conn.execute(sql, params).fetchall()
def fetch_one(conn, sql, params=()):  return conn.execute(sql, params).fetchone()
def df_from_rows(rows):
    if not rows: return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])

# ==============================
# LOGIN
# ==============================
def page_login():
    st.title("TechnoOps")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("Sistema de Operações Técnicas (Core)")
        st.caption("Ativação • Manutenção • Indicadores • Resumo Mensal")
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_principal.png")
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with col2:
        with st.form("login_form"):
            company  = st.text_input("Empresa", value="Techno Mais")
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
        if submitted:
            conn = get_conn()
            comp = fetch_one(conn, "SELECT * FROM companies WHERE name=?", (company.strip(),))
            if not comp:
                st.error("Empresa não encontrada.")
                return
            user = fetch_one(conn, "SELECT * FROM users WHERE company_id=? AND username=? AND is_active=1",
                             (comp["id"], username.strip()))
            if not user or not verify_password(user["password_hash"], password):
                st.error("Usuário ou senha inválidos.")
                return
            set_user(SessionUser(company_id=comp["id"], company_name=comp["name"],
                                 username=user["username"], role=user["role"]))
            st.success("Login realizado!")
            st.rerun()
        st.divider()
        st.caption("Primeiro acesso: empresa **Techno Mais**, usuário **admin**, senha **admin123**.")

# ==============================
# SIDEBAR
# ==============================
def sidebar_header():
    u = get_user()
    st.sidebar.markdown("### TechnoOps")
    sub_path = os.path.join(os.path.dirname(__file__), "assets", "submarca.png")
    if os.path.exists(sub_path):
        st.sidebar.image(sub_path, use_container_width=True)
    st.sidebar.write(f"**Empresa:** {u.company_name}")
    st.sidebar.write(f"**Usuário:** {u.username}")
    role_map = {"admin": "Admin", "operator": "Operador", "viewer": "Visualização"}
    st.sidebar.markdown(f"<span class='techno-pill'>{role_map.get(u.role, u.role)}</span>", unsafe_allow_html=True)
    if st.sidebar.button("Sair"):
        set_user(None)
        st.rerun()
    st.sidebar.divider()

# ==============================
# DASHBOARD
# ==============================
def page_dashboard():
    require_login()
    u     = get_user()
    today = dt.date.today()
    conn  = get_conn()
    st.header("Dashboard")

    rows = fetch_all(conn, "SELECT quantity, unit_value FROM entries WHERE company_id=? AND entry_date=?",
                     (u.company_id, today.isoformat()))
    total_services = sum(r["quantity"] for r in rows) if rows else 0
    total_revenue  = sum(r["quantity"] * r["unit_value"] for r in rows) if rows else 0

    ym     = f"{today.year:04d}-{today.month:02d}"
    m_rows = fetch_all(conn, "SELECT quantity, unit_value FROM entries WHERE company_id=? AND substr(entry_date,1,7)=?",
                       (u.company_id, ym))
    m_revenue  = sum(r["quantity"] * r["unit_value"] for r in m_rows) if m_rows else 0
    goal       = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                           (u.company_id, today.year, today.month))
    goal_value = float(goal["goal_value"]) if goal else 0.0
    pct        = (m_revenue / goal_value * 100.0) if goal_value > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Serviços hoje</div>"
                    f"<div class='techno-value'>{total_services:.0f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita hoje</div>"
                    f"<div class='techno-value'>R$ {total_revenue:,.2f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita do mês</div>"
                    f"<div class='techno-value'>R$ {m_revenue:,.2f}</div></div>", unsafe_allow_html=True)
    with c4:
        if goal_value > 0 and pct is not None:
            st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Meta atingida</div>"
                        f"<div class='techno-value'>{pct:.0f}%</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Meta do mês</div>"
                        f"<div class='techno-value'>—</div></div>", unsafe_allow_html=True)

# ==============================
# LANÇAMENTO DIÁRIO
# ==============================
def page_daily_entry():
    require_login()
    u = get_user()
    require_role({"admin", "operator"})
    st.header("Lançamento Diário")

    conn     = get_conn()
    techs    = df_from_rows(fetch_all(conn, "SELECT id, name FROM technicians WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    teams    = df_from_rows(fetch_all(conn, "SELECT id, name FROM teams WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    regions  = df_from_rows(fetch_all(conn, "SELECT id, name FROM regions WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    services = df_from_rows(fetch_all(conn, "SELECT id, name, category, default_unit_value FROM service_types WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))

    if techs.empty:
        st.warning("Cadastre pelo menos 1 técnico no Admin → Técnicos.")
        return

    entry_date = st.date_input("Data", value=dt.date.today())

    # ---- Novo lançamento ----
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            tech_name   = st.selectbox("Técnico", techs["name"].tolist())
            team_name   = st.selectbox("Equipe", teams["name"].tolist() if not teams.empty else ["Solo"])
            region_name = st.selectbox("Região", regions["name"].tolist() if not regions.empty else ["Geral"])
        with col2:
            service_name = st.selectbox("Tipo de Serviço", services["name"].tolist())
            quantity     = st.number_input("Quantidade", min_value=0.0, value=1.0, step=1.0)
            default_unit = float(services.loc[services["name"] == service_name, "default_unit_value"].iloc[0])
            unit_value   = st.number_input("Valor Unitário (R$)", min_value=0.0, value=default_unit, step=1.0)
        notes     = st.text_area("Observação (opcional)")
        submitted = st.form_submit_button("Salvar", use_container_width=True)
        if submitted:
            tech_id    = int(techs.loc[techs["name"] == tech_name, "id"].iloc[0])
            team_id    = int(teams.loc[teams["name"] == team_name, "id"].iloc[0]) if not teams.empty else None
            region_id  = int(regions.loc[regions["name"] == region_name, "id"].iloc[0]) if not regions.empty else None
            service_id = int(services.loc[services["name"] == service_name, "id"].iloc[0])
            conn.execute("""INSERT INTO entries(company_id, entry_date, technician_id, team_id, region_id,
                                service_type_id, quantity, unit_value, notes, created_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                         (u.company_id, entry_date.isoformat(), tech_id, team_id, region_id, service_id,
                          float(quantity), float(unit_value), notes.strip() if notes else None,
                          dt.datetime.utcnow().isoformat()))
            conn.commit()
            st.success("Lançamento salvo!")
            st.rerun()

    # ---- Tabela do dia ----
    st.subheader("Lançamentos do dia")
    rows = fetch_all(conn, """
        SELECT e.id, e.entry_date AS Data, t.name AS Tecnico, tm.name AS Equipe,
               r.name AS Regiao, st.name AS Servico,
               e.quantity AS Qtd, e.unit_value AS ValorUnit,
               (e.quantity * e.unit_value) AS Receita,
               COALESCE(e.notes,'') AS Observacao
        FROM entries e
        JOIN technicians t   ON t.id  = e.technician_id
        LEFT JOIN teams tm   ON tm.id = e.team_id
        LEFT JOIN regions r  ON r.id  = e.region_id
        JOIN service_types st ON st.id = e.service_type_id
        WHERE e.company_id=? AND e.entry_date=?
        ORDER BY e.id DESC
    """, (u.company_id, entry_date.isoformat()))
    df = df_from_rows(rows)

    if df.empty:
        st.info("Nenhum lançamento para esta data ainda.")
        return

    st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    total_rev = df["Receita"].sum()
    total_srv = df["Qtd"].sum()
    st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Totais do dia</div>"
                f"<div class='techno-value'>{total_srv:.0f} serviços • R$ {total_rev:,.2f}</div></div>",
                unsafe_allow_html=True)

    # ---- ✏️ Editar lançamento ----
    with st.expander("✏️ Editar lançamento"):
        edit_id = st.selectbox(
            "Selecione o lançamento para editar",
            df["id"].tolist(),
            format_func=lambda x: (
                f"ID {x} — "
                f"{df.loc[df['id']==x,'Tecnico'].values[0]} | "
                f"{df.loc[df['id']==x,'Servico'].values[0]} | "
                f"Qtd {df.loc[df['id']==x,'Qtd'].values[0]:.0f}"
            )
        )
        row_edit = fetch_one(conn, """
            SELECT e.*, t.name as tech_name, tm.name as team_name,
                   r.name as region_name, st.name as service_name
            FROM entries e
            JOIN technicians t   ON t.id  = e.technician_id
            LEFT JOIN teams tm   ON tm.id = e.team_id
            LEFT JOIN regions r  ON r.id  = e.region_id
            JOIN service_types st ON st.id = e.service_type_id
            WHERE e.id=? AND e.company_id=?
        """, (int(edit_id), u.company_id))

        if row_edit:
            with st.form("edit_entry_form"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_tech = st.selectbox("Técnico", techs["name"].tolist(),
                                          index=techs["name"].tolist().index(row_edit["tech_name"])
                                          if row_edit["tech_name"] in techs["name"].tolist() else 0)
                    e_team_list = teams["name"].tolist() if not teams.empty else ["Solo"]
                    e_team = st.selectbox("Equipe", e_team_list,
                                          index=e_team_list.index(row_edit["team_name"])
                                          if row_edit["team_name"] in e_team_list else 0)
                    e_region_list = regions["name"].tolist() if not regions.empty else ["Geral"]
                    e_region = st.selectbox("Região", e_region_list,
                                            index=e_region_list.index(row_edit["region_name"])
                                            if row_edit["region_name"] in e_region_list else 0)
                with ec2:
                    e_svc_list = services["name"].tolist()
                    e_service = st.selectbox("Tipo de Serviço", e_svc_list,
                                             index=e_svc_list.index(row_edit["service_name"])
                                             if row_edit["service_name"] in e_svc_list else 0)
                    e_qty  = st.number_input("Quantidade", min_value=0.0, value=float(row_edit["quantity"]), step=1.0)
                    e_unit = st.number_input("Valor Unitário (R$)", min_value=0.0, value=float(row_edit["unit_value"]), step=1.0)
                e_notes   = st.text_area("Observação", value=row_edit["notes"] or "")
                save_edit = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                if save_edit:
                    e_tech_id    = int(techs.loc[techs["name"] == e_tech, "id"].iloc[0])
                    e_team_id    = int(teams.loc[teams["name"] == e_team, "id"].iloc[0]) if not teams.empty else None
                    e_region_id  = int(regions.loc[regions["name"] == e_region, "id"].iloc[0]) if not regions.empty else None
                    e_service_id = int(services.loc[services["name"] == e_service, "id"].iloc[0])
                    conn.execute("""UPDATE entries SET technician_id=?, team_id=?, region_id=?,
                                        service_type_id=?, quantity=?, unit_value=?, notes=?
                                    WHERE id=? AND company_id=?""",
                                 (e_tech_id, e_team_id, e_region_id, e_service_id,
                                  float(e_qty), float(e_unit),
                                  e_notes.strip() if e_notes else None,
                                  int(edit_id), u.company_id))
                    conn.commit()
                    st.success("Lançamento atualizado!")
                    st.rerun()

    # ---- 🗑️ Excluir lançamento ----
    with st.expander("🗑️ Excluir lançamento"):
        del_id = st.selectbox("Selecione o ID para excluir", df["id"].tolist(),
                              format_func=lambda x: f"ID {x}")
        if st.button("Excluir", type="secondary"):
            conn.execute("DELETE FROM entries WHERE company_id=? AND id=?", (u.company_id, int(del_id)))
            conn.commit()
            st.success("Excluído.")
            st.rerun()

# ==============================
# RESUMO MENSAL
# ==============================
def page_monthly_summary():
    require_login()
    u     = get_user()
    today = dt.date.today()
    st.header("Resumo Mensal")

    year  = st.number_input("Ano", min_value=2020, max_value=2100, value=today.year,  step=1)
    month = st.number_input("Mês", min_value=1,    max_value=12,   value=today.month, step=1)
    ym    = f"{int(year):04d}-{int(month):02d}"

    conn = get_conn()
    rows = fetch_all(conn, """
        SELECT st.category, e.quantity, e.unit_value, e.entry_date
        FROM entries e JOIN service_types st ON st.id=e.service_type_id
        WHERE e.company_id=? AND substr(e.entry_date,1,7)=?
    """, (u.company_id, ym))

    if not rows:
        st.info("Sem dados para este mês.")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df["receita"] = df["quantity"] * df["unit_value"]

    total_ativ = df.loc[df["category"] == "ativacao",   "quantity"].sum()
    total_manu = df.loc[df["category"] == "manutencao", "quantity"].sum()
    total_srv  = df["quantity"].sum()
    rec_ativ   = df.loc[df["category"] == "ativacao",   "receita"].sum()
    rec_manu   = df.loc[df["category"] == "manutencao", "receita"].sum()
    rec_total  = df["receita"].sum()

    goal_row   = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                           (u.company_id, int(year), int(month)))
    goal_value = float(goal_row["goal_value"]) if goal_row else 0.0
    pct        = (rec_total / goal_value * 100.0) if goal_value > 0 else None
    avg_daily  = rec_total / df["entry_date"].nunique() if df["entry_date"].nunique() > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Total ativações</div><div class='techno-value'>{total_ativ:.0f}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Total manutenções</div><div class='techno-value'>{total_manu:.0f}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Total serviços</div><div class='techno-value'>{total_srv:.0f}</div></div>", unsafe_allow_html=True)
    st.divider()

    c4, c5, c6 = st.columns(3)
    with c4: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita ativações</div><div class='techno-value'>R$ {rec_ativ:,.2f}</div></div>", unsafe_allow_html=True)
    with c5: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita manutenções</div><div class='techno-value'>R$ {rec_manu:,.2f}</div></div>", unsafe_allow_html=True)
    with c6: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita bruta mensal</div><div class='techno-value'>R$ {rec_total:,.2f}</div></div>", unsafe_allow_html=True)
    st.divider()

    cA, cB, cC = st.columns(3)
    with cA: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Meta de receita</div><div class='techno-value'>R$ {goal_value:,.2f}</div></div>", unsafe_allow_html=True)
    with cB:
        v = f"{pct:.0f}%" if pct is not None else "—"
        st.markdown(f"<div class='techno-card'><div class='techno-kpi'>% meta atingida</div><div class='techno-value'>{v}</div></div>", unsafe_allow_html=True)
    with cC: st.markdown(f"<div class='techno-card'><div class='techno-kpi'>Receita média diária</div><div class='techno-value'>R$ {avg_daily:,.2f}</div></div>", unsafe_allow_html=True)

# ==============================
# INDICADORES DOS TÉCNICOS
# ==============================
def _semaforo(media, meta_media, limiar_pct=0.833):
    """Retorna (cor_css, emoji, status) baseado na média vs meta."""
    if media >= meta_media:
        return "kpi-green",  "🟢", "No alvo"
    elif media >= meta_media * limiar_pct:
        return "kpi-orange", "🟠", "Atenção"
    else:
        return "kpi-red",    "🔴", "Abaixo"

def page_technician_kpis():
    require_login()
    u     = get_user()
    today = dt.date.today()
    st.header("Indicadores dos Técnicos")

    year  = st.number_input("Ano", min_value=2020, max_value=2100, value=today.year,  step=1, key="iy")
    month = st.number_input("Mês", min_value=1,    max_value=12,   value=today.month, step=1, key="im")
    ym    = f"{int(year):04d}-{int(month):02d}"

    conn = get_conn()
    tech_rows = fetch_all(conn, """
        SELECT t.name as Tecnico,
               SUM(CASE WHEN st.category='ativacao'   THEN e.quantity ELSE 0 END) as AtivacoesTotais,
               SUM(CASE WHEN st.category='manutencao' THEN e.quantity ELSE 0 END) as ManutencoesTotais,
               SUM(e.quantity)              as TotalServicos,
               SUM(e.quantity*e.unit_value) as ReceitaGerada,
               COUNT(DISTINCT e.entry_date) as DiasComLancamento
        FROM entries e
        JOIN technicians t    ON t.id  = e.technician_id
        JOIN service_types st ON st.id = e.service_type_id
        WHERE e.company_id=? AND substr(e.entry_date,1,7)=?
        GROUP BY t.name ORDER BY ReceitaGerada DESC
    """, (u.company_id, ym))

    df = df_from_rows(tech_rows)
    if df.empty:
        st.info("Sem dados para este mês.")
        return

    # ── Calcular desempenho por técnico ──────────────────────────────
    perf_data = []
    for _, row in df.iterrows():
        tech_name = row["Tecnico"]
        dias_rows = fetch_all(conn, """
            SELECT e.entry_date,
                   MAX(CASE WHEN tm.name = 'Solo' THEN 1 ELSE 0 END) as is_solo
            FROM entries e
            JOIN technicians t ON t.id = e.technician_id
            LEFT JOIN teams tm ON tm.id = e.team_id
            WHERE e.company_id=? AND substr(e.entry_date,1,7)=? AND t.name=?
            GROUP BY e.entry_date
        """, (u.company_id, ym, tech_name))

        dias_solo   = sum(1 for d in dias_rows if d["is_solo"] == 1)
        dias_equipe = sum(1 for d in dias_rows if d["is_solo"] == 0)
        total_dias  = dias_solo + dias_equipe

        # ── Ativação: Solo=3, Equipe=4 ──
        meta_ativ_total = (dias_solo * 3) + (dias_equipe * 4)
        ativ_total      = float(row["AtivacoesTotais"])
        media_ativ      = ativ_total / total_dias       if total_dias > 0 else 0.0
        meta_ativ_media = meta_ativ_total / total_dias  if total_dias > 0 else 3.0
        pct_ativ        = (ativ_total / meta_ativ_total * 100) if meta_ativ_total > 0 else 0
        cor_a, sem_a, st_a = _semaforo(media_ativ, meta_ativ_media)

        # ── Manutenção: Solo=4, Equipe=6 ──
        meta_manu_total = (dias_solo * 4) + (dias_equipe * 6)
        manu_total      = float(row["ManutencoesTotais"])
        media_manu      = manu_total / total_dias       if total_dias > 0 else 0.0
        meta_manu_media = meta_manu_total / total_dias  if total_dias > 0 else 4.0
        pct_manu        = (manu_total / meta_manu_total * 100) if meta_manu_total > 0 else 0
        cor_m, sem_m, st_m = _semaforo(media_manu, meta_manu_media)

        perf_data.append({
            "Tecnico":          tech_name,
            "DiasSolo":         dias_solo,
            "DiasEquipe":       dias_equipe,
            "DiasTrabalh":      total_dias,
            "ReceitaGerada":    float(row["ReceitaGerada"]),
            # ativação
            "AtivTotal":        ativ_total,
            "MediaAtiv":        media_ativ,
            "MetaAtivMedia":    meta_ativ_media,
            "PctAtiv":          pct_ativ,
            "CorAtiv":          cor_a,
            "SemAtiv":          sem_a,
            "StAtiv":           st_a,
            # manutenção
            "ManuTotal":        manu_total,
            "MediaManu":        media_manu,
            "MetaManuMedia":    meta_manu_media,
            "PctManu":          pct_manu,
            "CorManu":          cor_m,
            "SemManu":          sem_m,
            "StManu":           st_m,
        })

    # ── Cards unificados por técnico ─────────────────────────────────
    st.subheader("🚦 Desempenho por Técnico")
    st.caption("Ativação: Solo = 3/dia | Equipe = 4/dia    •    Manutenção: Solo = 4/dia | Equipe = 6/dia")

    n_cols = min(len(perf_data), 3)
    cols   = st.columns(n_cols)
    for i, p in enumerate(perf_data):
        with cols[i % n_cols]:
            st.markdown(f"""
            <div style="background:#1e1e2f;border:1px solid rgba(255,255,255,0.12);
                        border-radius:16px;padding:16px 18px;margin-bottom:10px;">
                <div style="font-size:1.05rem;font-weight:700;color:#fff;margin-bottom:12px;">
                    👤 {p['Tecnico']}
                    &nbsp;<span style="font-size:0.78rem;color:#aaa;">
                        {p['DiasTrabalh']}d ({p['DiasSolo']}solo+{p['DiasEquipe']}eq)
                    </span>
                </div>
                <div style="display:flex;gap:10px;">
                    <div style="flex:1;background:{'#0d3320' if p['CorAtiv']=='kpi-green' else '#3d2400' if p['CorAtiv']=='kpi-orange' else '#3d0000'};
                                border:1px solid {'#2ecc71' if p['CorAtiv']=='kpi-green' else '#f39c12' if p['CorAtiv']=='kpi-orange' else '#e74c3c'};
                                border-radius:10px;padding:10px 12px;">
                        <div style="font-size:0.78rem;color:#ccc;">⚡ Ativação</div>
                        <div style="font-size:1.4rem;font-weight:700;color:#fff;">{p['MediaAtiv']:.2f}
                            <span style="font-size:0.75rem;color:#aaa;">/dia</span></div>
                        <div style="font-size:0.75rem;color:#ccc;">
                            {p['SemAtiv']} {p['StAtiv']}<br>
                            Meta {p['MetaAtivMedia']:.1f} &nbsp;|&nbsp; {p['PctAtiv']:.0f}% cumprido
                        </div>
                    </div>
                    <div style="flex:1;background:{'#0d3320' if p['CorManu']=='kpi-green' else '#3d2400' if p['CorManu']=='kpi-orange' else '#3d0000'};
                                border:1px solid {'#2ecc71' if p['CorManu']=='kpi-green' else '#f39c12' if p['CorManu']=='kpi-orange' else '#e74c3c'};
                                border-radius:10px;padding:10px 12px;">
                        <div style="font-size:0.78rem;color:#ccc;">🔧 Manutenção</div>
                        <div style="font-size:1.4rem;font-weight:700;color:#fff;">{p['MediaManu']:.2f}
                            <span style="font-size:0.75rem;color:#aaa;">/dia</span></div>
                        <div style="font-size:0.75rem;color:#ccc;">
                            {p['SemManu']} {p['StManu']}<br>
                            Meta {p['MetaManuMedia']:.1f} &nbsp;|&nbsp; {p['PctManu']:.0f}% cumprido
                        </div>
                    </div>
                </div>
                <div style="margin-top:8px;font-size:0.78rem;color:#aaa;text-align:right;">
                    Receita: R$ {p['ReceitaGerada']:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Gráfico agrupado único: ativação + manutenção por técnico ────
    st.subheader("📊 Comparativo — Ativação & Manutenção por Técnico")

    import json

    nomes       = [p["Tecnico"]                for p in perf_data]
    medias_ativ = [round(p["MediaAtiv"], 2)    for p in perf_data]
    metas_ativ  = [round(p["MetaAtivMedia"], 2) for p in perf_data]
    medias_manu = [round(p["MediaManu"], 2)    for p in perf_data]
    metas_manu  = [round(p["MetaManuMedia"], 2) for p in perf_data]

    def hex_cor(p, key):
        c = p[key]
        if c == "kpi-green":  return "#2ecc71"
        if c == "kpi-orange": return "#f39c12"
        return "#e74c3c"

    cores_ativ = [hex_cor(p, "CorAtiv") for p in perf_data]
    cores_manu = [hex_cor(p, "CorManu") for p in perf_data]

    chart_html = f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <div style="background:#1a1a2e;border-radius:16px;padding:24px;">
      <canvas id="kpiUnified" height="100"></canvas>
    </div>
    <script>
    new Chart(document.getElementById('kpiUnified').getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(nomes)},
        datasets: [
          {{
            label: '⚡ Ativação média/dia',
            data: {json.dumps(medias_ativ)},
            backgroundColor: {json.dumps(cores_ativ)},
            borderColor: {json.dumps(cores_ativ)},
            borderWidth: 2,
            borderRadius: 6,
            barPercentage: 0.4,
            categoryPercentage: 0.8,
          }},
          {{
            label: '🔧 Manutenção média/dia',
            data: {json.dumps(medias_manu)},
            backgroundColor: {json.dumps(["rgba(100,160,255,0.85)" if c=="kpi-green" else "rgba(255,150,50,0.85)" if c=="kpi-orange" else "rgba(220,60,60,0.85)" for c in [p["CorManu"] for p in perf_data]])},
            borderColor: {json.dumps(["#64a0ff" if c=="kpi-green" else "#ff9632" if c=="kpi-orange" else "#dc3c3c" for c in [p["CorManu"] for p in perf_data]])},
            borderWidth: 2,
            borderRadius: 6,
            barPercentage: 0.4,
            categoryPercentage: 0.8,
          }},
          {{
            label: 'Meta Ativação',
            data: {json.dumps(metas_ativ)},
            type: 'line',
            borderColor: '#FFC107',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [6, 3],
            pointBackgroundColor: '#FFC107',
            pointRadius: 5,
            fill: false,
            tension: 0.3,
            yAxisID: 'y',
          }},
          {{
            label: 'Meta Manutenção',
            data: {json.dumps(metas_manu)},
            type: 'line',
            borderColor: '#a78bfa',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [4, 4],
            pointBackgroundColor: '#a78bfa',
            pointRadius: 5,
            fill: false,
            tension: 0.3,
            yAxisID: 'y',
          }}
        ]
      }},
      options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{
            labels: {{ color: '#fff', font: {{ size: 12 }}, padding: 16 }}
          }},
          tooltip: {{
            callbacks: {{
              label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2)
            }}
          }}
        }},
        scales: {{
          x: {{
            ticks: {{ color: '#ccc', font: {{ size: 13 }} }},
            grid: {{ color: 'rgba(255,255,255,0.05)' }}
          }},
          y: {{
            beginAtZero: true,
            ticks: {{ color: '#ccc', font: {{ size: 13 }} }},
            grid: {{ color: 'rgba(255,255,255,0.08)' }}
          }}
        }}
      }}
    }});
    </script>
    """
    st.components.v1.html(chart_html, height=400)

    st.divider()

    # ── Tabela detalhada ─────────────────────────────────────────────
    st.subheader("📋 Tabela Detalhada")
    df_show = pd.DataFrame([{
        "Técnico":              p["Tecnico"],
        "Status Ativ":          p["SemAtiv"] + " " + p["StAtiv"],
        "Média Ativ/Dia":       round(p["MediaAtiv"], 2),
        "Meta Ativ/Dia":        round(p["MetaAtivMedia"], 1),
        "% Meta Ativ":          f"{p['PctAtiv']:.0f}%",
        "Status Manu":          p["SemManu"] + " " + p["StManu"],
        "Média Manu/Dia":       round(p["MediaManu"], 2),
        "Meta Manu/Dia":        round(p["MetaManuMedia"], 1),
        "% Meta Manu":          f"{p['PctManu']:.0f}%",
        "Dias Trabalhados":     p["DiasTrabalh"],
        "Receita (R$)":         round(p["ReceitaGerada"], 2),
    } for p in perf_data])
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==============================
# ADMIN — EDITOR TABELAS
# ==============================
def admin_table_editor(title, table, company_id, key_prefix):
    st.subheader(title)
    conn = get_conn()
    rows = fetch_all(conn, f"SELECT id, name, is_active FROM {table} WHERE company_id=? ORDER BY id DESC", (company_id,))
    df   = df_from_rows(rows)

    with st.form(f"{key_prefix}_add"):
        st.markdown("**Adicionar novo**")
        name      = st.text_input("Nome", key=f"{key_prefix}_name")
        submitted = st.form_submit_button("Adicionar", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Informe um nome.")
            else:
                try:
                    conn.execute(f"INSERT INTO {table}(company_id, name, is_active) VALUES (?,?,1)", (company_id, name.strip()))
                    conn.commit()
                    st.success("Adicionado.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Já existe um registro com esse nome.")

    st.divider()
    if df.empty:
        st.info("Nenhum registro cadastrado ainda.")
        return

    st.markdown("**Registros**")
    for row in rows:
        rid, name, is_active = int(row["id"]), row["name"], int(row["is_active"]) == 1
        c1, c2, c3, c4 = st.columns([6, 2, 2, 2])
        c1.write(name)
        c2.write("✅ Ativo" if is_active else "⛔ Inativo")
        if c3.button("Desativar" if is_active else "Ativar", key=f"{key_prefix}_toggle_{rid}"):
            conn.execute(f"UPDATE {table} SET is_active=? WHERE company_id=? AND id=?",
                         (0 if is_active else 1, company_id, rid))
            conn.commit(); st.rerun()
        if c4.button("Excluir", key=f"{key_prefix}_del_{rid}"):
            st.session_state[f"{key_prefix}_confirm_del"] = rid
        if st.session_state.get(f"{key_prefix}_confirm_del") == rid:
            st.warning(f"Confirmar exclusão de: **{name}** ?")
            cc1, cc2 = st.columns(2)
            if cc1.button("✅ Confirmar", key=f"{key_prefix}_confirm_yes_{rid}"):
                conn.execute(f"DELETE FROM {table} WHERE company_id=? AND id=?", (company_id, rid))
                conn.commit()
                st.session_state[f"{key_prefix}_confirm_del"] = None
                st.success("Excluído."); st.rerun()
            if cc2.button("Cancelar", key=f"{key_prefix}_confirm_no_{rid}"):
                st.session_state[f"{key_prefix}_confirm_del"] = None; st.rerun()

# ==============================
# ADMIN
# ==============================
def page_admin():
    require_login()
    u = get_user()
    require_role({"admin"})
    st.header("Admin")

    tabs = st.tabs(["Técnicos", "Equipes", "Regiões", "Serviços/Valores", "Meta Mensal", "Usuários"])

    with tabs[0]: admin_table_editor("Técnicos", "technicians", u.company_id, "tech")
    with tabs[1]: admin_table_editor("Equipes",  "teams",       u.company_id, "team")
    with tabs[2]: admin_table_editor("Regiões",  "regions",     u.company_id, "reg")

    with tabs[3]:
        st.subheader("Serviços e Valores Padrão")
        conn = get_conn()
        rows = fetch_all(conn, "SELECT id, name, category, default_unit_value, is_active FROM service_types WHERE company_id=? ORDER BY name", (u.company_id,))
        df   = df_from_rows(rows)
        if not df.empty:
            st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)
        with st.form("svc_add"):
            st.markdown("**Adicionar serviço**")
            name = st.text_input("Nome do serviço")
            cat  = st.selectbox("Categoria", ["ativacao", "manutencao", "outros"])
            val  = st.number_input("Valor padrão (R$)", min_value=0.0, value=0.0, step=1.0)
            ok   = st.form_submit_button("Adicionar", use_container_width=True)
            if ok:
                if not name.strip(): st.error("Informe um nome.")
                else:
                    try:
                        conn.execute("INSERT INTO service_types(company_id, name, category, default_unit_value, is_active) VALUES (?,?,?,?,1)",
                                     (u.company_id, name.strip(), cat, float(val)))
                        conn.commit(); st.success("Serviço adicionado."); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe um serviço com esse nome.")

    with tabs[4]:
        st.subheader("Meta Mensal")
        conn  = get_conn()
        today = dt.date.today()
        year  = st.number_input("Ano da meta", min_value=2020, max_value=2100, value=today.year,  step=1, key="gy")
        month = st.number_input("Mês da meta", min_value=1,    max_value=12,   value=today.month, step=1, key="gm")
        cur   = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                          (u.company_id, int(year), int(month)))
        goal  = st.number_input("Meta (R$)", min_value=0.0, value=float(cur["goal_value"]) if cur else 0.0, step=100.0)
        if st.button("Salvar meta", type="primary"):
            conn.execute("""INSERT INTO monthly_goals(company_id, year, month, goal_value) VALUES (?,?,?,?)
                            ON CONFLICT(company_id, year, month) DO UPDATE SET goal_value=excluded.goal_value""",
                         (u.company_id, int(year), int(month), float(goal)))
            conn.commit(); st.success("Meta salva.")

    with tabs[5]:
        st.subheader("Usuários e permissões")
        conn = get_conn()
        rows = fetch_all(conn, "SELECT id, username, role, is_active, created_at FROM users WHERE company_id=? ORDER BY id DESC", (u.company_id,))
        df   = df_from_rows(rows)
        if not df.empty:
            st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

        with st.form("user_add"):
            st.markdown("**Adicionar usuário**")
            username = st.text_input("Usuário (login)")
            role     = st.selectbox("Permissão", ["admin", "operator", "viewer"])
            password = st.text_input("Senha inicial", type="password")
            ok       = st.form_submit_button("Criar usuário", use_container_width=True)
            if ok:
                if not username.strip() or not password: st.error("Informe usuário e senha.")
                else:
                    try:
                        conn.execute("INSERT INTO users(company_id, username, password_hash, role, is_active, created_at) VALUES (?,?,?,?,1,?)",
                                     (u.company_id, username.strip(), hash_password(password), role, dt.datetime.utcnow().isoformat()))
                        conn.commit(); st.success("Usuário criado."); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Usuário já existe.")

        st.divider()
        st.subheader("Ações em usuários")
        usernames = df["username"].tolist() if not df.empty else []
        if not usernames:
            st.info("Nenhum usuário cadastrado.")
        else:
            sel_user = st.selectbox("Selecione um usuário", usernames, key="sel_user_admin")
            row = fetch_one(conn, "SELECT username, role, is_active FROM users WHERE company_id=? AND username=?",
                            (u.company_id, sel_user))
            if row:
                is_active = int(row["is_active"]) == 1
                role      = row["role"]
                c1, c2    = st.columns(2)
                if c1.button("Desativar usuário" if is_active else "Ativar usuário", use_container_width=True):
                    conn.execute("UPDATE users SET is_active=? WHERE company_id=? AND username=?",
                                 (0 if is_active else 1, u.company_id, sel_user))
                    conn.commit(); st.success("Status atualizado."); st.rerun()
                new_role = c2.selectbox("Permissão", ["admin","operator","viewer"],
                                        index=["admin","operator","viewer"].index(role))
                if st.button("Salvar permissão", use_container_width=True):
                    conn.execute("UPDATE users SET role=? WHERE company_id=? AND username=?",
                                 (new_role, u.company_id, sel_user))
                    conn.commit(); st.success("Permissão atualizada."); st.rerun()
                st.divider()
                st.markdown("**Resetar senha do usuário**")
                new_pass  = st.text_input("Nova senha (reset)",   type="password", key="reset_pass")
                new_pass2 = st.text_input("Confirmar nova senha", type="password", key="reset_pass2")
                if st.button("Resetar senha", type="primary", use_container_width=True):
                    if not new_pass or new_pass != new_pass2: st.error("As senhas não conferem.")
                    else:
                        update_user_password(u.company_id, sel_user, new_pass)
                        st.success("Senha resetada com sucesso.")

# ==============================
# MAIN
# ==============================
def main():
    st.set_page_config(page_title="TechnoOps Core", page_icon="🟣", layout="wide")
    inject_css()
    init_db()

    if not get_user():
        page_login()
        return

    sidebar_header()
    page = st.sidebar.radio("Menu", ["Dashboard", "Lançamento Diário", "Resumo Mensal", "Indicadores", "Admin"])

    if   page == "Dashboard":        page_dashboard()
    elif page == "Lançamento Diário": page_daily_entry()
    elif page == "Resumo Mensal":    page_monthly_summary()
    elif page == "Indicadores":      page_technician_kpis()
    elif page == "Admin":            page_admin()

if __name__ == "__main__":
    main()
