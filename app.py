import sqlite3
import os
import datetime as dt
import hashlib
import secrets
from dataclasses import dataclass
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "technoops.db")

PRIMARY = "#7E2D7F"   # Roxo
SECONDARY = "#F2B233" # Amarelo
BG = "#0F0F0F"
CARD = "#151515"
TEXT = "#FFFFFF"
MUTED = "#CFCFCF"

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

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        theme_primary TEXT,
        theme_secondary TEXT,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','operator','viewer')),
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        UNIQUE(company_id, username),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS service_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('ativacao','manutencao','outros')),
        default_unit_value REAL NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(company_id, name),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS monthly_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        goal_value REAL NOT NULL,
        UNIQUE(company_id, year, month),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        entry_date TEXT NOT NULL,
        technician_id INTEGER NOT NULL,
        team_id INTEGER,
        region_id INTEGER,
        service_type_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit_value REAL NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(technician_id) REFERENCES technicians(id),
        FOREIGN KEY(team_id) REFERENCES teams(id),
        FOREIGN KEY(region_id) REFERENCES regions(id),
        FOREIGN KEY(service_type_id) REFERENCES service_types(id)
    );
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) AS n FROM companies;")
    n = cur.fetchone()["n"]
    if n == 0:
        now = dt.datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO companies(name, theme_primary, theme_secondary, created_at) VALUES (?,?,?,?)",
            ("Techno Mais", "#7E2D7F", "#F2B233", now)
        )
        company_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO service_types(company_id, name, category, default_unit_value, is_active) VALUES (?,?,?,?,1)",
            [
                (company_id, "Ativação", "ativacao", 210.0),
                (company_id, "Manutenção", "manutencao", 135.0),
            ]
        )
        cur.execute("INSERT INTO regions(company_id, name, is_active) VALUES (?,?,1)", (company_id, "Geral",))
        cur.execute("INSERT INTO teams(company_id, name, is_active) VALUES (?,?,1)", (company_id, "Solo",))
        cur.execute(
            "INSERT INTO users(company_id, username, password_hash, role, is_active, created_at) VALUES (?,?,?,?,1,?)",
            (company_id, "admin", hash_password("admin123"), "admin", now)
        )
        conn.commit()
    conn.close()

def inject_css():
    st.markdown(f"""
    <style>
      .stApp {{
        background: {BG};
        color: {TEXT};
      }}
      .block-container {{
        padding-top: 2rem;
      }}
      .techno-card {{
        background: {CARD};
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 16px 18px;
      }}
      .techno-kpi {{
        font-size: 1.1rem;
        color: {MUTED};
        margin-bottom: 6px;
      }}
      .techno-value {{
        font-size: 1.7rem;
        font-weight: 700;
        color: {TEXT};
      }}
      .techno-pill {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        background: rgba(242,178,51,0.18);
        border: 1px solid rgba(242,178,51,0.35);
        color: {TEXT};
        font-size: 0.85rem;
      }}
      div[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(126,45,127,0.85), rgba(15,15,15,1));
      }}
      button[kind="primary"] {{
        background: {SECONDARY} !important;
        color: #111 !important;
        border: 0 !important;
      }}
      button[kind="secondary"] {{
        border: 1px solid rgba(255,255,255,0.18) !important;
        color: {TEXT} !important;
      }}
      input, textarea {{
        color: #111 !important;
      }}
    </style>
    """, unsafe_allow_html=True)

@dataclass
class SessionUser:
    company_id: int
    company_name: str
    username: str
    role: str

def set_user(user):
    st.session_state["user"] = user

def get_user():
    return st.session_state.get("user")

def require_login():
    if not get_user():
        st.warning("Faça login para continuar.")
        st.stop()

def require_role(roles):
    u = get_user()
    if not u or u.role not in roles:
        st.error("Você não tem permissão para acessar esta área.")
        st.stop()

def fetch_all(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()

def fetch_one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()

def df_from_rows(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])

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
            company = st.text_input("Empresa", value="Techno Mais")
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
        if submitted:
            conn = get_conn()
            comp = fetch_one(conn, "SELECT * FROM companies WHERE name = ?", (company.strip(),))
            if not comp:
                st.error("Empresa não encontrada.")
                return
            user = fetch_one(conn, "SELECT * FROM users WHERE company_id=? AND username=? AND is_active=1",
                             (comp["id"], username.strip()))
            if not user or not verify_password(user["password_hash"], password):
                st.error("Usuário ou senha inválidos.")
                return
            set_user(SessionUser(company_id=comp["id"], company_name=comp["name"], username=user["username"], role=user["role"]))
            st.success("Login realizado!")
            st.rerun()

        st.divider()
        st.caption("Primeiro acesso (padrão): empresa **Techno Mais**, usuário **admin**, senha **admin123**.")

def sidebar_header():
    u = get_user()
    st.sidebar.markdown("### TechnoOps")
    sub_path = os.path.join(os.path.dirname(__file__), "assets", "submarca.png")
    if os.path.exists(sub_path):
        st.sidebar.image(sub_path, use_container_width=True)
    st.sidebar.write(f"**Empresa:** {u.company_name}")
    st.sidebar.write(f"**Usuário:** {u.username}")
    role_map = {"admin":"Admin", "operator":"Operador", "viewer":"Visualização"}
    st.sidebar.markdown(f"<span class='techno-pill'>{role_map.get(u.role,u.role)}</span>", unsafe_allow_html=True)
    if st.sidebar.button("Sair"):
        set_user(None)
        st.rerun()
    st.sidebar.divider()

def page_dashboard():
    require_login()
    u = get_user()
    st.header("Dashboard")

    today = dt.date.today()
    conn = get_conn()
    rows = fetch_all(conn, """
    SELECT e.quantity, e.unit_value
    FROM entries e
    WHERE e.company_id=? AND e.entry_date=?
    """, (u.company_id, today.isoformat()))
    total_services = sum(r["quantity"] for r in rows) if rows else 0
    total_revenue = sum(r["quantity"] * r["unit_value"] for r in rows) if rows else 0

    ym = f"{today.year:04d}-{today.month:02d}"
    m_rows = fetch_all(conn, """
    SELECT e.quantity, e.unit_value
    FROM entries e
    WHERE e.company_id=? AND substr(e.entry_date,1,7)=?
    """, (u.company_id, ym))
    m_revenue = sum(r["quantity"] * r["unit_value"] for r in m_rows) if m_rows else 0
    goal = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                     (u.company_id, today.year, today.month))
    goal_value = float(goal["goal_value"]) if goal else 0.0
    pct = (m_revenue / goal_value * 100.0) if goal_value > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Serviços hoje</div>"
                    f"<div class='techno-value'>{total_services:.0f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita hoje</div>"
                    f"<div class='techno-value'>R$ {total_revenue:,.2f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita do mês</div>"
                    f"<div class='techno-value'>R$ {m_revenue:,.2f}</div></div>", unsafe_allow_html=True)
    with c4:
        if goal_value > 0 and pct is not None:
            st.markdown("<div class='techno-card'><div class='techno-kpi'>Meta atingida</div>"
                        f"<div class='techno-value'>{pct:.0f}%</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='techno-card'><div class='techno-kpi'>Meta do mês</div>"
                        f"<div class='techno-value'>—</div></div>", unsafe_allow_html=True)

def page_daily_entry():
    require_login()
    u = get_user()
    require_role({"admin","operator"})
    st.header("Lançamento Diário")

    conn = get_conn()
    techs = df_from_rows(fetch_all(conn, "SELECT id, name FROM technicians WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    teams = df_from_rows(fetch_all(conn, "SELECT id, name FROM teams WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    regions = df_from_rows(fetch_all(conn, "SELECT id, name FROM regions WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))
    services = df_from_rows(fetch_all(conn, "SELECT id, name, category, default_unit_value FROM service_types WHERE company_id=? AND is_active=1 ORDER BY name", (u.company_id,)))

    if techs.empty:
        st.warning("Cadastre pelo menos 1 técnico no Admin → Técnicos.")
        return

    entry_date = st.date_input("Data", value=dt.date.today())

    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            tech_name = st.selectbox("Técnico", techs["name"].tolist())
            team_name = st.selectbox("Equipe", teams["name"].tolist() if not teams.empty else ["Solo"])
            region_name = st.selectbox("Região", regions["name"].tolist() if not regions.empty else ["Geral"])
        with col2:
            service_name = st.selectbox("Tipo de Serviço", services["name"].tolist())
            quantity = st.number_input("Quantidade", min_value=0.0, value=1.0, step=1.0)
            default_unit = float(services.loc[services["name"] == service_name, "default_unit_value"].iloc[0])
            unit_value = st.number_input("Valor Unitário (R$)", min_value=0.0, value=default_unit, step=1.0)
        notes = st.text_area("Observação (opcional)")

        submitted = st.form_submit_button("Salvar", use_container_width=True)
        if submitted:
            tech_id = int(techs.loc[techs["name"] == tech_name, "id"].iloc[0])
            team_id = int(teams.loc[teams["name"] == team_name, "id"].iloc[0]) if not teams.empty else None
            region_id = int(regions.loc[regions["name"] == region_name, "id"].iloc[0]) if not regions.empty else None
            service_id = int(services.loc[services["name"] == service_name, "id"].iloc[0])

            conn.execute("""
                INSERT INTO entries(company_id, entry_date, technician_id, team_id, region_id, service_type_id,
                                   quantity, unit_value, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (u.company_id, entry_date.isoformat(), tech_id, team_id, region_id, service_id,
                  float(quantity), float(unit_value), notes.strip() if notes else None, dt.datetime.utcnow().isoformat()))
            conn.commit()
            st.success("Lançamento salvo!")
            st.rerun()

    st.subheader("Lançamentos do dia")
    rows = fetch_all(conn, """
        SELECT e.id,
               e.entry_date as Data,
               t.name as Tecnico,
               tm.name as Equipe,
               r.name as Regiao,
               st.name as Servico,
               e.quantity as Qtd,
               e.unit_value as ValorUnit,
               (e.quantity*e.unit_value) as Receita,
               COALESCE(e.notes,'') as Observacao
        FROM entries e
        JOIN technicians t ON t.id=e.technician_id
        LEFT JOIN teams tm ON tm.id=e.team_id
        LEFT JOIN regions r ON r.id=e.region_id
        JOIN service_types st ON st.id=e.service_type_id
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

    with st.expander("Excluir lançamento"):
        del_id = st.selectbox("Selecione o ID para excluir", df["id"].tolist(), format_func=lambda x: f"ID {x}")
        if st.button("Excluir", type="secondary"):
            conn.execute("DELETE FROM entries WHERE company_id=? AND id=?", (u.company_id, int(del_id)))
            conn.commit()
            st.success("Excluído.")
            st.rerun()

def page_monthly_summary():
    require_login()
    u = get_user()
    st.header("Resumo Mensal")

    today = dt.date.today()
    year = st.number_input("Ano", min_value=2020, max_value=2100, value=today.year, step=1)
    month = st.number_input("Mês", min_value=1, max_value=12, value=today.month, step=1)
    ym = f"{int(year):04d}-{int(month):02d}"

    conn = get_conn()
    rows = fetch_all(conn, """
        SELECT st.category, e.quantity, e.unit_value, e.entry_date
        FROM entries e
        JOIN service_types st ON st.id=e.service_type_id
        WHERE e.company_id=? AND substr(e.entry_date,1,7)=?
    """, (u.company_id, ym))

    if not rows:
        st.info("Sem dados para este mês.")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df["receita"] = df["quantity"] * df["unit_value"]

    total_ativ = df.loc[df["category"]=="ativacao", "quantity"].sum()
    total_manu = df.loc[df["category"]=="manutencao", "quantity"].sum()
    total_srv = df["quantity"].sum()

    rec_ativ = df.loc[df["category"]=="ativacao", "receita"].sum()
    rec_manu = df.loc[df["category"]=="manutencao", "receita"].sum()
    rec_total = df["receita"].sum()

    goal_row = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                         (u.company_id, int(year), int(month)))
    goal_value = float(goal_row["goal_value"]) if goal_row else 0.0
    pct = (rec_total / goal_value * 100.0) if goal_value > 0 else None

    days_with_data = df["entry_date"].nunique()
    avg_daily = rec_total / days_with_data if days_with_data > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Total de ativações</div>"
                    f"<div class='techno-value'>{total_ativ:.0f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Total de manutenções</div>"
                    f"<div class='techno-value'>{total_manu:.0f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Total de serviços</div>"
                    f"<div class='techno-value'>{total_srv:.0f}</div></div>", unsafe_allow_html=True)

    st.divider()

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita ativações</div>"
                    f"<div class='techno-value'>R$ {rec_ativ:,.2f}</div></div>", unsafe_allow_html=True)
    with c5:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita manutenções</div>"
                    f"<div class='techno-value'>R$ {rec_manu:,.2f}</div></div>", unsafe_allow_html=True)
    with c6:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita bruta mensal</div>"
                    f"<div class='techno-value'>R$ {rec_total:,.2f}</div></div>", unsafe_allow_html=True)

    st.divider()

    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Meta de receita</div>"
                    f"<div class='techno-value'>R$ {goal_value:,.2f}</div></div>", unsafe_allow_html=True)
    with colB:
        v = f"{pct:.0f}%" if pct is not None else "—"
        st.markdown("<div class='techno-card'><div class='techno-kpi'>% meta atingida</div>"
                    f"<div class='techno-value'>{v}</div></div>", unsafe_allow_html=True)
    with colC:
        st.markdown("<div class='techno-card'><div class='techno-kpi'>Receita média diária</div>"
                    f"<div class='techno-value'>R$ {avg_daily:,.2f}</div></div>", unsafe_allow_html=True)

def page_technician_kpis():
    require_login()
    u = get_user()
    st.header("Indicadores dos Técnicos")

    today = dt.date.today()
    year = st.number_input("Ano", min_value=2020, max_value=2100, value=today.year, step=1, key="iy")
    month = st.number_input("Mês", min_value=1, max_value=12, value=today.month, step=1, key="im")
    ym = f"{int(year):04d}-{int(month):02d}"

    conn = get_conn()
    tech_rows = fetch_all(conn, """
        SELECT t.name as Tecnico,
               SUM(CASE WHEN st.category='ativacao' THEN e.quantity ELSE 0 END) as AtivacoesTotais,
               SUM(CASE WHEN st.category='manutencao' THEN e.quantity ELSE 0 END) as ManutencoesTotais,
               SUM(e.quantity) as TotalServicos,
               SUM(e.quantity*e.unit_value) as ReceitaGerada,
               COUNT(DISTINCT e.entry_date) as DiasComLancamento
        FROM entries e
        JOIN technicians t ON t.id=e.technician_id
        JOIN service_types st ON st.id=e.service_type_id
        WHERE e.company_id=? AND substr(e.entry_date,1,7)=?
        GROUP BY t.name
        ORDER BY ReceitaGerada DESC
    """, (u.company_id, ym))
    df = df_from_rows(tech_rows)
    if df.empty:
        st.info("Sem dados para este mês.")
        return

    df["MediaServicosDia"] = df.apply(lambda r: (r["TotalServicos"]/r["DiasComLancamento"]) if r["DiasComLancamento"] else 0, axis=1)
    df = df[["Tecnico","AtivacoesTotais","ManutencoesTotais","MediaServicosDia","ReceitaGerada"]]
    st.dataframe(df, use_container_width=True, hide_index=True)

def admin_table_editor(title, table, company_id, key_prefix):
    st.subheader(title)
    conn = get_conn()
    rows = fetch_all(conn, f"SELECT id, name, is_active FROM {table} WHERE company_id=? ORDER BY id DESC", (company_id,))
    df = df_from_rows(rows)
    if not df.empty:
        st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    with st.form(f"{key_prefix}_add"):
        st.markdown("**Adicionar novo**")
        name = st.text_input("Nome", key=f"{key_prefix}_name")
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

def page_admin():
    require_login()
    u = get_user()
    require_role({"admin"})
    st.header("Admin")

    tabs = st.tabs(["Técnicos", "Equipes", "Regiões", "Serviços/Valores", "Meta Mensal", "Usuários"])
    with tabs[0]:
        admin_table_editor("Técnicos", "technicians", u.company_id, "tech")
    with tabs[1]:
        admin_table_editor("Equipes", "teams", u.company_id, "team")
    with tabs[2]:
        admin_table_editor("Regiões", "regions", u.company_id, "reg")
    with tabs[3]:
        st.subheader("Serviços e Valores Padrão")
        conn = get_conn()
        rows = fetch_all(conn, """
            SELECT id, name, category, default_unit_value, is_active
            FROM service_types
            WHERE company_id=?
            ORDER BY name
        """, (u.company_id,))
        df = df_from_rows(rows)
        if not df.empty:
            st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

        with st.form("svc_add"):
            st.markdown("**Adicionar serviço**")
            name = st.text_input("Nome do serviço")
            cat = st.selectbox("Categoria", ["ativacao","manutencao","outros"])
            val = st.number_input("Valor padrão (R$)", min_value=0.0, value=0.0, step=1.0)
            ok = st.form_submit_button("Adicionar", use_container_width=True)
            if ok:
                if not name.strip():
                    st.error("Informe um nome.")
                else:
                    try:
                        conn.execute("""
                            INSERT INTO service_types(company_id, name, category, default_unit_value, is_active)
                            VALUES (?,?,?,?,1)
                        """, (u.company_id, name.strip(), cat, float(val)))
                        conn.commit()
                        st.success("Serviço adicionado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe um serviço com esse nome.")

    with tabs[4]:
        st.subheader("Meta Mensal")
        conn = get_conn()
        today = dt.date.today()
        year = st.number_input("Ano da meta", min_value=2020, max_value=2100, value=today.year, step=1, key="gy")
        month = st.number_input("Mês da meta", min_value=1, max_value=12, value=today.month, step=1, key="gm")
        current = fetch_one(conn, "SELECT goal_value FROM monthly_goals WHERE company_id=? AND year=? AND month=?",
                            (u.company_id, int(year), int(month)))
        cur_val = float(current["goal_value"]) if current else 0.0
        goal = st.number_input("Meta (R$)", min_value=0.0, value=cur_val, step=100.0)
        if st.button("Salvar meta", type="primary"):
            conn.execute("""
                INSERT INTO monthly_goals(company_id, year, month, goal_value)
                VALUES (?,?,?,?)
                ON CONFLICT(company_id, year, month) DO UPDATE SET goal_value=excluded.goal_value
            """, (u.company_id, int(year), int(month), float(goal)))
            conn.commit()
            st.success("Meta salva.")

    with tabs[5]:
        st.subheader("Usuários e permissões")
        conn = get_conn()
        rows = fetch_all(conn, """
            SELECT id, username, role, is_active, created_at
            FROM users
            WHERE company_id=?
            ORDER BY id DESC
        """, (u.company_id,))
        df = df_from_rows(rows)
        if not df.empty:
            st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

        with st.form("user_add"):
            st.markdown("**Adicionar usuário**")
            username = st.text_input("Usuário (login)")
            role = st.selectbox("Permissão", ["admin","operator","viewer"])
            password = st.text_input("Senha inicial", type="password")
            ok = st.form_submit_button("Criar usuário", use_container_width=True)
            if ok:
                if not username.strip() or not password:
                    st.error("Informe usuário e senha.")
                else:
                    try:
                        conn.execute("""
                            INSERT INTO users(company_id, username, password_hash, role, is_active, created_at)
                            VALUES (?,?,?,?,1,?)
                        """, (u.company_id, username.strip(), hash_password(password), role, dt.datetime.utcnow().isoformat()))
                        conn.commit()
                        st.success("Usuário criado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Usuário já existe.")

def main():
    st.set_page_config(page_title="TechnoOps Core", page_icon="🟣", layout="wide")
    inject_css()
    init_db()

    if not get_user():
        page_login()
        return

    sidebar_header()
    page = st.sidebar.radio("Menu", ["Dashboard", "Lançamento Diário", "Resumo Mensal", "Indicadores", "Admin"])
    if page == "Dashboard":
        page_dashboard()
    elif page == "Lançamento Diário":
        page_daily_entry()
    elif page == "Resumo Mensal":
        page_monthly_summary()
    elif page == "Indicadores":
        page_technician_kpis()
    elif page == "Admin":
        page_admin()

if __name__ == "__main__":
    main()
