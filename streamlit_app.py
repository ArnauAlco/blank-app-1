import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import networkx as nx
from PIL import Image

st.set_page_config(page_title="Análisis ABP Fútbol", layout="wide")

@st.cache_data
def cargar_datos():
    archivo = "Prova ABP.xlsx"
    df = pd.read_excel(archivo)
    return df

# ==== FUNCIÓN PARA MOSTRAR PUNTOS SOBRE EL CAMPO DE FÚTBOL CON TU IMAGEN ====
def plot_campo_con_fondo(df, x_col, y_col, color_col=None, title="Zonas de ejecución sobre campo", campo_img_path="Campo xG.png"):
    img = Image.open(campo_img_path)
    fig = go.Figure()

    # Añade imagen como fondo, correctamente alineada y con proporción 2.25 (180/80)
    fig.add_layout_image(
        dict(
            source=img,
            xref="x",
            yref="y",
            x=0,           # esquina izq
            y=80,          # esquina sup
            sizex=120,     # campo completo horizontal
            sizey=80,      # campo completo vertical
            sizing="stretch",
            layer="below"
        )
    )
    # Añade puntos
    if color_col and color_col in df.columns:
        for tipo in df[color_col].dropna().unique():
            dft = df[df[color_col] == tipo]
            fig.add_trace(go.Scatter(
                x=dft[x_col], y=dft[y_col],
                mode="markers",
                name=str(tipo),
                marker=dict(size=10),
                hoverinfo="text",
                text=dft[color_col]
            ))
    else:
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[y_col],
            mode="markers",
            marker=dict(size=10, color='red'),
            name="Ejecuciones"
        ))
    fig.update_xaxes(range=[-5, 125], constrain="domain")
    fig.update_yaxes(range=[-5, 85], scaleanchor="x", scaleratio=1, constrain="domain")

    # OCULTA líneas, ticks y números:
    fig.update_xaxes(showgrid=False, showticklabels=False, visible=False)
    fig.update_yaxes(showgrid=False, showticklabels=False, visible=False)    
    fig.update_layout(
        title=title,
        width=900,
        height=int(900 / 2.25),
        showlegend=True,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig


# ---- RECARGA MANUAL ----
if st.sidebar.button("Recargar datos"):
    st.cache_data.clear()
    st.info("¡Cache borrada! Cambia cualquier filtro, o pulsa el botón de 'Rerun' arriba a la derecha, para recargar el Excel.")

df = cargar_datos()

# ---- PREPARA VALORES ÚNICOS PARA FILTROS ----
df['Jornada'] = pd.to_numeric(df['Jornada'], errors='coerce')
temporadas = df['Temporada'].dropna().unique()
tipos_abp = df['ABP_Tipo'].dropna().unique()
ejecucion_tipos = df['Ejecucion_Tipo'].dropna().unique() if 'Ejecucion_Tipo' in df.columns else []
jugadores = df['Jugador_Ejecutor'].dropna().unique()
jugadores_objetivo = df['Jugador_Objetivo'].dropna().unique() if 'Jugador_Objetivo' in df.columns else []
porteros_defensores = df['Portero_Defensor'].dropna().unique() if 'Portero_Defensor' in df.columns else []
equipos_atacantes = df['Equipo_Atacante'].dropna().unique()
equipos_defensores = df['Equipo_Defensor'].dropna().unique()
tipo_tiro = df['Tiro'].dropna().unique()
tipo_gol = df['Gol'].dropna().unique()
jornada_min = int(df['Jornada'].min())
jornada_max = int(df['Jornada'].max())
fases_atacante = df['Momento_Resultado_Atacante'].dropna().unique() if 'Momento_Resultado_Atacante' in df.columns else []
fases_defensor = df['Momento_Resultado_Defensor'].dropna().unique() if 'Momento_Resultado_Defensor' in df.columns else []
mitades_disponibles = df['Momento_Mitad'].dropna().unique() if 'Momento_Mitad' in df.columns else []
situaciones_numericas_atac = df['Situacion_Numerica_Atacante'].dropna().unique() if 'Situacion_Numerica_Atacante' in df.columns else []
situaciones_numericas_def = df['Situacion_Numerica_Defensor'].dropna().unique() if 'Situacion_Numerica_Defensor' in df.columns else []
porteros_ataca = df['Portero_Ataca'].dropna().unique() if 'Portero_Ataca' in df.columns else []


# ---- SIDEBAR DE NAVEGACIÓN ----
st.sidebar.title("Navegación")
pagina = st.sidebar.radio(
    "Selecciona la página:",
    (
        "Dashboard general",
        "Análisis equipos atacantes",
        "Análisis equipos defensores",
        "Comparativa entre equipos",
        "Ranking defensivo",
        "Comparativa entre temporadas",
        "Mapa de conexiones (red ABP)"
    )
)

# ---- FILTROS GENERALES ----
st.sidebar.header("Filtros generales")

if st.sidebar.button("🔄 Resetear todos los filtros"):
    for key in list(st.session_state.keys()):
        if key not in ("_uploaded_file_mgr_state",):  # Evita borrar cosas de streamlit interno
            del st.session_state[key]
    st.rerun()


jornada_sel = st.sidebar.slider(
    "Jornada (rango)",
    min_value=jornada_min,
    max_value=jornada_max,
    value=(jornada_min, jornada_max),
    step=1,
    key="jornada_sel"
)
temporada_sel = st.sidebar.multiselect("Temporada", temporadas, default=list(temporadas), key="temporada_sel")
tipo_abp_sel = st.sidebar.multiselect("Tipo ABP", tipos_abp, default=list(tipos_abp), key="tipo_abp_sel")
if len(ejecucion_tipos) > 0:
    ejecucion_tipo_sel = st.sidebar.multiselect(
        "Tipo de ejecución",
        ejecucion_tipos,
        default=list(ejecucion_tipos),
        key="ejecucion_tipo_sel"
    )
else:
    ejecucion_tipo_sel = None

# ---- FILTRO DE MITAD DEL PARTIDO ----
if len(mitades_disponibles) > 0:
    mitad_sel = st.sidebar.multiselect(
        "Mitad del partido",
        mitades_disponibles,
        default=list(mitades_disponibles),
        key="mitad_sel"
    )
else:
    mitad_sel = []

# ---- TIMELINE DE MOMENTO DEL PARTIDO (DEPENDIENTE DE MITAD) ----
franjas_primera = ["0-15", "16-30", "31-45", "EXTRA 1"]
franjas_segunda = ["45-60", "61-75", "76-90", "EXTRA 2"]
opciones_timeline = franjas_primera + franjas_segunda

if 'Momento_Rango' in df.columns:
    franjas_data = list(df['Momento_Rango'].dropna().unique())
    if mitad_sel == ["Primera"]:
        franjas_disponibles = [o for o in franjas_primera if o in franjas_data]
    elif mitad_sel == ["Segunda"]:
        franjas_disponibles = [o for o in franjas_segunda if o in franjas_data]
    elif sorted(mitad_sel) == sorted(list(mitades_disponibles)):
        franjas_disponibles = [o for o in opciones_timeline if o in franjas_data]
    else:
        franjas_disponibles = [o for o in opciones_timeline if o in franjas_data]
else:
    franjas_disponibles = []

franja_sel = st.sidebar.multiselect(
    "Franja(s) de tiempo",
    franjas_disponibles,
    default=franjas_disponibles,
    key="franja_sel"
)

equipo_atacante_sel = st.sidebar.multiselect("Equipo Atacante", equipos_atacantes, default=list(equipos_atacantes), key="equipo_atacante_sel")
equipo_defensor_sel = st.sidebar.multiselect("Equipo Defensor", equipos_defensores, default=list(equipos_defensores), key="equipo_defensor_sel")
jugador_sel = st.sidebar.multiselect("Jugador ejecutor", jugadores, default=list(jugadores), key="jugador_sel")

if len(jugadores_objetivo) > 0:
    jugador_objetivo_sel = st.sidebar.multiselect(
        "Jugador objetivo",
        jugadores_objetivo,
        default=list(jugadores_objetivo),
        key="jugador_objetivo_sel"
    )
else:
    jugador_objetivo_sel = None

if len(porteros_defensores) > 0:
    portero_defensor_sel = st.sidebar.multiselect(
        "Portero defensor",
        porteros_defensores,
        default=list(porteros_defensores),
        key="portero_defensor_sel"
    )
else:
    portero_defensor_sel = None

if len(porteros_ataca) > 0:
    portero_ataca_sel = st.sidebar.multiselect(
        "Portero ataca",
        porteros_ataca,
        default=list(porteros_ataca),
        key="portero_ataca_sel"
    )
else:
    portero_ataca_sel = None

tipo_tiro_sel = st.sidebar.multiselect("¿Acaba en tiro?", tipo_tiro, default=list(tipo_tiro), key="tipo_tiro_sel")
tipo_gol_sel = st.sidebar.multiselect("¿Acaba en gol?", tipo_gol, default=list(tipo_gol), key="tipo_gol_sel")

if len(fases_atacante) > 0:
    fase_sel = st.sidebar.multiselect("Resultado atacante", fases_atacante, default=list(fases_atacante), key="fase_atacante_sel")
else:
    fase_sel = None

if len(fases_defensor) > 0:
    fase_sel = st.sidebar.multiselect("Resultado defensor", fases_defensor, default=list(fases_defensor), key="fase_defensor_sel")
else:
    fase_sel = None

if len(situaciones_numericas_atac) > 0:
    situacion_numerica_atac_sel = st.sidebar.multiselect(
        "Situación numérica atacante",
        situaciones_numericas_atac,
        default=list(situaciones_numericas_atac),
        key="situacion_numerica_atac_sel"
    )
else:
    situacion_numerica_atac_sel = None

if len(situaciones_numericas_def) > 0:
    situacion_numerica_def_sel = st.sidebar.multiselect(
        "Situación numérica defensor",
        situaciones_numericas_def,
        default=list(situaciones_numericas_def),
        key="situacion_numerica_def_sel"
    )
else:
    situacion_numerica_def_sel = None



# ---- FUNCIONES DE FILTRADO ----
def aplicar_filtros(df):
    condiciones = (
        df['Temporada'].isin(temporada_sel) &
        df['ABP_Tipo'].isin(tipo_abp_sel) &
        df['Jornada'].between(jornada_sel[0], jornada_sel[1]) &
        df['Jugador_Ejecutor'].isin(jugador_sel) &
        df['Tiro'].isin(tipo_tiro_sel) &
        df['Gol'].isin(tipo_gol_sel) &
        df['Equipo_Atacante'].isin(equipo_atacante_sel) &
        df['Equipo_Defensor'].isin(equipo_defensor_sel)
    )
    if fase_sel is not None and 'Momento_Resultado_Atacante' in df.columns:
        condiciones = condiciones & df['Momento_Resultado_Atacante'].isin(fase_sel)
    if mitad_sel and 'Momento_Mitad' in df.columns:
        condiciones = condiciones & df['Momento_Mitad'].isin(mitad_sel)
    if franja_sel and 'Momento_Rango' in df.columns:
        condiciones = condiciones & df['Momento_Rango'].isin(franja_sel)
    if portero_defensor_sel is not None and 'Portero_Defensor' in df.columns:
        condiciones = condiciones & df['Portero_Defensor'].isin(portero_defensor_sel)
    if situacion_numerica_atac_sel is not None and 'Situacion_Numerica_Atacante' in df.columns:
        condiciones = condiciones & df['Situacion_Numerica_Atacante'].isin(situacion_numerica_atac_sel)
    if situacion_numerica_def_sel is not None and 'Situacion_Numerica_Defensor' in df.columns:
        condiciones = condiciones & df['Situacion_Numerica_Defensor'].isin(situacion_numerica_def_sel)
    if portero_ataca_sel is not None and 'Portero_Ataca' in df.columns:
        condiciones = condiciones & df['Portero_Ataca'].isin(portero_ataca_sel)
    if jugador_objetivo_sel is not None and 'Jugador_Objetivo' in df.columns:
        condiciones = condiciones & df['Jugador_Objetivo'].isin(jugador_objetivo_sel)
    if ejecucion_tipo_sel is not None and 'Ejecucion_Tipo' in df.columns:
        condiciones = condiciones & df['Ejecucion_Tipo'].isin(ejecucion_tipo_sel)


    return df[condiciones]

# ========== PÁGINAS PRINCIPALES ==========

if pagina == "Dashboard general":
    st.title("Dashboard resumen ABP")
    df_pag = aplicar_filtros(df)
    st.dataframe(df_pag, use_container_width=True)

    # KPIs
    st.subheader("KPIs generales")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total ABP (todas las acciones)", len(df))
    k2.metric("Total ABP (según filtros)", len(df_pag))
    k3.metric("Equipos atacantes", df_pag['Equipo_Atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['Equipo_Defensor'].nunique())
    k5.metric("Tiros", df_pag['Tiro'].str.upper().eq("SI").sum())
    if 'GOL' in df_pag.columns:
        k6.metric("Goles", df_pag['GOL'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")
    
    # Gráficos principales
    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['ABP_Tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['ABP_Tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='ABP_Tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('Jornada').size().reset_index(name='Cantidad')
    fig2 = px.line(abp_jornada, x='Jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig2, use_container_width=True)
    
    # --- CAMPO DE FÚTBOL CON PUNTOS ---
    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'X_Ejecucion' in df_pag.columns and 'Y_Ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['X_Ejecucion', 'Y_Ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='X_Ejecucion', y_col='Y_Ejecucion',
                color_col='ABP_Tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores (nº ABP)")
    top_ejecutores = df_pag['Jugador_Ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['Jugador_Ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='Jugador_Ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    # xG acumulado por equipo atacante y jornada (mejorado)
    st.subheader("xG acumulado por jornada (equipos atacantes seleccionados)")
    if 'xG_Tiro' in df_pag.columns and not df_pag.empty:
        equipos_disponibles = equipo_atacante_sel
        jornadas_disponibles = sorted(df['Jornada'].dropna().unique())
        xg_ac = (
            df_pag.groupby(['Equipo_Atacante', 'Jornada'])['xG_Tiro']
            .sum().reset_index()
            .set_index(['Equipo_Atacante', 'Jornada'])
            .unstack(fill_value=0)
            .stack().reset_index()
        )
        # Asegura que todos los equipos y jornadas estén presentes (con 0 si no hay dato)
        full_idx = pd.MultiIndex.from_product([equipos_disponibles, jornadas_disponibles], names=['Equipo_Atacante', 'Jornada'])
        xg_ac = xg_ac.set_index(['Equipo_Atacante', 'Jornada']).reindex(full_idx, fill_value=0).reset_index()
        fig_xg = px.line(
            xg_ac, x='Jornada', y='xG_Tiro', color='Equipo_Atacante',
            title="xG acumulado por jornada (equipos atacantes seleccionados)"
        )
        st.plotly_chart(fig_xg, use_container_width=True)
    else:
        st.info("No hay columna 'xG_Tiro' en los datos.")

elif pagina == "Análisis equipos atacantes":
    st.title("Análisis de equipos atacantes (ABP)")
    df_pag = aplicar_filtros(df)

    st.dataframe(df_pag, use_container_width=True)

    # KPIs
    st.subheader("KPIs equipos atacantes")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total ABP (todas las acciones)", len(df))
    k2.metric("Total ABP (según filtros)", len(df_pag))
    k3.metric("Equipos atacantes", df_pag['Equipo_Atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['Equipo_Defensor'].nunique())
    k5.metric("Tiros", df_pag['Tiro'].str.upper().eq("SI").sum())
    if 'GOL' in df_pag.columns:
        k6.metric("Goles", df_pag['GOL'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")

    st.markdown("---")

    # Gráficos
    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['ABP_Tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['ABP_Tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='ABP_Tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("ABP por equipo atacante")
    ataque_count = df_pag['Equipo_Atacante'].value_counts().reset_index()
    ataque_count.columns = ['Equipo_Atacante', 'count']
    fig2 = px.bar(ataque_count, x='Equipo_Atacante', y='count', title="ABP por equipo atacante")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('Jornada').size().reset_index(name='Cantidad')
    fig3 = px.line(abp_jornada, x='Jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    # --- CAMPO DE FÚTBOL CON PUNTOS ---
    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'X_Ejecucion' in df_pag.columns and 'Y_Ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['X_Ejecucion', 'Y_Ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='X_Ejecucion', y_col='Y_Ejecucion',
                color_col='ABP_Tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores")
    top_ejecutores = df_pag['Jugador_Ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['Jugador_Ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='Jugador_Ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    # xG acumulado por equipo atacante y jornada (mejorado)
    st.subheader("xG acumulado por jornada (equipos atacantes seleccionados)")
    if 'xG_Tiro' in df_pag.columns and not df_pag.empty:
        equipos_disponibles = equipo_atacante_sel
        jornadas_disponibles = sorted(df['Jornada'].dropna().unique())
        xg_ac = (
            df_pag.groupby(['Equipo_Atacante', 'Jornada'])['xG_Tiro']
            .sum().reset_index()
            .set_index(['Equipo_Atacante', 'Jornada'])
            .unstack(fill_value=0)
            .stack().reset_index()
        )
        full_idx = pd.MultiIndex.from_product([equipos_disponibles, jornadas_disponibles], names=['Equipo_Atacante', 'Jornada'])
        xg_ac = xg_ac.set_index(['Equipo_Atacante', 'Jornada']).reindex(full_idx, fill_value=0).reset_index()
        fig_xg = px.line(
            xg_ac, x='Jornada', y='xG_Tiro', color='Equipo_Atacante',
            title="xG acumulado por jornada (equipos atacantes seleccionados)"
        )
        st.plotly_chart(fig_xg, use_container_width=True)
    else:
        st.info("No hay columna 'xG_Tiro' en los datos.")

    # Efectividad
    st.subheader("Efectividad: % de ABP que terminan en tiro")
    total_abp = len(df_pag)
    tiros = df_pag['Tiro'].str.upper().eq("SI").sum()
    porcentaje_tiro = (tiros / total_abp * 100) if total_abp > 0 else 0
    st.write(f"**{porcentaje_tiro:.1f}%** de las ABP terminan en tiro.")

    st.subheader("xG medio por tipo de ABP")
    if 'xG_Tiro' in df_pag.columns:
        xg_media = df_pag.groupby('ABP_Tipo')['xG_Tiro'].mean().reset_index()
        fig4 = px.bar(
            xg_media, x='ABP_Tipo', y='xG_Tiro',
            labels={'ABP_Tipo': 'Tipo ABP', 'xG_Tiro': 'xG medio'},
            title="xG medio por tipo de ABP"
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay columna 'xG_Tiro' en los datos.")

elif pagina == "Análisis equipos defensores":
    st.title("Análisis de equipos defensores (ABP)")
    df_pag = aplicar_filtros(df)

    st.dataframe(df_pag, use_container_width=True)

    # KPIs
    st.subheader("KPIs equipos defensores")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total ABP (todas las acciones)", len(df))
    k2.metric("Total ABP (según filtros)", len(df_pag))
    k3.metric("Equipos atacantes", df_pag['Equipo_Atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['Equipo_Defensor'].nunique())
    k5.metric("Tiros", df_pag['Tiro'].str.upper().eq("SI").sum())
    if 'GOL' in df_pag.columns:
        k6.metric("Goles", df_pag['GOL'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")

    st.markdown("---")

    # Gráficos
    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['ABP_Tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['ABP_Tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='ABP_Tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("ABP por equipo defensor")
    defensa_count = df_pag['Equipo_Defensor'].value_counts().reset_index()
    defensa_count.columns = ['Equipo_Defensor', 'count']
    fig2 = px.bar(defensa_count, x='Equipo_Defensor', y='count', title="ABP por equipo defensor")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('Jornada').size().reset_index(name='Cantidad')
    fig3 = px.line(abp_jornada, x='Jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    # --- CAMPO DE FÚTBOL CON PUNTOS ---
    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'X_Ejecucion' in df_pag.columns and 'Y_Ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['X_Ejecucion', 'Y_Ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='X_Ejecucion', y_col='Y_Ejecucion',
                color_col='ABP_Tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores")
    top_ejecutores = df_pag['Jugador_Ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['Jugador_Ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='Jugador_Ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    # xG acumulado por equipo atacante y jornada (NO se debe poner por equipo defensor)
    st.info("El xG acumulado siempre es por equipo atacante. Para comparar xG, usa el análisis atacante.")

    # Efectividad
    st.subheader("Efectividad defensiva: % de ABP que reciben tiro")
    total_abp = len(df_pag)
    tiros = df_pag['Tiro'].str.upper().eq("SI").sum()
    porcentaje_tiro = (tiros / total_abp * 100) if total_abp > 0 else 0
    st.write(f"**{porcentaje_tiro:.1f}%** de las ABP reciben tiro.")

    st.subheader("xG medio por tipo de ABP")
    if 'xG_Tiro' in df_pag.columns:
        xg_media = df_pag.groupby('ABP_Tipo')['xG_Tiro'].mean().reset_index()
        fig4 = px.bar(
            xg_media, x='ABP_Tipo', y='xG_Tiro',
            labels={'ABP_Tipo': 'Tipo ABP', 'xG_Tiro': 'xG medio'},
            title="xG medio por tipo de ABP"
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay columna 'xG_Tiro' en los datos.")

elif pagina == "Comparativa entre equipos":
    st.title("Comparativa entre dos equipos")
    equipo1 = st.selectbox("Selecciona equipo 1", equipos_atacantes)
    equipo2 = st.selectbox("Selecciona equipo 2", equipos_atacantes, index=1 if len(equipos_atacantes) > 1 else 0)
    df1 = aplicar_filtros(df[df['Equipo_Atacante'] == equipo1])
    df2 = aplicar_filtros(df[df['Equipo_Atacante'] == equipo2])
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"ABP {equipo1}", len(df1))
        st.metric(f"Tiros {equipo1}", df1['Tiro'].str.upper().eq("SI").sum())
        if 'GOL' in df1.columns:
            st.metric(f"Goles {equipo1}", df1['GOL'].str.upper().eq("SI").sum())
    with col2:
        st.metric(f"ABP {equipo2}", len(df2))
        st.metric(f"Tiros {equipo2}", df2['Tiro'].str.upper().eq("SI").sum())
        if 'GOL' in df2.columns:
            st.metric(f"Goles {equipo2}", df2['GOL'].str.upper().eq("SI").sum())
    # Comparativa de gráficos
    st.subheader("Comparativa por jornada (línea)")
    if not df1.empty and not df2.empty:
        abp1 = df1.groupby('Jornada').size().reset_index(name=equipo1)
        abp2 = df2.groupby('Jornada').size().reset_index(name=equipo2)
        df_comp = pd.merge(abp1, abp2, on='Jornada', how='outer').fillna(0)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=df_comp['Jornada'], y=df_comp[equipo1], name=equipo1))
        fig_comp.add_trace(go.Scatter(x=df_comp['Jornada'], y=df_comp[equipo2], name=equipo2))
        fig_comp.update_layout(title="ABP por jornada")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("No hay suficientes datos para la comparativa.")
    
elif pagina == "Ranking defensivo":
    st.title("Ranking defensivo (menos tiros/goles recibidos por ABP)")
    df_def = aplicar_filtros(df)
    aggs = {
        'ABP': ('Equipo_Defensor', 'size'),
        'Tiros_Recibidos': ('Tiro', lambda x: (x.str.upper() == "SI").sum())
    }
    if 'GOL' in df_def.columns:
        aggs['Goles_Recibidos'] = ('GOL', lambda x: (x.str.upper() == "SI").sum())

    ranking = df_def.groupby('Equipo_Defensor').agg(**aggs).reset_index()
    ranking['Tiros/ABP'] = ranking['Tiros_Recibidos'] / ranking['ABP']
    if 'Goles_Recibidos' in ranking.columns:
        ranking['Goles/ABP'] = ranking['Goles_Recibidos'] / ranking['ABP']

    st.dataframe(ranking.sort_values('Tiros/ABP'), use_container_width=True)
    fig_rank = px.bar(
        ranking.sort_values('Tiros/ABP').head(10), 
        x='Tiros/ABP', y='Equipo_Defensor', orientation='h', 
        title="Top defensas (menos tiros por ABP)"
    )
    st.plotly_chart(fig_rank, use_container_width=True)

elif pagina == "Comparativa entre temporadas":
    st.title("Comparativa entre temporadas")
    df_temp = aplicar_filtros(df)
    if not df_temp.empty:
        abp_temp = df_temp.groupby(['Temporada', 'Jornada']).size().reset_index(name='Cantidad')
        fig_temp = px.line(abp_temp, x='Jornada', y='Cantidad', color='Temporada', markers=True, title="ABP por jornada y temporada")
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("No hay datos para mostrar comparativa entre temporadas.")

elif pagina == "Mapa de conexiones (red ABP)":
    st.title("Red de conexiones en ABP")
    # Usando la columna 'Jugador_Objetivo' como receptor
    if 'Jugador_Objetivo' in df.columns:
        G = nx.DiGraph()
        for _, row in aplicar_filtros(df).dropna(subset=['Jugador_Ejecutor', 'Jugador_Objetivo']).iterrows():
            G.add_edge(row['Jugador_Ejecutor'], row['Jugador_Objetivo'])
        pos = nx.spring_layout(G, k=0.5)
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        node_x = []
        node_y = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=[str(n) for n in G.nodes()],
            textposition="bottom center",
            marker=dict(size=12, color='skyblue'),
            hoverinfo='text')
        fig_net = go.Figure(data=[edge_trace, node_trace])
        fig_net.update_layout(showlegend=False, title='Red de ejecutores y objetivos en ABP')
        st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.info("No hay columna 'Jugador_Objetivo' para crear la red de conexiones.")

# ---- EXPORTAR DATOS ----
st.sidebar.markdown("---")
csv = aplicar_filtros(df).to_csv(index=False).encode('utf-8')
def to_excel(df_filtrado):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name='ABP_filtrado')
    return output.getvalue()
excel_bytes = to_excel(aplicar_filtros(df))

st.sidebar.download_button(
    label="Descargar datos filtrados (CSV)",
    data=csv,
    file_name="abp_filtrado.csv",
    mime='text/csv'
)
st.sidebar.download_button(
    label="Descargar datos filtrados (Excel)",
    data=excel_bytes,
    file_name="abp_filtrado.xlsx",
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)