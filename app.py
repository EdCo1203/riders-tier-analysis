import streamlit as st
import pandas as pd
import io

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Análisis Riders",
    page_icon="🛵",
    layout="wide"
)

# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f0f0f; }
    .block-container { padding-top: 2rem; }

    .rider-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .rider-card.critico { border-left: 4px solid #ef4444; }
    .rider-card.medio   { border-left: 4px solid #f59e0b; }
    .rider-card.leve    { border-left: 4px solid #3b82f6; }

    .rider-nombre {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f5f5f5;
        margin-bottom: 0.2rem;
    }
    .rider-meta {
        font-size: 0.78rem;
        color: #888;
        margin-bottom: 0.7rem;
    }
    .fallo-badge {
        display: inline-block;
        background: #2a1a1a;
        color: #f87171;
        border: 1px solid #ef444440;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin: 2px 3px 2px 0;
    }
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 0.6rem 0 0.8rem 0;
        flex-wrap: wrap;
    }
    .metric-item {
        background: #222;
        border-radius: 8px;
        padding: 4px 12px;
        font-size: 0.8rem;
        color: #bbb;
    }
    .metric-item.mal { color: #f87171; background: #2a1212; border: 1px solid #ef444430; }
    .metric-item.ok  { color: #34d399; }

    .msg-box {
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        font-size: 0.82rem;
        color: #ccc;
        white-space: pre-wrap;
        font-family: monospace;
        line-height: 1.6;
    }
    .stat-box {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        text-align: center;
    }
    .stat-num { font-size: 2rem; font-weight: 800; color: #f5f5f5; }
    .stat-label { font-size: 0.78rem; color: #888; margin-top: 2px; }
    .stat-num.rojo { color: #ef4444; }
    .stat-num.amber { color: #f59e0b; }
    .stat-num.azul { color: #3b82f6; }

    h1, h2, h3 { color: #f5f5f5 !important; }
    .stTabs [data-baseweb="tab"] { color: #888; }
    .stTabs [aria-selected="true"] { color: #f5f5f5 !important; }
    div[data-testid="stExpander"] { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# UMBRALES
# ─────────────────────────────────────────
UMBRALES = {
    "UTR":          {"col": "UTR",       "op": "<",  "val": 2.5,  "label": "UTR bajo",            "desc": "Menos de 2.5 pedidos/hora"},
    "Avg WTd":      {"col": "Avg WTd",   "op": ">",  "val": 5.9,  "label": "Tiempo en puerta alto","desc": "Más de 5 min confirmando entrega"},
    "CDT":          {"col": "CDT",       "op": ">",  "val": 20.9, "label": "CDT alto",             "desc": "Más de 20 min de entrega total"},
    "Reasignacion": {"col": "% RR",      "op": ">",  "val": 0.0, "label": "Reasignaciones altas", "desc": "Se detectan pedidos reasignados de pedidos reasignados"},
    "Cancelacion":  {"col": "% Cancels", "op": ">",  "val": 5.0,  "label": "Cancelaciones altas",  "desc": "Más del 5% de pedidos cancelados"},
}

# ─────────────────────────────────────────
# MENSAJES PERSONALIZADOS
# ─────────────────────────────────────────
MENSAJES_FALLO = {
    "UTR":          "📦 Tu ritmo de pedidos por hora (UTR: {val}) está por debajo del mínimo recomendado de 2.5. Trata de mejorar tus tiempos de busqueda y entrega, al mismo tiempo no demores en confirmar el pedido en casa de cliente.",
    "Avg WTd":      "🚪 El tiempo que tardas en confirmar la entrega en puerta ({val} min) es alto. Tener la app lista y confirmar rápido al llegar mejora mucho este indicador.",
    "CDT":          "⏱️ Tu tiempo total de entrega ({val} min) supera los 20 minutos. Revisar las rutas y salir más rápido del punto de recogida puede ayudar.",
    "Reasignacion": "🔄 Tienes un {val}% de pedidos que se te reasignan. Apresurate al buscar los pedidos con más rapidez y mantenerte cerca de las zonas de alta demanda reduce esto.",
    "Cancelacion":  "❌ Tu tasa de cancelación ({val}%) supera el 5%. Cada cancelación penaliza tu score. Si hay un problema recurrente cuéntamelo y lo vemos juntos.",
}

INTRO_WS_SEMANAL  = "Hola {nombre} 👋, he revisado tus métricas de esta semana y quería darte un pequeño feedback para ayudarte a mejorar tu score:"
INTRO_WS_DIARIO   = "Hola {nombre} 👋, he revisado tus métricas de hoy y quería darte un pequeño feedback para ayudarte a mejorar tu score:"
INTRO_EMAIL_SEMANAL = "Hola {nombre},\n\nHe revisado tus métricas de esta semana y quería compartirte un feedback personalizado para ayudarte a mejorar tu rendimiento:"
INTRO_EMAIL_DIARIO  = "Hola {nombre},\n\nHe revisado tus métricas de hoy y quería compartirte un feedback personalizado para ayudarte a mejorar tu rendimiento:"
CIERRE_WS   = "\n\nSi tienes cualquier duda o quieres que lo hablemos, escríbeme. ¡Ánimo! "
CIERRE_EMAIL = "\n\nQuedo a tu disposición para cualquier duda o para hablar en persona.\n\nUn saludo,"

# ─────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────
def limpiar_porcentaje(df):
    for col in ["% RR", "% No Show", "% Cancels"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df

def evaluar_rider(rider):
    fallos = []
    for key, u in UMBRALES.items():
        val = rider.get(u["col"], None)
        if pd.isna(val):
            continue
        if (u["op"] == "<" and val < u["val"]) or (u["op"] == ">" and val > u["val"]):
            fallos.append(key)
    return fallos

def generar_mensaje(rider, fallos, canal="ws", periodo="semanal"):
    nombre = rider["Nombre"].split()[0].capitalize()
    if canal == "ws":
        intro = INTRO_WS_SEMANAL.format(nombre=nombre) if periodo == "semanal" else INTRO_WS_DIARIO.format(nombre=nombre)
    else:
        intro = INTRO_EMAIL_SEMANAL.format(nombre=nombre) if periodo == "semanal" else INTRO_EMAIL_DIARIO.format(nombre=nombre)
    cierre = CIERRE_WS if canal == "ws" else CIERRE_EMAIL

    lineas = []
    for fallo in fallos:
        u = UMBRALES[fallo]
        val_raw = rider.get(u["col"], "?")
        if isinstance(val_raw, float):
            val_fmt = f"{val_raw:.1f}{'%' if '%' in u['col'] else ''}"
        else:
            val_fmt = str(val_raw)
        lineas.append(MENSAJES_FALLO[fallo].format(val=val_fmt))

    cuerpo = "\n\n".join(f"• {l}" for l in lineas)
    return f"{intro}\n\n{cuerpo}{cierre}"

def color_card(n_fallos):
    if n_fallos >= 3: return "critico"
    if n_fallos == 2: return "medio"
    return "leve"

def metric_html(label, val, es_malo):
    cls = "mal" if es_malo else "ok"
    return f'<span class="metric-item {cls}">{label}: <b>{val}</b></span>'

def to_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Análisis Tiers")
    return buf.getvalue()

# ─────────────────────────────────────────
# UI PRINCIPAL
# ─────────────────────────────────────────
st.markdown("# 🛵 Análisis de Riders — Tier")
st.markdown("Sube el CSV semanal y obtén el diagnóstico completo con mensajes listos para enviar.")

uploaded = st.file_uploader("Arrastra el CSV aquí", type=["csv"], label_visibility="collapsed")

if not uploaded:
    st.markdown("""
    <div style='background:#1a1a1a;border:1px dashed #333;border-radius:12px;padding:3rem;text-align:center;color:#555;margin-top:2rem;'>
        <div style='font-size:3rem'>📂</div>
        <div style='margin-top:0.5rem'>Sube el CSV de análisis semanal para empezar</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────
# PROCESADO
# ─────────────────────────────────────────
df_raw = pd.read_csv(uploaded)
df_raw = limpiar_porcentaje(df_raw)
df45 = df_raw[df_raw["Tier"].isin(["Tier 1","Tier 2","Tier 3","Tier 4", "Tier 5"])].copy()

if df45.empty:
    st.warning("No se encontraron riders de Tier 1, Tier 2, Tier 3, Tier 4 o Tier 5 en este archivo.")
    st.stop()

# Evaluar fallos
df45["_fallos"] = df45.apply(lambda r: evaluar_rider(r), axis=1)
df45["_n_fallos"] = df45["_fallos"].apply(len)
df45_sorted = df45.sort_values("_n_fallos", ascending=False).reset_index(drop=True)

# ─────────────────────────────────────────
# ESTADÍSTICAS TOP
# ─────────────────────────────────────────
total = len(df45_sorted)
criticos = len(df45_sorted[df45_sorted["_n_fallos"] >= 3])
con_fallos = len(df45_sorted[df45_sorted["_n_fallos"] > 0])
sin_fallos = total - con_fallos

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Riders analizados</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-box"><div class="stat-num rojo">{criticos}</div><div class="stat-label">Críticos (3+ fallos)</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-box"><div class="stat-num amber">{con_fallos}</div><div class="stat-label">Con algún fallo</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-box"><div class="stat-num azul">{sin_fallos}</div><div class="stat-label">Sin fallos detectados</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# TABS
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Riders y diagnóstico", "💬 Mensajes", "📊 Exportar"])

# ══════════════════════════════════════════
# TAB 1 — DIAGNÓSTICO
# ══════════════════════════════════════════
with tab1:
    filtro_tier = st.multiselect("Filtrar por Tier", ["Tier 1", "Tier 2", "Tier 3","Tier 4", "Tier 5"], default=["Tier 4", "Tier 5"], key="filtro_tier_tab1")
    filtro_min_fallos = st.slider("Mínimo de fallos", 0, 5, 0)

    riders_filtrados = df45_sorted[
        (df45_sorted["Tier"].isin(filtro_tier)) &
        (df45_sorted["_n_fallos"] >= filtro_min_fallos)
    ]

    for _, rider in riders_filtrados.iterrows():
        fallos = rider["_fallos"]
        n = len(fallos)
        clase = color_card(n)
        nombre = rider["Nombre"]
        tier = rider["Tier"]
        score = rider["Score"]
        contrato = rider.get("Contrato", "")
        vehiculo = rider.get("Vehículo", "")

        utr_val   = rider.get("UTR", 0)
        cdt_val   = rider.get("CDT", 0)
        wtd_val   = rider.get("Avg WTd", 0)
        rr_val    = rider.get("% RR", 0)
        canc_val  = rider.get("% Cancels", 0)

        metricas_html = "".join([
            metric_html("UTR", f"{utr_val:.2f}", "UTR" in fallos),
            metric_html("CDT", f"{cdt_val:.1f}m", "CDT" in fallos),
            metric_html("WTd", f"{wtd_val:.1f}m", "Avg WTd" in fallos),
            metric_html("% RR", f"{rr_val:.1f}%", "Reasignacion" in fallos),
            metric_html("% Cancels", f"{canc_val:.2f}%", "Cancelacion" in fallos),
        ])

        badges = "".join([f'<span class="fallo-badge">{UMBRALES[f]["label"]}</span>' for f in fallos])
        if not fallos:
            badges = '<span style="color:#34d399;font-size:0.8rem">✅ Sin fallos detectados</span>'

        st.markdown(f"""
        <div class="rider-card {clase}">
            <div class="rider-nombre">{nombre}</div>
            <div class="rider-meta">ID: {rider['Rider ID']} &nbsp;·&nbsp; {tier} &nbsp;·&nbsp; Score: {score} &nbsp;·&nbsp; {contrato}h &nbsp;·&nbsp; {vehiculo}</div>
            <div class="metric-row">{metricas_html}</div>
            <div>{badges}</div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 2 — MENSAJES
# ══════════════════════════════════════════
with tab2:
    filtro_tier_msj = st.multiselect("Filtrar por Tier", ["Tier 1", "Tier 2", "Tier 3","Tier 4", "Tier 5"], default=["Tier 4", "Tier 5"], key="filtro_tier_tab2")
    riders_filtrados_msj = df45_sorted[
        (df45_sorted["Tier"].isin(filtro_tier_msj))
    ]
    
    canal = st.radio("Canal de contacto", ["WhatsApp", "Email"], horizontal=True)
    canal_key = "ws" if canal == "WhatsApp" else "email"
    periodo = st.selectbox("Período del informe", ["Semanal", "Diario"])
    periodo_key = "semanal" if periodo == "Semanal" else "diario"
    
    solo_con_fallos = st.checkbox("Mostrar solo riders con fallos", value=True)

    riders_msg = df45_sorted[
        (df45_sorted["Tier"].isin(filtro_tier_msj)) &
        (df45_sorted["_n_fallos"] > 0)] if solo_con_fallos else df45_sorted

    for _, rider in riders_msg.iterrows():
        fallos = rider["_fallos"]
        if not fallos:
            continue

        nombre = rider["Nombre"]
        tier = rider["Tier"]
        n = len(fallos)
        mensaje = generar_mensaje(rider, fallos, canal_key, periodo_key)

        with st.expander(f"{'🔴' if n >= 3 else '🟡' if n == 2 else '🔵'} {nombre} - {tier} — {n} fallo{'s' if n > 1 else ''}"):
            st.markdown(f'<div class="msg-box">{mensaje}</div>', unsafe_allow_html=True)
            st.code(mensaje, language=None)

# ══════════════════════════════════════════
# TAB 3 — EXPORTAR
# ══════════════════════════════════════════
with tab3:
    st.markdown("### Exportar informe completo")

    df_export = df45_sorted[[
        "Rider ID", "Nombre", "Tier", "Score", "Contrato", "Vehículo",
        "UTR", "CDT", "Avg WTd", "% RR", "% Cancels", "_n_fallos", "_fallos"
    ]].copy()
    df_export.columns = [
        "Rider ID", "Nombre", "Tier", "Score", "Contrato", "Vehículo",
        "UTR", "CDT", "Avg WTd", "% RR", "% Cancels", "Nº fallos", "Fallos"
    ]
    df_export["Fallos"] = df_export["Fallos"].apply(
        lambda fs: " | ".join([UMBRALES[f]["label"] for f in fs]) if fs else "Sin fallos"
    )

    st.dataframe(df_export, use_container_width=True, hide_index=True)

    excel_data = to_excel(df_export)
    st.download_button(
        label="⬇️ Descargar Excel",
        data=excel_data,
        file_name="informe_riders_tier4_5.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )