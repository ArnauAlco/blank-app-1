import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import networkx as nx
from PIL import Image

st.set_page_config(page_title="Análisis ABP Fútbol", layout="wide")

# ---- FUNCION PARA MULTISELECT CON "SELECCIONAR TODO" ----
def multiselect_con_todo(label, opciones, key):
    check = st.sidebar.checkbox(f"Seleccionar todo {label.lower()}", value=True, key=f"{key}_todo")
    if check:
        return st.sidebar.multiselect(label, opciones, default=opciones, key=key)
    else:
        return st.sidebar.multiselect(label, opciones, key=key)

# ---- CARGA DE DATOS ----
st.sidebar.header("Carga de datos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel ABP", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
else:
    @st.cache_data
    def cargar_datos():
        archivo = "Prova ABP.xlsx"
        try:
            df = pd.read_excel(archivo)
        except FileNotFoundError:
            st.error(f"No se encuentra el archivo `{archivo}`. Sube un archivo usando el botón de arriba.")
            st.stop()
        return df
    df = cargar_datos()

# ---- NORMALIZA NOMBRES DE COLUMNAS ----
df.columns = [col.lower() for col in df.columns]

# ---- EXTRAE VALORES ÚNICOS ORDENADOS ----
def col_ok(col, dft=None):
    dft = dft if dft is not None else df
    return sorted(dft[col].dropna().unique()) if col in dft.columns else []

df['jornada'] = pd.to_numeric(df['jornada'], errors='coerce')
temporadas = col_ok('temporada')
tipos_abp = col_ok('abp_tipo')
ejecucion_tipos = col_ok('ejecucion_tipo')
jugadores = col_ok('jugador_ejecutor')
jugadores_objetivo = col_ok('jugador_objetivo')
porteros_defensores = col_ok('portero_defensor')
equipos_atacantes = col_ok('equipo_atacante')
equipos_defensores = col_ok('equipo_defensor')
tipo_tiro = col_ok('tiro')
tipo_gol = col_ok('gol')
jornada_min = int(df['jornada'].min())
jornada_max = int(df['jornada'].max())
fases_atacante = col_ok('momento_resultado_atacante')
fases_defensor = col_ok('momento_resultado_defensor')
mitades_disponibles = col_ok('momento_mitad')
situaciones_numericas_atac = col_ok('situacion_numerica_atacante')
situaciones_numericas_def = col_ok('situacion_numerica_defensor')
porteros_ataca = col_ok('portero_ataca')

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

temporada_sel = multiselect_con_todo("Temporada", temporadas, "temporada_sel")
tipo_abp_sel = multiselect_con_todo("Tipo ABP", tipos_abp, "tipo_abp_sel")
ejecucion_tipo_sel = multiselect_con_todo("Tipo de ejecución", ejecucion_tipos, "ejecucion_tipo_sel") if ejecucion_tipos else []
mitad_sel = multiselect_con_todo("Mitad del partido", mitades_disponibles, "mitad_sel") if mitades_disponibles else []
equipo_atacante_sel = multiselect_con_todo("Equipo Atacante", equipos_atacantes, "equipo_atacante_sel")
equipo_defensor_sel = multiselect_con_todo("Equipo Defensor", equipos_defensores, "equipo_defensor_sel")
jugador_sel = multiselect_con_todo("Jugador ejecutor", jugadores, "jugador_sel")
jugador_objetivo_sel = multiselect_con_todo("Jugador objetivo", jugadores_objetivo, "jugador_objetivo_sel") if jugadores_objetivo else []
portero_defensor_sel = multiselect_con_todo("Portero defensor", porteros_defensores, "portero_defensor_sel") if porteros_defensores else []
portero_ataca_sel = multiselect_con_todo("Portero ataca", porteros_ataca, "portero_ataca_sel") if porteros_ataca else []
tipo_tiro_sel = multiselect_con_todo("¿Acaba en tiro?", tipo_tiro, "tipo_tiro_sel")
tipo_gol_sel = multiselect_con_todo("¿Acaba en gol?", tipo_gol, "tipo_gol_sel")
fase_atacante_sel = multiselect_con_todo("Resultado atacante", fases_atacante, "fase_atacante_sel") if fases_atacante else []
fase_defensor_sel = multiselect_con_todo("Resultado defensor", fases_defensor, "fase_defensor_sel") if fases_defensor else []
situacion_numerica_atac_sel = multiselect_con_todo("Situación numérica atacante", situaciones_numericas_atac, "situacion_numerica_atac_sel") if situaciones_numericas_atac else []
situacion_numerica_def_sel = multiselect_con_todo("Situación numérica defensor", situaciones_numericas_def, "situacion_numerica_def_sel") if situaciones_numericas_def else []

# ---- TIMELINE DE MOMENTO DEL PARTIDO (DEPENDIENTE DE MITAD) ----
franjas_primera = ["0-15", "16-30", "31-45", "EXTRA 1"]
franjas_segunda = ["45-60", "61-75", "76-90", "EXTRA 2"]
opciones_timeline = franjas_primera + franjas_segunda

if 'momento_rango' in df.columns:
    franjas_data = list(df['momento_rango'].dropna().unique())
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

franja_sel = multiselect_con_todo("Franja(s) de tiempo", franjas_disponibles, "franja_sel") if franjas_disponibles else []

# ---- FUNCION DE FILTRADO ----
def aplicar_filtros(df):
    condiciones = (
        df['temporada'].isin(temporada_sel) &
        df['abp_tipo'].isin(tipo_abp_sel) &
        df['jornada'].between(jornada_sel[0], jornada_sel[1]) &
        df['jugador_ejecutor'].isin(jugador_sel) &
        df['tiro'].isin(tipo_tiro_sel) &
        df['gol'].isin(tipo_gol_sel) &
        df['equipo_atacante'].isin(equipo_atacante_sel) &
        df['equipo_defensor'].isin(equipo_defensor_sel)
    )
    if fase_atacante_sel and 'momento_resultado_atacante' in df.columns:
        condiciones = condiciones & df['momento_resultado_atacante'].isin(fase_atacante_sel)
    if mitad_sel and 'momento_mitad' in df.columns:
        condiciones = condiciones & df['momento_mitad'].isin(mitad_sel)
    if franja_sel and 'momento_rango' in df.columns:
        condiciones = condiciones & df['momento_rango'].isin(franja_sel)
    if portero_defensor_sel and 'portero_defensor' in df.columns:
        condiciones = condiciones & df['portero_defensor'].isin(portero_defensor_sel)
    if situacion_numerica_atac_sel and 'situacion_numerica_atacante' in df.columns:
        condiciones = condiciones & df['situacion_numerica_atacante'].isin(situacion_numerica_atac_sel)
    if situacion_numerica_def_sel and 'situacion_numerica_defensor' in df.columns:
        condiciones = condiciones & df['situacion_numerica_defensor'].isin(situacion_numerica_def_sel)
    if portero_ataca_sel and 'portero_ataca' in df.columns:
        condiciones = condiciones & df['portero_ataca'].isin(portero_ataca_sel)
    if jugador_objetivo_sel and 'jugador_objetivo' in df.columns:
        condiciones = condiciones & df['jugador_objetivo'].isin(jugador_objetivo_sel)
    if ejecucion_tipo_sel and 'ejecucion_tipo' in df.columns:
        condiciones = condiciones & df['ejecucion_tipo'].isin(ejecucion_tipo_sel)
    if fase_defensor_sel and 'momento_resultado_defensor' in df.columns:
        condiciones = condiciones & df['momento_resultado_defensor'].isin(fase_defensor_sel)
    return df[condiciones]

# ---- FUNCION CAMPO CON FONDO ----
def plot_campo_con_fondo(df, x_col, y_col, color_col=None, title="Zonas de ejecución sobre campo", campo_img_path="Campo xG.png"):
    img = Image.open(campo_img_path)
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=img,
            xref="x",
            yref="y",
            x=0,
            y=80,
            sizex=120,
            sizey=80,
            sizing="stretch",
            layer="below"
        )
    )
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
    fig.update_xaxes(range=[-5, 125], constrain="domain", showgrid=False, showticklabels=False, visible=False)
    fig.update_yaxes(range=[-5, 85], scaleanchor="x", scaleratio=1, constrain="domain", showgrid=False, showticklabels=False, visible=False)    
    fig.update_layout(
        title=title,
        width=900,
        height=int(900 / 2.25),
        showlegend=True,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

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
    k3.metric("Equipos atacantes", df_pag['equipo_atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['equipo_defensor'].nunique())
    k5.metric("Tiros", df_pag['tiro'].str.upper().eq("SI").sum())
    if 'gol' in df_pag.columns:
        k6.metric("Goles", df_pag['gol'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")
    
    # Gráficos principales
    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['abp_tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['abp_tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='abp_tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('jornada').size().reset_index(name='Cantidad')
    fig2 = px.line(abp_jornada, x='jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig2, use_container_width=True)
    
    # --- CAMPO DE FÚTBOL CON PUNTOS ---
    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'x_ejecucion' in df_pag.columns and 'y_ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['x_ejecucion', 'y_ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='x_ejecucion', y_col='y_ejecucion',
                color_col='abp_tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores (nº ABP)")
    top_ejecutores = df_pag['jugador_ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['jugador_ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='jugador_ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    st.subheader("xG acumulado por jornada (equipos atacantes seleccionados)")
    if 'xg_tiro' in df_pag.columns and not df_pag.empty:
        equipos_disponibles = equipo_atacante_sel
        jornadas_disponibles = sorted(df['jornada'].dropna().unique())
        xg_ac = (
            df_pag.groupby(['equipo_atacante', 'jornada'])['xg_tiro']
            .sum().reset_index()
            .set_index(['equipo_atacante', 'jornada'])
            .unstack(fill_value=0)
            .stack().reset_index()
        )
        full_idx = pd.MultiIndex.from_product([equipos_disponibles, jornadas_disponibles], names=['equipo_atacante', 'jornada'])
        xg_ac = xg_ac.set_index(['equipo_atacante', 'jornada']).reindex(full_idx, fill_value=0).reset_index()
        fig_xg = px.line(
            xg_ac, x='jornada', y='xg_tiro', color='equipo_atacante',
            title="xG acumulado por jornada (equipos atacantes seleccionados)"
        )
        st.plotly_chart(fig_xg, use_container_width=True)
    else:
        st.info("No hay columna 'xg_tiro' en los datos.")

elif pagina == "Análisis equipos atacantes":
    st.title("Análisis de equipos atacantes (ABP)")
    df_pag = aplicar_filtros(df)

    st.dataframe(df_pag, use_container_width=True)

    st.subheader("KPIs equipos atacantes")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total ABP (todas las acciones)", len(df))
    k2.metric("Total ABP (según filtros)", len(df_pag))
    k3.metric("Equipos atacantes", df_pag['equipo_atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['equipo_defensor'].nunique())
    k5.metric("Tiros", df_pag['tiro'].str.upper().eq("SI").sum())
    if 'gol' in df_pag.columns:
        k6.metric("Goles", df_pag['gol'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")

    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['abp_tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['abp_tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='abp_tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("ABP por equipo atacante")
    ataque_count = df_pag['equipo_atacante'].value_counts().reset_index()
    ataque_count.columns = ['equipo_atacante', 'count']
    fig2 = px.bar(ataque_count, x='equipo_atacante', y='count', title="ABP por equipo atacante")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('jornada').size().reset_index(name='Cantidad')
    fig3 = px.line(abp_jornada, x='jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'x_ejecucion' in df_pag.columns and 'y_ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['x_ejecucion', 'y_ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='x_ejecucion', y_col='y_ejecucion',
                color_col='abp_tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores")
    top_ejecutores = df_pag['jugador_ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['jugador_ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='jugador_ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    st.subheader("xG acumulado por jornada (equipos atacantes seleccionados)")
    if 'xg_tiro' in df_pag.columns and not df_pag.empty:
        equipos_disponibles = equipo_atacante_sel
        jornadas_disponibles = sorted(df['jornada'].dropna().unique())
        xg_ac = (
            df_pag.groupby(['equipo_atacante', 'jornada'])['xg_tiro']
            .sum().reset_index()
            .set_index(['equipo_atacante', 'jornada'])
            .unstack(fill_value=0)
            .stack().reset_index()
        )
        full_idx = pd.MultiIndex.from_product([equipos_disponibles, jornadas_disponibles], names=['equipo_atacante', 'jornada'])
        xg_ac = xg_ac.set_index(['equipo_atacante', 'jornada']).reindex(full_idx, fill_value=0).reset_index()
        fig_xg = px.line(
            xg_ac, x='jornada', y='xg_tiro', color='equipo_atacante',
            title="xG acumulado por jornada (equipos atacantes seleccionados)"
        )
        st.plotly_chart(fig_xg, use_container_width=True)
    else:
        st.info("No hay columna 'xg_tiro' en los datos.")

    st.subheader("Efectividad: % de ABP que terminan en tiro")
    total_abp = len(df_pag)
    tiros = df_pag['tiro'].str.upper().eq("SI").sum()
    porcentaje_tiro = (tiros / total_abp * 100) if total_abp > 0 else 0
    st.write(f"**{porcentaje_tiro:.1f}%** de las ABP terminan en tiro.")

    st.subheader("xG medio por tipo de ABP")
    if 'xg_tiro' in df_pag.columns:
        xg_media = df_pag.groupby('abp_tipo')['xg_tiro'].mean().reset_index()
        fig4 = px.bar(
            xg_media, x='abp_tipo', y='xg_tiro',
            labels={'abp_tipo': 'Tipo ABP', 'xg_tiro': 'xG medio'},
            title="xG medio por tipo de ABP"
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay columna 'xg_tiro' en los datos.")

elif pagina == "Análisis equipos defensores":
    st.title("Análisis de equipos defensores (ABP)")
    df_pag = aplicar_filtros(df)

    st.dataframe(df_pag, use_container_width=True)

    st.subheader("KPIs equipos defensores")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total ABP (todas las acciones)", len(df))
    k2.metric("Total ABP (según filtros)", len(df_pag))
    k3.metric("Equipos atacantes", df_pag['equipo_atacante'].nunique())
    k4.metric("Equipos defensores", df_pag['equipo_defensor'].nunique())
    k5.metric("Tiros", df_pag['tiro'].str.upper().eq("SI").sum())
    if 'gol' in df_pag.columns:
        k6.metric("Goles", df_pag['gol'].str.upper().eq("SI").sum())
    else:
        k6.metric("Goles", "—")
    st.markdown("---")

    st.subheader("Distribución de tipos de ABP")
    abp_tipo_count = df_pag['abp_tipo'].value_counts().reset_index()
    abp_tipo_count.columns = ['abp_tipo', 'count']
    fig1 = px.bar(abp_tipo_count, x='abp_tipo', y='count', title="ABP por tipo")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("ABP por equipo defensor")
    defensa_count = df_pag['equipo_defensor'].value_counts().reset_index()
    defensa_count.columns = ['equipo_defensor', 'count']
    fig2 = px.bar(defensa_count, x='equipo_defensor', y='count', title="ABP por equipo defensor")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Evolución de ABP por jornada")
    abp_jornada = df_pag.groupby('jornada').size().reset_index(name='Cantidad')
    fig3 = px.line(abp_jornada, x='jornada', y='Cantidad', markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Mapa de zonas de ejecución sobre el campo")
    if 'x_ejecucion' in df_pag.columns and 'y_ejecucion' in df_pag.columns:
        ejecs = df_pag.dropna(subset=['x_ejecucion', 'y_ejecucion'])
        if not ejecs.empty:
            fig_campo = plot_campo_con_fondo(
                ejecs, x_col='x_ejecucion', y_col='y_ejecucion',
                color_col='abp_tipo',
                title="Zonas de ejecución sobre campo de fútbol",
                campo_img_path="Campo xG.png"
            )
            st.plotly_chart(fig_campo, use_container_width=True)
        else:
            st.info("No hay datos de ejecuciones para mostrar en el campo.")
    else:
        st.info("No hay columnas de ejecuciones para el campo.")

    st.subheader("Top ejecutores")
    top_ejecutores = df_pag['jugador_ejecutor'].value_counts().reset_index().head(10)
    top_ejecutores.columns = ['jugador_ejecutor', 'count']
    fig_ej = px.bar(top_ejecutores, x='jugador_ejecutor', y='count')
    st.plotly_chart(fig_ej, use_container_width=True)

    st.info("El xG acumulado siempre es por equipo atacante. Para comparar xG, usa el análisis atacante.")

    st.subheader("Efectividad defensiva: % de ABP que reciben tiro")
    total_abp = len(df_pag)
    tiros = df_pag['tiro'].str.upper().eq("SI").sum()
    porcentaje_tiro = (tiros / total_abp * 100) if total_abp > 0 else 0
    st.write(f"**{porcentaje_tiro:.1f}%** de las ABP reciben tiro.")

    st.subheader("xG medio por tipo de ABP")
    if 'xg_tiro' in df_pag.columns:
        xg_media = df_pag.groupby('abp_tipo')['xg_tiro'].mean().reset_index()
        fig4 = px.bar(
            xg_media, x='abp_tipo', y='xg_tiro',
            labels={'abp_tipo': 'Tipo ABP', 'xg_tiro': 'xG medio'},
            title="xG medio por tipo de ABP"
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay columna 'xg_tiro' en los datos.")

elif pagina == "Comparativa entre equipos":
    st.title("Comparativa entre dos equipos")
    equipo1 = st.selectbox("Selecciona equipo 1", equipos_atacantes)
    equipo2 = st.selectbox("Selecciona equipo 2", equipos_atacantes, index=1 if len(equipos_atacantes) > 1 else 0)
    df1 = aplicar_filtros(df[df['equipo_atacante'] == equipo1])
    df2 = aplicar_filtros(df[df['equipo_atacante'] == equipo2])
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"ABP {equipo1}", len(df1))
        st.metric(f"Tiros {equipo1}", df1['tiro'].str.upper().eq("SI").sum())
        if 'gol' in df1.columns:
            st.metric(f"Goles {equipo1}", df1['gol'].str.upper().eq("SI").sum())
    with col2:
        st.metric(f"ABP {equipo2}", len(df2))
        st.metric(f"Tiros {equipo2}", df2['tiro'].str.upper().eq("SI").sum())
        if 'gol' in df2.columns:
            st.metric(f"Goles {equipo2}", df2['gol'].str.upper().eq("SI").sum())
    st.subheader("Comparativa por jornada (línea)")
    if not df1.empty and not df2.empty:
        abp1 = df1.groupby('jornada').size().reset_index(name=equipo1)
        abp2 = df2.groupby('jornada').size().reset_index(name=equipo2)
        df_comp = pd.merge(abp1, abp2, on='jornada', how='outer').fillna(0)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=df_comp['jornada'], y=df_comp[equipo1], name=equipo1))
        fig_comp.add_trace(go.Scatter(x=df_comp['jornada'], y=df_comp[equipo2], name=equipo2))
        fig_comp.update_layout(title="ABP por jornada")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("No hay suficientes datos para la comparativa.")

elif pagina == "Ranking defensivo":
    st.title("Ranking defensivo (menos tiros/goles recibidos por ABP)")
    df_def = aplicar_filtros(df)
    aggs = {
        'ABP': ('equipo_defensor', 'size'),
        'Tiros_Recibidos': ('tiro', lambda x: (x.str.upper() == "SI").sum())
    }
    if 'gol' in df_def.columns:
        aggs['Goles_Recibidos'] = ('gol', lambda x: (x.str.upper() == "SI").sum())

    ranking = df_def.groupby('equipo_defensor').agg(**aggs).reset_index()
    ranking['Tiros/ABP'] = ranking['Tiros_Recibidos'] / ranking['ABP']
    if 'Goles_Recibidos' in ranking.columns:
        ranking['Goles/ABP'] = ranking['Goles_Recibidos'] / ranking['ABP']

    st.dataframe(ranking.sort_values('Tiros/ABP'), use_container_width=True)
    fig_rank = px.bar(
        ranking.sort_values('Tiros/ABP').head(10), 
        x='Tiros/ABP', y='equipo_defensor', orientation='h', 
        title="Top defensas (menos tiros por ABP)"
    )
    st.plotly_chart(fig_rank, use_container_width=True)

elif pagina == "Comparativa entre temporadas":
    st.title("Comparativa entre temporadas")
    df_temp = aplicar_filtros(df)
    if not df_temp.empty:
        abp_temp = df_temp.groupby(['temporada', 'jornada']).size().reset_index(name='Cantidad')
        fig_temp = px.line(abp_temp, x='jornada', y='Cantidad', color='temporada', markers=True, title="ABP por jornada y temporada")
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("No hay datos para mostrar comparativa entre temporadas.")

elif pagina == "Mapa de conexiones (red ABP)":
    st.title("Red de conexiones en ABP")
    if 'jugador_objetivo' in df.columns:
        G = nx.DiGraph()
        for _, row in aplicar_filtros(df).dropna(subset=['jugador_ejecutor', 'jugador_objetivo']).iterrows():
            G.add_edge(row['jugador_ejecutor'], row['jugador_objetivo'])
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
        st.info("No hay columna 'jugador_objetivo' para crear la red de conexiones.")

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
