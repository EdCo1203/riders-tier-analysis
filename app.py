import streamlit as st
import pandas as pd
import io
import math
from datetime import datetime

st.set_page_config(page_title="Análisis Riders", page_icon="🛵", layout="wide")

# ─────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────
SHEET_NAME = "Historicos Riders"

@st.cache_resource
def get_gsheet_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

def get_sheet():
    client = get_gsheet_client()
    if client is None: return None
    try:
        return client.open(SHEET_NAME).sheet1
    except:
        return None

def cargar_historico():
    ws = get_sheet()
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()

def guardar_decision(rider_id, nombre, tier, score, semana, fallos_str, decision, notas):
    ws = get_sheet()
    if ws is None:
        st.warning("No se pudo conectar con Google Sheets.")
        return False
    try:
        if not ws.get_all_values():
            ws.append_row(["Fecha Decisión","Rider ID","Nombre","Tier","Score",
                           "Semana","Fallos","Decisión","Notas"])
        ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"),
                       str(rider_id), nombre, tier, str(score),
                       semana, fallos_str, decision, notas])
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False

# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main{background-color:#0f0f0f}
    .block-container{padding-top:2rem}
    .rider-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem}
    .rider-card.critico{border-left:4px solid #ef4444}
    .rider-card.medio{border-left:4px solid #f59e0b}
    .rider-card.leve{border-left:4px solid #3b82f6}
    .rider-card.ok{border-left:4px solid #34d399}
    .rider-nombre{font-size:1.05rem;font-weight:700;color:#f5f5f5;margin-bottom:.2rem}
    .rider-meta{font-size:.78rem;color:#888;margin-bottom:.7rem}
    .fallo-badge{display:inline-block;background:#2a1a1a;color:#f87171;border:1px solid #ef444440;border-radius:6px;padding:2px 10px;font-size:.75rem;margin:2px 3px 2px 0}
    .day-row{background:#111;border:1px solid #222;border-radius:8px;padding:.6rem 1rem;margin:.3rem 0;font-size:.8rem}
    .day-label{color:#888;font-weight:600;margin-bottom:.3rem}
    .metric-row{display:flex;gap:.6rem;flex-wrap:wrap;margin:.3rem 0}
    .metric-item{background:#222;border-radius:6px;padding:3px 10px;font-size:.75rem;color:#bbb}
    .metric-item.mal{color:#f87171;background:#2a1212;border:1px solid #ef444430}
    .metric-item.ok{color:#34d399}
    .msg-box{background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:.9rem 1rem;font-size:.82rem;color:#ccc;white-space:pre-wrap;font-family:monospace;line-height:1.6}
    .stat-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:1rem 1.5rem;text-align:center}
    .stat-num{font-size:2rem;font-weight:800;color:#f5f5f5}
    .stat-label{font-size:.78rem;color:#888;margin-top:2px}
    .stat-num.rojo{color:#ef4444}
    .stat-num.amber{color:#f59e0b}
    .stat-num.azul{color:#3b82f6}
    .decision-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:.5rem}
    h1,h2,h3{color:#f5f5f5!important}
    .stTabs [data-baseweb="tab"]{color:#888}
    .stTabs [aria-selected="true"]{color:#f5f5f5!important}
    div[data-testid="stExpander"]{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px}
    .upload-hint{background:#1a1a1a;border:1px dashed #333;border-radius:12px;padding:2rem;text-align:center;color:#555}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────
UMBRALES = {
    "UTR":          {"op":"<",  "val":2.5,  "label":"UTR bajo",             "col":"UTR"},
    "Avg WTd":      {"op":">",  "val":5.0,  "label":"Tiempo en puerta alto","col":"Avg WTd"},
    "CDT":          {"op":">",  "val":20.0, "label":"CDT alto",             "col":"CDT"},
    "Reasignacion": {"op":">",  "val":10.0, "label":"Reasignaciones altas", "col":"% RR"},
    "Cancelacion":  {"op":">",  "val":5.0,  "label":"Cancelaciones altas",  "col":"% Cancels"},
}

UMBRALES_RAW = {
    "UTR":          {"op":"<",  "val":2.5,  "label":"UTR bajo"},
    "Pedidos":      {"op":"<",  "val":None, "label":"Pedidos insuficientes"},
    "CDT":          {"op":">",  "val":20.0, "label":"CDT alto"},
    "Reasignacion": {"op":">",  "val":10.0, "label":"Reasignaciones altas"},
    "Cancelacion":  {"op":">",  "val":5.0,  "label":"Cancelaciones altas"},
}

MENSAJES_FALLO = {
    "UTR":          "📦 Tu ritmo de pedidos por hora (UTR: {val}) está por debajo del mínimo recomendado de 2.5. Trata de mejorar tus tiempos de búsqueda y entrega, al mismo tiempo no demores en confirmar el pedido en casa del cliente.",
    "Avg WTd":      "🚪 El tiempo que tardas en confirmar la entrega en puerta ({val} min) es alto. Tener la app lista y confirmar rápido al llegar mejora mucho este indicador.",
    "CDT":          "⏱️ Tu tiempo total de entrega ({val} min) supera los 20 minutos. Revisar las rutas y salir más rápido del punto de recogida puede ayudar.",
    "Reasignacion": "🔄 Tienes un {val}% de pedidos reasignados. Te recordamos que toda reasignación de no ser justificada está prohibida. Si no te diriges al establecimiento apenas te cae la orden debes corregir esta acción de forma inmediata.",
    "Cancelacion":  "❌ Tu tasa de cancelación ({val}%) supera el 5%. Cada cancelación penaliza tu score. Si hay un problema recurrente cuéntamelo y lo vemos juntos.",
}

INTRO_WS    = "{saludo} {nombre} 👋, he revisado tus métricas de la semana pasada y quería darte un pequeño feedback para ayudarte a mejorar tu score:"
INTRO_EMAIL = "{saludo} {nombre},\n\nHe revisado tus métricas de la semana pasada y quería compartirte un feedback personalizado para ayudarte a mejorar tu rendimiento:"
CIERRE_WS    = "\n\nSi tienes cualquier duda o quieres que lo hablemos, escríbeme. ¡Ánimo! 💪"
CIERRE_EMAIL = "\n\nQuedo a tu disposición para cualquier duda o para hablar en persona.\n\nUn saludo,"

DIAS_ES = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
           "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}

# ─────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────
def safe_float(v, default=0.0):
    try:
        return default if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)
    except:
        return default

def saludo_hora():
    h = datetime.now().hour
    if 7 <= h < 12: return "Buenos días"
    elif 12 <= h < 19: return "Buenas tardes"
    else: return "Buenas noches"

def limpiar_porcentaje(df):
    for col in ["% RR","% No Show","% Cancels"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace("%","").str.strip(), errors="coerce").fillna(0.0)
    return df

def evaluar_rider_semanal(rider):
    """Evalúa fallos del CSV semanal (una fila por rider)"""
    fallos = []
    for key, u in UMBRALES.items():
        val = safe_float(rider.get(u["col"], None))
        if (u["op"] == "<" and val < u["val"]) or (u["op"] == ">" and val > u["val"]):
            fallos.append(key)
    return fallos

def calcular_metricas_dia(row):
    """Calcula métricas del CSV raw (una fila por día)"""
    completados = safe_float(row.get("orders_completed_deliveries", 0))
    cancelados  = safe_float(row.get("orders_cancelled_deliveries", 0))
    asignados   = safe_float(row.get("total_assigned", 0))
    reasignados = safe_float(row.get("total_reassigned", 0))
    horas       = safe_float(row.get("total_worked_hours", 0))
    utr         = safe_float(row.get("utr", 0))
    cdt         = safe_float(row.get("avg_courier_delivery_time", 0))
    pct_cancel  = (cancelados / asignados * 100) if asignados > 0 else 0
    pct_rr      = (reasignados / asignados * 100) if asignados > 0 else 0
    esperados   = round(horas * 2.5, 1)

    fallos = []
    detalle_fallos = {}
    if utr < 2.5:
        fallos.append("UTR")
        detalle_fallos["UTR"] = {"val": f"{utr:.2f}"}
    if horas > 0 and completados < esperados:
        fallos.append("Pedidos")
        detalle_fallos["Pedidos"] = {"horas": f"{horas:.1f}", "esperados": int(esperados), "completados": int(completados)}
    if cdt > 20:
        fallos.append("CDT")
        detalle_fallos["CDT"] = {"val": f"{cdt:.1f}"}
    if pct_rr > 10:
        fallos.append("Reasignacion")
        detalle_fallos["Reasignacion"] = {"val": f"{pct_rr:.1f}"}
    if pct_cancel > 5:
        fallos.append("Cancelacion")
        detalle_fallos["Cancelacion"] = {"val": f"{pct_cancel:.1f}"}

    return {"utr":utr,"cdt":cdt,"pct_cancel":pct_cancel,"pct_rr":pct_rr,
            "horas":horas,"completados":completados,"esperados":esperados,
            "fallos":fallos,"detalle_fallos":detalle_fallos,"n_fallos":len(fallos)}

def color_card(n):
    return "critico" if n>=3 else "medio" if n==2 else "leve" if n==1 else "ok"

def metric_html(label, val, es_malo):
    cls = "mal" if es_malo else "ok"
    return f'<span class="metric-item {cls}">{label}: <b>{val}</b></span>'

def generar_mensaje(nombre_completo, fallos_dict, canal="ws"):
    nombre = nombre_completo.split()[0].capitalize()
    saludo = saludo_hora()
    intro  = INTRO_WS.format(saludo=saludo, nombre=nombre) if canal=="ws" else INTRO_EMAIL.format(saludo=saludo, nombre=nombre)
    cierre = CIERRE_WS if canal=="ws" else CIERRE_EMAIL
    lineas = []
    for fallo, det in fallos_dict.items():
        if fallo in MENSAJES_FALLO:
            msg = MENSAJES_FALLO[fallo].format(**{k:v for k,v in det.items() if v is not None})
            lineas.append(f"• {msg}")
    return f"{intro}\n\n" + "\n\n".join(lineas) + cierre

def to_excel_multi(sheets_dict):
    """Genera Excel con múltiples hojas"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets_dict.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()

# ─────────────────────────────────────────
# UI — SUBIDA ARCHIVOS
# ─────────────────────────────────────────
st.markdown("# 🛵 Análisis de Riders")

col_up1, col_up2 = st.columns(2)
with col_up1:
    st.markdown("**📊 CSV Semanal** *(Nombre, Tier, Score, métricas)*")
    f_semanal = st.file_uploader("CSV semanal", type=["csv"], label_visibility="collapsed", key="semanal")
with col_up2:
    st.markdown("**📅 CSV Raw Diario** *(métricas por día)*")
    f_raw = st.file_uploader("CSV raw", type=["csv"], label_visibility="collapsed", key="raw")

if not f_semanal or not f_raw:
    st.markdown("""
    <div class='upload-hint' style='margin-top:1.5rem'>
        <div style='font-size:2.5rem'>📂</div>
        <div style='margin-top:.5rem'>Sube los dos archivos CSV para empezar el análisis</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────
# CARGA DATOS
# ─────────────────────────────────────────
df_sem = limpiar_porcentaje(pd.read_csv(f_semanal))
df_sem["Rider ID"] = df_sem["Rider ID"].astype(str).str.strip()

df_raw_data = pd.read_csv(f_raw)
df_raw_data["rider_id"] = df_raw_data["rider_id"].astype(str).str.strip()
df_raw_data["day"] = pd.to_datetime(df_raw_data["day"]).dt.strftime("%Y-%m-%d")
semana_str = f"{df_raw_data['day'].min()} / {df_raw_data['day'].max()}"

# Cruce raw con semanal — renombramos columnas del semanal para evitar colisiones
df_sem_merge = df_sem[["Rider ID","Nombre","Tier","Score","Contrato","Vehículo"]].copy()
df_sem_merge = df_sem_merge.rename(columns={
    "Rider ID": "sem_rider_id",
    "Nombre":   "sem_nombre",
    "Tier":     "sem_tier",
    "Score":    "sem_score",
    "Contrato": "sem_contrato",
    "Vehículo": "sem_vehiculo",
})
df_merged = df_raw_data.merge(df_sem_merge, left_on="rider_id", right_on="sem_rider_id", how="left")

# ─────────────────────────────────────────
# FILTRO TIER
# ─────────────────────────────────────────
tiers_disponibles = sorted(df_sem["Tier"].dropna().unique().tolist())
filtro_tier = st.multiselect(
    "Filtrar por Tier", tiers_disponibles,
    default=[t for t in ["Tier 4","Tier 5"] if t in tiers_disponibles]
)

# CSV semanal filtrado
df_sem_f = df_sem[df_sem["Tier"].isin(filtro_tier)].copy() if filtro_tier else df_sem.copy()
df_sem_f["_fallos"]   = df_sem_f.apply(evaluar_rider_semanal, axis=1)
df_sem_f["_n_fallos"] = df_sem_f["_fallos"].apply(len)
df_sem_f = df_sem_f.sort_values("_n_fallos", ascending=False).reset_index(drop=True)

# CSV raw filtrado
df_filtered = df_merged[df_merged["sem_tier"].isin(filtro_tier)].copy() if filtro_tier else df_merged.copy()
metricas_raw = df_filtered.apply(calcular_metricas_dia, axis=1, result_type="expand")
df_filtered = pd.concat([df_filtered.reset_index(drop=True), metricas_raw.reset_index(drop=True)], axis=1)
riders_orden = (
    df_filtered.groupby("rider_id")["n_fallos"].sum()
    .sort_values(ascending=False).index.tolist()
)

# ─────────────────────────────────────────
# STATS TOP
# ─────────────────────────────────────────
total_riders = len(df_sem_f)
criticos     = len(df_sem_f[df_sem_f["_n_fallos"] >= 3])
con_fallos   = len(df_sem_f[df_sem_f["_n_fallos"] > 0])

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-num">{total_riders}</div><div class="stat-label">Riders analizados</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-num rojo">{criticos}</div><div class="stat-label">Críticos (3+ fallos)</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-num amber">{con_fallos}</div><div class="stat-label">Con algún fallo</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-num azul">{total_riders-con_fallos}</div><div class="stat-label">Sin fallos detectados</div></div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# TABS
# ─────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Diagnóstico", "💬 Mensajes", "✅ Decisiones", "📜 Histórico", "📊 Exportar"
])

# ══════════════════════════════════════════
# TAB 1 — DIAGNÓSTICO SEMANAL (como antes)
# ══════════════════════════════════════════
with tab1:
    buscar_d  = st.text_input("🔍 Buscar por Rider ID o nombre", placeholder="Ej: 4067385 o Juan...", key="buscar_d")
    solo_f1 = st.checkbox("Solo riders con fallos", value=True, key="sf1")
    filtro_min = st.slider("Mínimo de fallos", 0, 5, 0)

    for _, rider in df_sem_f.iterrows():
        fallos   = rider["_fallos"]
        n        = len(fallos)
        nombre   = rider["Nombre"]
        rid_d    = str(rider["Rider ID"]).strip()
        if buscar_d and buscar_d.strip().lower() not in rid_d.lower() and buscar_d.strip().lower() not in nombre.lower():
            continue
        if solo_f1 and n == 0: continue
        if n < filtro_min: continue
        tier     = rider.get("Tier","—")
        score    = rider.get("Score","—")
        contrato = rider.get("Contrato","—")
        vehiculo = rider.get("Vehículo","—")
        rid      = rider["Rider ID"]
        clase    = color_card(n)

        utr_v  = safe_float(rider.get("UTR",0))
        cdt_v  = safe_float(rider.get("CDT",0))
        wtd_v  = safe_float(rider.get("Avg WTd",0))
        rr_v   = safe_float(rider.get("% RR",0))
        canc_v = safe_float(rider.get("% Cancels",0))

        metricas_html = "".join([
            metric_html("UTR",      f"{utr_v:.2f}",   "UTR"          in fallos),
            metric_html("CDT",      f"{cdt_v:.1f}m",  "CDT"          in fallos),
            metric_html("WTd",      f"{wtd_v:.1f}m",  "Avg WTd"      in fallos),
            metric_html("% RR",     f"{rr_v:.1f}%",   "Reasignacion" in fallos),
            metric_html("% Cancel", f"{canc_v:.2f}%", "Cancelacion"  in fallos),
        ])

        badges = "".join([f'<span class="fallo-badge">{UMBRALES[f]["label"]}</span>' for f in fallos]) if fallos else '<span style="color:#34d399;font-size:.8rem">✅ Sin fallos</span>'

        st.markdown(f"""
        <div class="rider-card {clase}">
            <div class="rider-nombre">{nombre}</div>
            <div class="rider-meta">ID: {rid} &nbsp;·&nbsp; {tier} &nbsp;·&nbsp; Score: {score} &nbsp;·&nbsp; {contrato}h &nbsp;·&nbsp; {vehiculo}</div>
            <div class="metric-row">{metricas_html}</div>
            <div>{badges}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 2 — MENSAJES
# ══════════════════════════════════════════
with tab2:
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        canal     = st.radio("Canal", ["WhatsApp","Email"], horizontal=True)
        canal_key = "ws" if canal=="WhatsApp" else "email"
    with col_m2:
        tipo_msg  = st.radio("Tipo de mensaje", ["Resumen semanal", "Detalle por día"], horizontal=True)

    solo_f2 = st.checkbox("Solo riders con fallos", value=True, key="sf2")

    for _, rider in df_sem_f.iterrows():
        fallos = rider["_fallos"]
        n      = len(fallos)
        if solo_f2 and n == 0: continue

        nombre = rider["Nombre"]
        tier   = rider.get("Tier","—")
        rid    = str(rider["Rider ID"]).strip()
        icono  = "🔴" if n>=3 else "🟡" if n==2 else "🔵"

        with st.expander(f"{icono} {nombre} — {tier} — {n} fallo{'s' if n!=1 else ''}"):

            if tipo_msg == "Resumen semanal":
                fallos_dict = {}
                for f in fallos:
                    col = UMBRALES[f]["col"]
                    val = safe_float(rider.get(col, 0))
                    fallos_dict[f] = {"val": f"{val:.1f}"}
                mensaje = generar_mensaje(nombre, fallos_dict, canal_key)

            else:  # Detalle por día
                df_rider_msg = df_filtered[df_filtered["rider_id"] == rid].sort_values("day")
                bloques = []
                for _, dia in df_rider_msg.iterrows():
                    if not dia["fallos"]: continue
                    try:
                        dt = datetime.strptime(dia["day"], "%Y-%m-%d")
                        dia_label = f"{DIAS_ES.get(dt.strftime('%A'),'')} {dt.strftime('%d/%m')}"
                    except:
                        dia_label = dia["day"]
                    lineas = []
                    for fallo in dia["fallos"]:
                        det = dia["detalle_fallos"].get(fallo, {})
                        if fallo in MENSAJES_FALLO:
                            msg = MENSAJES_FALLO[fallo].format(**{k:v for k,v in det.items() if v is not None})
                            lineas.append(f"  • {msg}")
                    if lineas:
                        bloques.append(f"📅 *{dia_label}*\n" + "\n".join(lineas))

                if bloques:
                    saludo = saludo_hora()
                    nombre_corto = nombre.split()[0].capitalize()
                    intro  = INTRO_WS.format(saludo=saludo, nombre=nombre_corto) if canal_key=="ws" else INTRO_EMAIL.format(saludo=saludo, nombre=nombre_corto)
                    cierre = CIERRE_WS if canal_key=="ws" else CIERRE_EMAIL
                    mensaje = intro + "\n\n" + "\n\n".join(bloques) + cierre
                else:
                    mensaje = "Sin fallos diarios detectados."

            st.markdown(f'<div class="msg-box">{mensaje}</div>', unsafe_allow_html=True)
            st.code(mensaje, language=None)

# ══════════════════════════════════════════
# TAB 3 — DECISIONES (día a día + botones)
# ══════════════════════════════════════════
with tab3:
    st.markdown("### ✅ Decisiones por rider")
    st.caption(f"Semana: **{semana_str}**")

    canal_dec     = st.radio("Canal", ["WhatsApp","Email"], horizontal=True, key="canal_dec")
    canal_dec_key = "ws" if canal_dec=="WhatsApp" else "email"
    solo_f3       = st.checkbox("Solo riders con fallos", value=True, key="sf3")
    buscar_dec    = st.text_input("🔍 Buscar por Rider ID o nombre", placeholder="Ej: 4067385 o Juan...", key="buscar_dec")

    for rid in riders_orden:
        df_rider     = df_filtered[df_filtered["rider_id"]==rid].sort_values("day")
        total_f      = int(df_rider["n_fallos"].sum())
        max_f        = int(df_rider["n_fallos"].max())
        if solo_f3 and total_f == 0: continue

        nombre   = df_rider["sem_nombre"].iloc[0] if pd.notna(df_rider["sem_nombre"].iloc[0]) else f"Rider {rid}"
        tier     = df_rider["sem_tier"].iloc[0]   if "sem_tier"  in df_rider.columns else "—"
        score    = df_rider["sem_score"].iloc[0]  if "sem_score" in df_rider.columns else "—"
        contrato = df_rider["sem_contrato"].iloc[0] if "sem_contrato" in df_rider.columns else "—"
        vehiculo = df_rider["sem_vehiculo"].iloc[0] if "sem_vehiculo" in df_rider.columns else "—"
        clase    = color_card(max_f)
        if buscar_dec and buscar_dec.strip().lower() not in rid.lower() and buscar_dec.strip().lower() not in nombre.lower():
            continue
        borde    = "#ef4444" if max_f>=3 else "#f59e0b" if max_f==2 else "#3b82f6" if max_f==1 else "#34d399"
        icono    = "🔴" if max_f>=3 else "🟡" if max_f==2 else "🔵" if max_f==1 else "✅"

        # Cabecera del rider
        fallos_semana_raw = {}
        for _, dia in df_rider.iterrows():
            for fallo in dia["fallos"]:
                if fallo not in fallos_semana_raw:
                    fallos_semana_raw[fallo] = dia["detalle_fallos"].get(fallo,{})

        fallos_str = " | ".join([UMBRALES_RAW[f]["label"] for f in fallos_semana_raw.keys()])
        badges = "".join([f'<span class="fallo-badge">{UMBRALES_RAW[f]["label"]}</span>' for f in fallos_semana_raw.keys()]) if fallos_semana_raw else '<span style="color:#34d399;font-size:.73rem">✅ Sin fallos</span>'

        st.markdown(f"""
        <div class="decision-card" style="border-left:4px solid {borde}">
            <div class="rider-nombre">{icono} {nombre}</div>
            <div class="rider-meta">ID: {rid} &nbsp;·&nbsp; {tier} &nbsp;·&nbsp; Score: {score} &nbsp;·&nbsp; {contrato}h &nbsp;·&nbsp; {vehiculo} &nbsp;·&nbsp; <b>{total_f} fallos esta semana</b></div>
            <div style="margin:.3rem 0">{badges}</div>
        </div>""", unsafe_allow_html=True)

        # Días de la semana
        dias_html = ""
        for _, dia in df_rider.iterrows():
            try:
                dt = datetime.strptime(dia["day"], "%Y-%m-%d")
                dia_label = f"{DIAS_ES.get(dt.strftime('%A'),'')} {dt.strftime('%d/%m')}"
            except:
                dia_label = dia["day"]

            fd    = dia["fallos"]
            n_dia = len(fd)
            utr_v   = safe_float(dia["utr"])
            cdt_v   = safe_float(dia["cdt"])
            comp_v  = int(safe_float(dia["completados"]))
            esp_v   = int(safe_float(dia["esperados"]))
            rr_v    = safe_float(dia["pct_rr"])
            canc_v  = safe_float(dia["pct_cancel"])
            horas_v = safe_float(dia["horas"])

            m = "".join([
                metric_html("UTR",      f"{utr_v:.2f}",      "UTR"          in fd),
                metric_html("CDT",      f"{cdt_v:.1f}m",     "CDT"          in fd),
                metric_html("Pedidos",  f"{comp_v}/{esp_v}", "Pedidos"      in fd),
                metric_html("% RR",     f"{rr_v:.1f}%",      "Reasignacion" in fd),
                metric_html("% Cancel", f"{canc_v:.1f}%",    "Cancelacion"  in fd),
                metric_html("Horas",    f"{horas_v:.1f}h",   False),
            ])
            b       = "".join([f'<span class="fallo-badge">{UMBRALES_RAW[f]["label"]}</span>' for f in fd]) if fd else '<span style="color:#34d399;font-size:.73rem">✅ OK</span>'
            col_bg  = "#ef444420" if n_dia>=3 else "#f59e0b15" if n_dia==2 else "#3b82f615" if n_dia==1 else "transparent"
            col_brd = "#ef4444"   if n_dia>=3 else "#f59e0b"   if n_dia==2 else "#3b82f6"   if n_dia==1 else "#34d399"

            dias_html += f'<div class="day-row" style="border-left:3px solid {col_brd};background:{col_bg}"><div class="day-label">{dia_label}</div><div class="metric-row">{m}</div><div>{b}</div></div>'

        st.markdown(dias_html, unsafe_allow_html=True)

        # Notas + botones
        notas = st.text_input("Notas (opcional)", key=f"notas_{rid}", placeholder="Ej: problema de zona, ya contactado...")
        col_c, col_p = st.columns(2)
        with col_c:
            if st.button("✅ Contactar", key=f"contactar_{rid}", use_container_width=True):
                ok = guardar_decision(rid, nombre, tier, score, semana_str, fallos_str, "Contactar", notas)
                if ok: st.success(f"Guardado: {nombre} → Contactar")
        with col_p:
            if st.button("❌ Prescindir", key=f"prescindir_{rid}", use_container_width=True):
                ok = guardar_decision(rid, nombre, tier, score, semana_str, fallos_str, "Prescindir", notas)
                if ok: st.warning(f"Guardado: {nombre} → Prescindir")

        st.markdown("---")

# ══════════════════════════════════════════
# TAB 4 — HISTÓRICO
# ══════════════════════════════════════════
with tab4:
    st.markdown("### 📜 Histórico de decisiones")
    if st.button("🔄 Actualizar"):
        st.cache_resource.clear()
        st.rerun()

    df_hist = cargar_historico()

    if df_hist.empty:
        st.info("Aún no hay decisiones guardadas.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_dec = st.multiselect("Filtrar decisión", ["Contactar","Prescindir"], default=["Contactar","Prescindir"])
        with col_f2:
            if "Semana" in df_hist.columns:
                semanas    = df_hist["Semana"].dropna().unique().tolist()
                filtro_sem = st.multiselect("Filtrar semana", semanas, default=semanas)
            else:
                filtro_sem = []

        df_hist_f = df_hist.copy()
        if filtro_dec and "Decisión" in df_hist_f.columns:
            df_hist_f = df_hist_f[df_hist_f["Decisión"].isin(filtro_dec)]
        if filtro_sem and "Semana" in df_hist_f.columns:
            df_hist_f = df_hist_f[df_hist_f["Semana"].isin(filtro_sem)]

        if "Decisión" in df_hist_f.columns:
            n_c = len(df_hist_f[df_hist_f["Decisión"]=="Contactar"])
            n_p = len(df_hist_f[df_hist_f["Decisión"]=="Prescindir"])
            hc1,hc2,hc3 = st.columns(3)
            with hc1: st.markdown(f'<div class="stat-box"><div class="stat-num">{len(df_hist_f)}</div><div class="stat-label">Total decisiones</div></div>', unsafe_allow_html=True)
            with hc2: st.markdown(f'<div class="stat-box"><div class="stat-num azul">{n_c}</div><div class="stat-label">Contactar</div></div>', unsafe_allow_html=True)
            with hc3: st.markdown(f'<div class="stat-box"><div class="stat-num rojo">{n_p}</div><div class="stat-label">Prescindir</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_hist_f, use_container_width=True, hide_index=True)

        st.download_button(
            label="⬇️ Descargar histórico Excel",
            data=to_excel_multi({"Histórico decisiones": df_hist_f}),
            file_name="historico_decisiones.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ══════════════════════════════════════════
# TAB 5 — EXPORTAR (informe + histórico)
# ══════════════════════════════════════════
with tab5:
    st.markdown("### 📊 Exportar informe completo")

    # Hoja 1: diagnóstico semanal
    rows_sem = []
    for _, rider in df_sem_f.iterrows():
        rows_sem.append({
            "Rider ID":      rider["Rider ID"],
            "Nombre":        rider["Nombre"],
            "Tier":          rider.get("Tier","—"),
            "Score":         rider.get("Score","—"),
            "Contrato":      rider.get("Contrato","—"),
            "Vehículo":      rider.get("Vehículo","—"),
            "UTR":           safe_float(rider.get("UTR",0)),
            "CDT":           safe_float(rider.get("CDT",0)),
            "Avg WTd":       safe_float(rider.get("Avg WTd",0)),
            "% RR":          safe_float(rider.get("% RR",0)),
            "% Cancels":     safe_float(rider.get("% Cancels",0)),
            "Nº fallos":     rider["_n_fallos"],
            "Fallos":        " | ".join([UMBRALES[f]["label"] for f in rider["_fallos"]]) if rider["_fallos"] else "Sin fallos",
        })
    df_exp_sem = pd.DataFrame(rows_sem)

    # Hoja 2: detalle día a día
    rows_dia = []
    for rid in riders_orden:
        df_rider = df_filtered[df_filtered["rider_id"]==rid].sort_values("day")
        nombre   = df_rider["sem_nombre"].iloc[0] if pd.notna(df_rider["sem_nombre"].iloc[0]) else f"Rider {rid}"
        tier     = df_rider["sem_tier"].iloc[0]   if "sem_tier"  in df_rider.columns else "—"
        score    = df_rider["sem_score"].iloc[0]  if "sem_score" in df_rider.columns else "—"
        for _, dia in df_rider.iterrows():
            rows_dia.append({
                "Rider ID":       rid, "Nombre": nombre, "Tier": tier, "Score": score,
                "Fecha":          dia["day"],
                "Horas":          round(safe_float(dia["horas"]),2),
                "UTR":            round(safe_float(dia["utr"]),3),
                "CDT (min)":      round(safe_float(dia["cdt"]),1),
                "Completados":    int(safe_float(dia["completados"])),
                "Esperados":      int(safe_float(dia["esperados"])),
                "% Reasignación": round(safe_float(dia["pct_rr"]),2),
                "% Cancelación":  round(safe_float(dia["pct_cancel"]),2),
                "Nº fallos":      dia["n_fallos"],
                "Fallos":         " | ".join([UMBRALES_RAW[f]["label"] for f in dia["fallos"]]) if dia["fallos"] else "Sin fallos",
            })
    df_exp_dia = pd.DataFrame(rows_dia)

    # Hoja 3: histórico decisiones
    df_hist_exp = cargar_historico()

    st.dataframe(df_exp_sem, use_container_width=True, hide_index=True)

    sheets = {
        "Diagnóstico semanal": df_exp_sem,
        "Detalle por día":     df_exp_dia,
    }
    if not df_hist_exp.empty:
        sheets["Histórico decisiones"] = df_hist_exp

    st.download_button(
        label="⬇️ Descargar Excel completo",
        data=to_excel_multi(sheets),
        file_name="informe_riders_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )