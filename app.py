import streamlit as st
import pandas as pd
import io
from datetime import datetime

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
    .rider-card.ok      { border-left: 4px solid #34d399; }

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
    .day-row {
        background: #111;
        border: 1px solid #222;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.8rem;
    }
    .day-label {
        color: #888;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .metric-row {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin: 0.3rem 0;
    }
    .metric-item {
        background: #222;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 0.75rem;
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
    .stat-num.rojo  { color: #ef4444; }
    .stat-num.amber { color: #f59e0b; }
    .stat-num.azul  { color: #3b82f6; }

    h1, h2, h3 { color: #f5f5f5 !important; }
    .stTabs [data-baseweb="tab"] { color: #888; }
    .stTabs [aria-selected="true"] { color: #f5f5f5 !important; }
    div[data-testid="stExpander"] { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; }
    .upload-hint { background:#1a1a1a; border:1px dashed #333; border-radius:12px; padding:2rem; text-align:center; color:#555; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# UMBRALES
# ─────────────────────────────────────────
UMBRALES = {
    "UTR":          {"op": "<",  "val": 2.5,  "label": "UTR bajo",             "desc": "Menos de 2.5 pedidos/hora"},
    "Pedidos":      {"op": "<",  "val": None, "label": "Pedidos insuficientes", "desc": "Completó menos pedidos de los esperados según horas trabajadas"},
    "CDT":          {"op": ">",  "val": 20.0, "label": "CDT alto",              "desc": "Más de 20 min de entrega total"},
    "Reasignacion": {"op": ">",  "val": 10.0, "label": "Reasignaciones altas",  "desc": "Más del 10% de pedidos reasignados"},
    "Cancelacion":  {"op": ">",  "val": 5.0,  "label": "Cancelaciones altas",   "desc": "Más del 5% de pedidos cancelados"},
}

MENSAJES_FALLO = {
    "UTR":          "📦 Tu ritmo de pedidos por hora (UTR: {val}) está por debajo del mínimo recomendado de 2.5. Trata de mejorar tus tiempos de búsqueda y entrega, al mismo tiempo no demores en confirmar el pedido en casa del cliente.",
    "Pedidos":      "📊 Según tus horas trabajadas ({horas}h) deberías haber completado al menos {esperados} pedidos, pero completaste {completados}. Intenta mantener el ritmo durante toda la jornada.",
    "CDT":          "⏱️ Tu tiempo total de entrega ({val} min) supera los 20 minutos. Revisar las rutas y salir más rápido del punto de recogida puede ayudar.",
    "Reasignacion": "🔄 Tienes un {val}% de pedidos reasignados. Te recordamos que toda reasignación de no ser justificada está prohibida. Si no te diriges al establecimiento apenas te cae la orden debes corregir esta acción de forma inmediata.",
    "Cancelacion":  "❌ Tu tasa de cancelación ({val}%) supera el 5%. Cada cancelación penaliza tu score. Si hay un problema recurrente cuéntamelo y lo vemos juntos.",
}

INTRO_WS_SEMANAL    = "{saludo} {nombre} 👋, he revisado tus métricas de la semana pasada y quería darte un pequeño feedback para ayudarte a mejorar tu score:"
INTRO_WS_DIARIO     = "{saludo} {nombre} 👋, he revisado tus métricas de ayer y quería darte un pequeño feedback para ayudarte a mejorar tu score:"
INTRO_EMAIL_SEMANAL = "{saludo} {nombre},\n\nHe revisado tus métricas de la semana pasada y quería compartirte un feedback personalizado para ayudarte a mejorar tu rendimiento:"
INTRO_EMAIL_DIARIO  = "{saludo} {nombre},\n\nHe revisado tus métricas de ayer y quería compartirte un feedback personalizado para ayudarte a mejorar tu rendimiento:"
CIERRE_WS    = "\n\nSi tienes cualquier duda o quieres que lo hablemos, escríbeme. ¡Ánimo! 💪"
CIERRE_EMAIL = "\n\nQuedo a tu disposición para cualquier duda o para hablar en persona.\n\nUn saludo,"

DIAS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

# ─────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────
def saludo_hora():
    hora = datetime.now().hour
    if 7 <= hora < 12:   return "Buenos días"
    elif 12 <= hora < 19: return "Buenas tardes"
    else:                  return "Buenas noches"

def limpiar_porcentaje(df):
    for col in ["% RR", "% No Show", "% Cancels"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df

def calcular_metricas_dia(row):
    """Calcula métricas y fallos para una fila del raw diario"""
    completados  = row.get("orders_completed_deliveries", 0) or 0
    cancelados   = row.get("orders_cancelled_deliveries", 0) or 0
    asignados    = row.get("total_assigned", 0) or 0
    reasignados  = row.get("total_reassigned", 0) or 0
    horas        = row.get("total_worked_hours", 0) or 0
    utr          = row.get("utr", 0) or 0
    cdt          = row.get("avg_courier_delivery_time", 0) or 0

    pct_cancel   = (cancelados / asignados * 100) if asignados > 0 else 0
    pct_rr       = (reasignados / asignados * 100) if asignados > 0 else 0
    esperados    = round(horas * 2.5, 1)

    fallos = []
    detalle_fallos = {}

    if utr < 2.5:
        fallos.append("UTR")
        detalle_fallos["UTR"] = {"val": f"{utr:.2f}", "horas": None, "esperados": None, "completados": None}

    if horas > 0 and completados < esperados:
        fallos.append("Pedidos")
        detalle_fallos["Pedidos"] = {"val": None, "horas": f"{horas:.1f}", "esperados": int(esperados), "completados": int(completados)}

    if cdt > 20:
        fallos.append("CDT")
        detalle_fallos["CDT"] = {"val": f"{cdt:.1f}"}

    if pct_rr > 10:
        fallos.append("Reasignacion")
        detalle_fallos["Reasignacion"] = {"val": f"{pct_rr:.1f}"}

    if pct_cancel > 5:
        fallos.append("Cancelacion")
        detalle_fallos["Cancelacion"] = {"val": f"{pct_cancel:.1f}"}

    return {
        "utr": utr,
        "cdt": cdt,
        "pct_cancel": pct_cancel,
        "pct_rr": pct_rr,
        "horas": horas,
        "completados": completados,
        "esperados": esperados,
        "asignados": asignados,
        "fallos": fallos,
        "detalle_fallos": detalle_fallos,
        "n_fallos": len(fallos),
    }

def color_card(n_fallos):
    if n_fallos >= 3: return "critico"
    if n_fallos == 2: return "medio"
    if n_fallos == 1: return "leve"
    return "ok"

def metric_html(label, val, es_malo):
    cls = "mal" if es_malo else "ok"
    return f'<span class="metric-item {cls}">{label}: <b>{val}</b></span>'

def generar_mensaje_diario(nombre_completo, dias_con_fallos, canal="ws"):
    nombre = nombre_completo.split()[0].capitalize()
    saludo = saludo_hora()
    intro  = INTRO_WS_DIARIO.format(saludo=saludo, nombre=nombre) if canal == "ws" else INTRO_EMAIL_DIARIO.format(saludo=saludo, nombre=nombre)
    cierre = CIERRE_WS if canal == "ws" else CIERRE_EMAIL

    bloques = []
    for dia_info in dias_con_fallos:
        fecha_str = dia_info["fecha"]
        try:
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            dia_label = f"{DIAS_ES.get(dt.strftime('%A'), dt.strftime('%A'))} {dt.strftime('%d/%m')}"
        except:
            dia_label = fecha_str

        lineas = []
        for fallo in dia_info["fallos"]:
            det = dia_info["detalle_fallos"].get(fallo, {})
            msg = MENSAJES_FALLO[fallo].format(**{k: v for k, v in det.items() if v is not None})
            lineas.append(f"  • {msg}")

        bloque = f"📅 *{dia_label}*\n" + "\n".join(lineas)
        bloques.append(bloque)

    cuerpo = "\n\n".join(bloques)
    return f"{intro}\n\n{cuerpo}{cierre}"

def generar_mensaje_semanal(nombre_completo, fallos_semana, canal="ws"):
    nombre = nombre_completo.split()[0].capitalize()
    saludo = saludo_hora()
    intro  = INTRO_WS_SEMANAL.format(saludo=saludo, nombre=nombre) if canal == "ws" else INTRO_EMAIL_SEMANAL.format(saludo=saludo, nombre=nombre)
    cierre = CIERRE_WS if canal == "ws" else CIERRE_EMAIL

    lineas = []
    for fallo, det in fallos_semana.items():
        msg = MENSAJES_FALLO[fallo].format(**{k: v for k, v in det.items() if v is not None})
        lineas.append(f"• {msg}")

    cuerpo = "\n\n".join(lineas)
    return f"{intro}\n\n{cuerpo}{cierre}"

def to_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Análisis Riders")
    return buf.getvalue()

# ─────────────────────────────────────────
# UI PRINCIPAL
# ─────────────────────────────────────────
st.markdown("# 🛵 Análisis de Riders")
st.markdown("Sube los dos CSV para obtener el diagnóstico día a día con mensajes listos para enviar.")

col_up1, col_up2 = st.columns(2)
with col_up1:
    st.markdown("**📊 CSV Semanal** *(Nombre, Tier, Score)*")
    f_semanal = st.file_uploader("CSV semanal", type=["csv"], label_visibility="collapsed", key="semanal")
with col_up2:
    st.markdown("**📅 CSV Raw Diario** *(métricas por día)*")
    f_raw = st.file_uploader("CSV raw", type=["csv"], label_visibility="collapsed", key="raw")

if not f_semanal or not f_raw:
    st.markdown("""
    <div class='upload-hint' style='margin-top:1.5rem'>
        <div style='font-size:2.5rem'>📂</div>
        <div style='margin-top:0.5rem'>Sube los dos archivos CSV para empezar el análisis</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────
# CARGA Y CRUCE
# ─────────────────────────────────────────
df_sem = pd.read_csv(f_semanal)
df_sem = limpiar_porcentaje(df_sem)
df_sem["Rider ID"] = df_sem["Rider ID"].astype(str).str.strip()

df_raw = pd.read_csv(f_raw)
df_raw["rider_id"] = df_raw["rider_id"].astype(str).str.strip()
df_raw["day"] = pd.to_datetime(df_raw["day"]).dt.strftime("%Y-%m-%d")

# Cruce por ID
df_merged = df_raw.merge(
    df_sem[["Rider ID", "Nombre", "Tier", "Score", "Contrato", "Vehículo"]],
    left_on="rider_id", right_on="Rider ID",
    how="left"
)

# Filtro de tiers
tiers_disponibles = sorted(df_sem["Tier"].dropna().unique().tolist())
filtro_tier = st.multiselect(
    "Filtrar por Tier", tiers_disponibles,
    default=[t for t in ["Tier 4", "Tier 5"] if t in tiers_disponibles]
)

df_filtered = df_merged[df_merged["Tier"].isin(filtro_tier)].copy() if filtro_tier else df_merged.copy()

# Calcular métricas por fila (día)
metricas = df_filtered.apply(calcular_metricas_dia, axis=1, result_type="expand")
df_filtered = pd.concat([df_filtered.reset_index(drop=True), metricas.reset_index(drop=True)], axis=1)

# Agrupar por rider
riders_ids = df_filtered["rider_id"].unique()

# ─────────────────────────────────────────
# ESTADÍSTICAS TOP
# ─────────────────────────────────────────
riders_con_fallos = sum(
    1 for rid in riders_ids
    if df_filtered[df_filtered["rider_id"] == rid]["n_fallos"].sum() > 0
)
total_riders = len(riders_ids)
criticos = sum(
    1 for rid in riders_ids
    if df_filtered[df_filtered["rider_id"] == rid]["n_fallos"].max() >= 3
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{total_riders}</div><div class="stat-label">Riders analizados</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-box"><div class="stat-num rojo">{criticos}</div><div class="stat-label">Con día crítico (3+ fallos)</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-box"><div class="stat-num amber">{riders_con_fallos}</div><div class="stat-label">Con algún fallo</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-box"><div class="stat-num azul">{total_riders - riders_con_fallos}</div><div class="stat-label">Sin fallos detectados</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# TABS
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Diagnóstico día a día", "💬 Mensajes", "📊 Exportar"])

# ══════════════════════════════════════════
# TAB 1 — DIAGNÓSTICO DÍA A DÍA
# ══════════════════════════════════════════
with tab1:
    solo_fallos_tab1 = st.checkbox("Mostrar solo riders con fallos", value=True, key="sf1")
    filtro_min = st.slider("Mínimo de fallos en algún día", 0, 5, 1)

    # Ordenar riders por total de fallos en la semana
    riders_orden = (
        df_filtered.groupby("rider_id")["n_fallos"].sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    for rid in riders_orden:
        df_rider = df_filtered[df_filtered["rider_id"] == rid].sort_values("day")
        total_fallos_semana = df_rider["n_fallos"].sum()
        max_fallos_dia = df_rider["n_fallos"].max()

        if solo_fallos_tab1 and total_fallos_semana == 0:
            continue
        if max_fallos_dia < filtro_min:
            continue

        nombre    = df_rider["Nombre"].iloc[0] if pd.notna(df_rider["Nombre"].iloc[0]) else f"Rider {rid}"
        tier      = df_rider["Tier"].iloc[0] if "Tier" in df_rider.columns else "—"
        score     = df_rider["Score"].iloc[0] if "Score" in df_rider.columns else "—"
        contrato  = df_rider["Contrato"].iloc[0] if "Contrato" in df_rider.columns else "—"
        vehiculo  = df_rider["Vehículo"].iloc[0] if "Vehículo" in df_rider.columns else "—"

        clase = color_card(max_fallos_dia)

        dias_html = ""
        for _, dia in df_rider.iterrows():
            try:
                dt = datetime.strptime(dia["day"], "%Y-%m-%d")
                dia_label = f"{DIAS_ES.get(dt.strftime('%A'), '')} {dt.strftime('%d/%m')}"
            except:
                dia_label = dia["day"]

            fallos_dia = dia["fallos"]
            n_dia = len(fallos_dia)

            metricas_dia = "".join([
                metric_html("UTR", f"{dia['utr']:.2f}", "UTR" in fallos_dia),
                metric_html("CDT", f"{dia['cdt']:.1f}m", "CDT" in fallos_dia),
                metric_html("Pedidos", f"{int(dia['completados'])}/{int(dia['esperados'])}", "Pedidos" in fallos_dia),
                metric_html("% RR", f"{dia['pct_rr']:.1f}%", "Reasignacion" in fallos_dia),
                metric_html("% Cancel", f"{dia['pct_cancel']:.1f}%", "Cancelacion" in fallos_dia),
                metric_html("Horas", f"{dia['horas']:.1f}h", False),
            ])

            badges_dia = "".join([
                f'<span class="fallo-badge">{UMBRALES[f]["label"]}</span>'
                for f in fallos_dia
            ]) if fallos_dia else '<span style="color:#34d399;font-size:0.73rem">✅ OK</span>'

            color_dia = "#ef444420" if n_dia >= 3 else "#f59e0b15" if n_dia == 2 else "#3b82f615" if n_dia == 1 else "transparent"

            dias_html += f"""
            <div class="day-row" style="border-left: 3px solid {'#ef4444' if n_dia >= 3 else '#f59e0b' if n_dia == 2 else '#3b82f6' if n_dia == 1 else '#34d399'}; background:{color_dia}">
                <div class="day-label">{dia_label}</div>
                <div class="metric-row">{metricas_dia}</div>
                <div>{badges_dia}</div>
            </div>
            """

        st.markdown(f"""
        <div class="rider-card {clase}">
            <div class="rider-nombre">{nombre}</div>
            <div class="rider-meta">ID: {rid} &nbsp;·&nbsp; {tier} &nbsp;·&nbsp; Score: {score} &nbsp;·&nbsp; {contrato}h &nbsp;·&nbsp; {vehiculo} &nbsp;·&nbsp; <b>{total_fallos_semana} fallos en la semana</b></div>
            {dias_html}
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 2 — MENSAJES
# ══════════════════════════════════════════
with tab2:
    canal = st.radio("Canal", ["WhatsApp", "Email"], horizontal=True)
    canal_key = "ws" if canal == "WhatsApp" else "email"
    tipo_msg = st.radio("Tipo de mensaje", ["Resumen semanal", "Detalle por día"], horizontal=True)
    solo_fallos_tab2 = st.checkbox("Solo riders con fallos", value=True, key="sf2")

    for rid in riders_orden:
        df_rider = df_filtered[df_filtered["rider_id"] == rid].sort_values("day")
        total_fallos = df_rider["n_fallos"].sum()

        if solo_fallos_tab2 and total_fallos == 0:
            continue

        nombre   = df_rider["Nombre"].iloc[0] if pd.notna(df_rider["Nombre"].iloc[0]) else f"Rider {rid}"
        tier     = df_rider["Tier"].iloc[0] if "Tier" in df_rider.columns else "—"
        n_max    = df_rider["n_fallos"].max()

        if tipo_msg == "Detalle por día":
            dias_con_fallos = []
            for _, dia in df_rider.iterrows():
                if dia["fallos"]:
                    dias_con_fallos.append({
                        "fecha": dia["day"],
                        "fallos": dia["fallos"],
                        "detalle_fallos": dia["detalle_fallos"],
                    })
            if not dias_con_fallos:
                continue
            mensaje = generar_mensaje_diario(nombre, dias_con_fallos, canal_key)
        else:
            # Resumen semanal: fallos más frecuentes con sus peores valores
            fallos_semana = {}
            for _, dia in df_rider.iterrows():
                for fallo in dia["fallos"]:
                    det = dia["detalle_fallos"].get(fallo, {})
                    if fallo not in fallos_semana:
                        fallos_semana[fallo] = det
            if not fallos_semana:
                continue
            mensaje = generar_mensaje_semanal(nombre, fallos_semana, canal_key)

        icono = "🔴" if n_max >= 3 else "🟡" if n_max == 2 else "🔵"
        with st.expander(f"{icono} {nombre} — {tier} — {total_fallos} fallos en la semana"):
            st.markdown(f'<div class="msg-box">{mensaje}</div>', unsafe_allow_html=True)
            st.code(mensaje, language=None)

# ══════════════════════════════════════════
# TAB 3 — EXPORTAR
# ══════════════════════════════════════════
with tab3:
    st.markdown("### Exportar informe completo")

    rows = []
    for rid in riders_orden:
        df_rider = df_filtered[df_filtered["rider_id"] == rid].sort_values("day")
        nombre = df_rider["Nombre"].iloc[0] if pd.notna(df_rider["Nombre"].iloc[0]) else f"Rider {rid}"
        tier   = df_rider["Tier"].iloc[0] if "Tier" in df_rider.columns else "—"
        score  = df_rider["Score"].iloc[0] if "Score" in df_rider.columns else "—"

        for _, dia in df_rider.iterrows():
            rows.append({
                "Rider ID":      rid,
                "Nombre":        nombre,
                "Tier":          tier,
                "Score":         score,
                "Fecha":         dia["day"],
                "Horas":         round(dia["horas"], 2),
                "UTR":           round(dia["utr"], 3),
                "CDT (min)":     round(dia["cdt"], 1),
                "Completados":   int(dia["completados"]),
                "Esperados":     int(dia["esperados"]),
                "% Reasignación":round(dia["pct_rr"], 2),
                "% Cancelación": round(dia["pct_cancel"], 2),
                "Nº fallos":     dia["n_fallos"],
                "Fallos":        " | ".join([UMBRALES[f]["label"] for f in dia["fallos"]]) if dia["fallos"] else "Sin fallos",
            })

    df_export = pd.DataFrame(rows)
    st.dataframe(df_export, use_container_width=True, hide_index=True)

    excel_data = to_excel(df_export)
    st.download_button(
        label="⬇️ Descargar Excel",
        data=excel_data,
        file_name="informe_riders_diario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )