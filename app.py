import streamlit as st
import leafmap.foliumap as leafmap
import os
import pandas as pd
import altair as alt
import rasterio
from rasterio.warp import reproject, Resampling
from folium import MacroElement
from branca.element import Template

st.set_page_config(layout="wide", page_title="WebGIS Monitoring - Остров Тюлений")

# Tọa độ trung tâm
TARGET_CENTER = [44.475, 47.513]
TARGET_ZOOM = 13

# CSS
st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        h1 {text-align: center; color: #2c3e50;}
        .stat-box { background-color: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #dee2e6; margin-bottom: 10px; }
        .info-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-top: 20px; font-family: 'Arial', sans-serif; color: #333; line-height: 1.6; }
        .info-card h3 { color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .info-card h4 { color: #007bff; margin-top: 15px; margin-bottom: 5px; font-weight: bold; }
        .info-card ul { margin-left: 20px; margin-bottom: 10px; }
        .info-card li { margin-bottom: 5px; }
        .comp-header { font-weight: bold; text-align: center; color: #555; margin-bottom: 5px;}
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("so_lieu_thong_ke.xlsx", engine='openpyxl')
        cols = ['Длина', 'Вода', 'Почва', 'Водно-полотные', 'Растения']
        for c in cols:
            if c in df.columns: df[c] = df[c].astype(str).str.replace(',', '.').apply(pd.to_numeric, errors='coerce')
        if 'Год' in df.columns:
            df['Year_Str'] = df['Год'].astype(str)
            df = df.set_index("Год")
        return df
    except: return None

df_stats = load_data()

with st.sidebar:
    st.header("ВЫБЕРИТЕ ГОД (CHỌN NĂM)")
    years = []
    if os.path.exists("data"): years = sorted([d for d in os.listdir("data") if os.path.isdir(os.path.join("data", d))])
    
    # Fallback
    if not years and df_stats is not None: years = sorted(df_stats.index.tolist())
    if not years: years = [2024]
    
    sel_year = st.selectbox("Год:", years, index=len(years)-1, key="main_year")
    st.markdown("---")
    
    val = 0
    dt = {"Классификация": [], "Площадь (га)": []}
    if df_stats is not None and int(sel_year) in df_stats.index:
        r = df_stats.loc[int(sel_year)]
        val = r.get('Длина', 0)
        dt = {
            "Классификация": ["Вода", "Почва", "Водно-болотные", "Растения"],
            "Площадь (га)": [f"{r.get('Вода', 0):,.2f}", f"{r.get('Почва', 0):,.2f}", f"{r.get('Водно-полотные', 0):,.2f}", f"{r.get('Растения', 0):,.2f}"]
        }
    
    st.subheader("Статистика")
    st.markdown(f"<div class='stat-box'><b>📏 Длина береговой линии:</b><br><span style='font-size: 24px; color: blue; font-weight: bold;'>{val:,.2f} km</span></div>", unsafe_allow_html=True)
    st.markdown("<b>🌳 Детализация площади:</b>", unsafe_allow_html=True)
    st.dataframe(dt, hide_index=True)
    
    st.markdown("---")
    st.subheader("📊 Динамика изменений")
    if df_stats is not None:
        cd = df_stats.reset_index()
        def chart(d, y, c, t):
            b = alt.Chart(d).mark_bar(color=c).encode(x=alt.X('Year_Str', axis=alt.Axis(labels=False), title=None), y=alt.Y(y, title=None), tooltip=['Year_Str', y])
            return (b + b.mark_text(align='center', dy=-5, color='black').encode(text=alt.Text(y, format=",.0f"))).properties(title=t, height=150)
        
        c1, c2 = st.sidebar.columns(2)
        with c1: st.altair_chart(chart(cd, 'Длина', '#0000FF', 'Длина (km)'), use_container_width=True)
        with c2: st.altair_chart(chart(cd, 'Почва', '#D2691E', 'Почва (ha)'), use_container_width=True)
        c3, c4 = st.sidebar.columns(2)
        with c3: st.altair_chart(chart(cd, 'Водно-полотные', '#00CED1', 'Водно-болотные'), use_container_width=True)
        with c4: st.altair_chart(chart(cd, 'Растения', '#228B22', 'Растения (ha)'), use_container_width=True)

st.title(f"Остров Тюлений - {sel_year}")

# Zoom Button
zoom_svg = """<svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="#444" stroke-width="2" fill="white" fill-opacity="0.8"/><line x1="12" y1="2" x2="12" y2="22" stroke="#444" stroke-width="2"/><line x1="2" y1="12" x2="22" y2="12" stroke="#444" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="#444"/></svg>"""
class ZoomButton(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            L.Control.ZoomButton = L.Control.extend({
                onAdd: function(map) {
                    var btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control');
                    btn.innerHTML = `""" + zoom_svg + """`;
                    btn.style.width = '34px'; btn.style.height = '34px'; btn.style.backgroundColor = 'white'; btn.style.cursor = 'pointer'; btn.style.border = '2px solid rgba(0,0,0,0.2)'; btn.style.display = 'flex'; btn.style.alignItems = 'center'; btn.style.justifyContent = 'center'; btn.title = 'Zoom to Island';
                    btn.onclick = function() { map.setView([44.475, 47.513], 13); };
                    return btn;
                }
            });
            new L.Control.ZoomButton({ position: 'topright' }).addTo({{this._parent.get_name()}});
        {% endmacro %}
    """)

# Process Image Fix
def process_img(s, c):
    o = s.replace(".tif", "_matched.tif")
    if os.path.exists(o): return o
    try:
        with rasterio.open(c) as ref:
            dst_crs, dst_tr, w, h = ref.crs, ref.transform, ref.width, ref.height
            kw = ref.meta.copy()
        with rasterio.open(s) as src:
            # --- FIX QUAN TRỌNG: Dùng dtypes[0] ---
            dt = src.dtypes[0] if isinstance(src.dtypes, (list, tuple)) else src.dtypes
            kw.update({'crs': dst_crs, 'transform': dst_tr, 'width': w, 'height': h, 'count': src.count, 'dtype': dt, 'driver': 'GTiff'})
            with rasterio.open(o, 'w', **kw) as dst:
                for i in range(1, src.count+1):
                    reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i), src_transform=src.transform, src_crs=src.crs, dst_transform=dst_tr, dst_crs=dst_crs, resampling=Resampling.nearest)
        return o
    except: return s

def render_map(y):
    s = f"data/{y}/satellite.tif"
    c = f"data/{y}/landcover.tif"
    s_final = process_img(s, c) if os.path.exists(s) and os.path.exists(c) else s
    
    m = leafmap.Map(center=TARGET_CENTER, zoom=TARGET_ZOOM, draw_control=False, measure_control=False, fullscreen_control=True, scale_control=True)
    m.add_tile_layer(url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", name="Google Satellite", attribution="Google", overlay=True, shown=False)
    
    if os.path.exists(s_final) and os.path.exists(c):
        m.split_map(left_layer=s_final, right_layer=c)
    else:
        st.warning(f"Chưa tìm thấy ảnh năm {y}")
        
    m.add_child(ZoomButton())
    
    # Legend Fix Font
    legend = """<div style="position: fixed; bottom: 30px; right: 10px; width: 170px; background-color: white; border: 2px solid #333; z-index:9999; font-size:14px; padding: 10px; opacity: 0.95; font-family: Arial, sans-serif;"><b style="color:black; display:block; margin-bottom:5px; border-bottom:1px solid #ccc; padding-bottom:3px;">&#1050;&#1083;&#1072;&#1089;&#1089;&#1080;&#1092;&#1080;&#1082;&#1072;&#1094;&#1080;&#1103;</b><div style="margin-bottom:4px;"><span style="background:blue; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1042;&#1086;&#1076;&#1072;</span></div><div style="margin-bottom:4px;"><span style="background:#D2691E; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1055;&#1086;&#1095;&#1074;&#1072;</span></div><div style="margin-bottom:4px;"><span style="background:#00CED1; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1042;&#1086;&#1076;&#1085;&#1086;-&#1073;&#1086;&#1083;&#1086;&#1090;.</span></div><div style="margin-bottom:4px;"><span style="background:green; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1056;&#1072;&#1089;&#1090;&#1077;&#1085;&#1080;&#1103;</span></div><div style="margin-top:6px; padding-top:4px; border-top:1px dashed #ccc;"><span style="border: 2px solid red; background:transparent; width:18px; height:12px; display:inline-block; margin-right:8px;"></span><span>&#1043;&#1088;&#1072;&#1085;&#1080;&#1094;&#1072;</span></div></div>"""
    m.add_html(legend, position='bottomright')
    return m

m = render_map(sel_year)
m.to_streamlit(height=500)

# --- PHẦN SO SÁNH ---
st.markdown("---"); st.subheader("🔍 Сравнение изображений (So sánh chi tiết)")
c1, c2 = st.columns(2)
def sub_map(k):
    cy, ct = st.columns([1,1])
    with cy: y = st.selectbox("Год:", years, key=f"y_{k}")
    with ct: t = st.selectbox("Тип:", ["Спутник", "Классификация"], key=f"t_{k}")
    p = f"data/{y}/satellite.tif" if "Спутник" in t else f"data/{y}/landcover.tif"
    
    ms = leafmap.Map(center=TARGET_CENTER, zoom=TARGET_ZOOM, draw_control=False, measure_control=False, scale_control=True)
    if os.path.exists(p):
        try: ms.add_raster(p, layer_name="Img", zoom_to_layer=False)
        except: st.error("Lỗi: Cần localtileserver")
    ms.to_streamlit(height=400)

with c1: st.markdown('<div class="comp-header">Cửa sổ 1</div>', unsafe_allow_html=True); sub_map("L")
with c2: st.markdown('<div class="comp-header">Cửa sổ 2</div>', unsafe_allow_html=True); sub_map("R")

# --- INFO ---
st.markdown("---"); st.subheader("ℹ️ Обзор острова Тюлений")
st.markdown("""<div class="info-card"><h3>Остров Тюлений</h3><p>Остров Тюлений — песчаный остров в северо-западной части Каспийского моря.</p><h4>1. 📍 География</h4><ul><li><b>Расположение:</b> 47 км от Дагестана.</li><li><b>Размеры:</b> Длина 8-10 км.</li></ul><h4>2. 🏜️ Климат</h4><ul><li>Полупустынный, засушливый.</li></ul><h4>3. 🌿 Экосистема</h4><ul><li>Важное лежбище каспийского тюленя и место гнездования птиц.</li></ul></div>""", unsafe_allow_html=True)
