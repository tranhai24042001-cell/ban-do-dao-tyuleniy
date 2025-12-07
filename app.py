import streamlit as st
import leafmap.foliumap as leafmap
import os
import pandas as pd
import altair as alt

# --- THƯ VIỆN XỬ LÝ ẢNH ---
import rasterio
from rasterio.warp import reproject, Resampling

# --- IMPORT MODULE BẮT BUỘC ---
from folium import MacroElement
from branca.element import Template
# ------------------------------

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="WebGIS Monitoring - Остров Тюлений")

# Tọa độ trung tâm đảo Tyuleniy
TARGET_CENTER = [44.475, 47.513]
TARGET_ZOOM = 13

# --- CSS TÙY CHỈNH ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        h1 {text-align: center; color: #2c3e50;}
        .stat-box {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
            margin-bottom: 10px;
        }
        .info-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #ddd;
            margin-top: 20px;
            font-family: 'Arial', sans-serif;
            color: #333;
            line-height: 1.6;
        }
        .info-card h3 { color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .info-card h4 { color: #007bff; margin-top: 15px; margin-bottom: 5px; font-weight: bold; }
        .info-card ul { margin-left: 20px; margin-bottom: 10px; }
        .info-card li { margin-bottom: 5px; }
        
        .comp-header { font-weight: bold; text-align: center; color: #555; margin-bottom: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- 2. HÀM ĐỌC DỮ LIỆU ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("so_lieu_thong_ke.xlsx", engine='openpyxl')
        cols_to_fix = ['Длина', 'Вода', 'Почва', 'Водно-полотные', 'Растения']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').apply(pd.to_numeric, errors='coerce')
        if 'Год' in df.columns:
            df['Year_Str'] = df['Год'].astype(str)
            df = df.set_index("Год")
        return df
    except Exception:
        return None

df_stats = load_data()

# --- 3. MENU BÊN TRÁI (CHỈ ĐIỀU KHIỂN BẢN ĐỒ CHÍNH) ---
with st.sidebar:
    st.header("BẢN ĐỒ CHÍNH (MAIN MAP)")
    
    available_years = []
    if os.path.exists("data"):
        available_years = sorted([d for d in os.listdir("data") if os.path.isdir(os.path.join("data", d))])
    if not available_years and df_stats is not None:
        available_years = sorted(df_stats.index.tolist())
    if not available_years: available_years = [2024]
    
    # Biến này chỉ dành cho Bản đồ chính
    selected_year_main = st.selectbox("Chọn năm hiển thị chính:", available_years, index=len(available_years)-1, key="main_year_selector")
    
    st.markdown("---")

    # Số liệu thống kê (Theo năm chính)
    coastline_val = 0
    data_table = {"Классификация": [], "Площадь (га)": []}
    if df_stats is not None and int(selected_year_main) in df_stats.index:
        row = df_stats.loc[int(selected_year_main)]
        coastline_val = row.get('Длина', 0)
        data_table = {
            "Классификация": ["Вода", "Почва", "Водно-болотные", "Растения"],
            "Площадь (га)": [
                f"{row.get('Вода', 0):,.2f}", f"{row.get('Почва', 0):,.2f}",
                f"{row.get('Водно-полотные', 0):,.2f}", f"{row.get('Растения', 0):,.2f}"
            ]
        }

    st.subheader("Статистика (Thống kê)")
    st.markdown(f"""
    <div class="stat-box">
        <b>📏 Длина береговой линии:</b><br>
        <span style="font-size: 24px; color: blue; font-weight: bold;">{coastline_val:,.2f} km</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<b>🌳 Детализация площади:</b>", unsafe_allow_html=True)
    st.dataframe(data_table, hide_index=True)

    # Biểu đồ
    st.markdown("---")
    st.subheader("📊 Динамика изменений")
    def make_bar_chart(data, y_col, color_hex, title, y_label):
        bars = alt.Chart(data).mark_bar(color=color_hex).encode(
            x=alt.X('Year_Str', title=None, axis=alt.Axis(labels=False)),
            y=alt.Y(y_col, title=None),
            tooltip=['Year_Str', alt.Tooltip(y_col, title=y_label, format=",.2f")]
        )
        text = bars.mark_text(align='center', baseline='bottom', dy=-5, color='black', fontSize=10).encode(text=alt.Text(y_col, format=",.0f"))
        return (bars + text).properties(title=title, height=150)

    if df_stats is not None:
        chart_data = df_stats.reset_index()
        col1, col2 = st.sidebar.columns(2)
        with col1: st.altair_chart(make_bar_chart(chart_data, 'Длина', '#0000FF', 'Длина (km)', 'км'), use_container_width=True)
        with col2: st.altair_chart(make_bar_chart(chart_data, 'Почва', '#D2691E', 'Почва (ha)', 'га'), use_container_width=True)
        col3, col4 = st.sidebar.columns(2)
        with col3: st.altair_chart(make_bar_chart(chart_data, 'Водно-полотные', '#00CED1', 'Водно-болотные (ha)', 'га'), use_container_width=True)
        with col4: st.altair_chart(make_bar_chart(chart_data, 'Растения', '#228B22', 'Растения (ha)', 'га'), use_container_width=True)

# --- 4. TIÊU ĐỀ ---
st.title(f"Остров Тюлений - {selected_year_main}")

# --- 5. TẠO NÚT ZOOM (SVG) ---
zoom_icon_svg = """
<svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="12" cy="12" r="10" stroke="#444" stroke-width="2" fill="white" fill-opacity="0.8"/>
<line x1="12" y1="2" x2="12" y2="22" stroke="#444" stroke-width="2"/>
<line x1="2" y1="12" x2="22" y2="12" stroke="#444" stroke-width="2"/>
<circle cx="12" cy="12" r="2" fill="#444"/>
</svg>
"""
class ZoomButton(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            L.Control.ZoomButton = L.Control.extend({
                onAdd: function(map) {
                    var btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control');
                    btn.innerHTML = `""" + zoom_icon_svg + """`;
                    btn.style.width = '34px';
                    btn.style.height = '34px';
                    btn.style.backgroundColor = 'white';
                    btn.style.cursor = 'pointer';
                    btn.style.border = '2px solid rgba(0,0,0,0.2)';
                    btn.style.display = 'flex';
                    btn.style.alignItems = 'center';
                    btn.style.justifyContent = 'center';
                    btn.title = 'Zoom to Island';
                    btn.onclick = function() { map.setView([44.475, 47.513], 13); };
                    return btn;
                }
            });
            new L.Control.ZoomButton({ position: 'topright' }).addTo({{this._parent.get_name()}});
        {% endmacro %}
    """)

# --- 6. HÀM XỬ LÝ ẢNH ---
def process_matched_image(sat_path, class_path):
    output_path = sat_path.replace(".tif", "_matched.tif")
    if os.path.exists(output_path): return output_path
    try:
        with rasterio.open(class_path) as ref:
            dst_crs, dst_transform = ref.crs, ref.transform
            dst_width, dst_height = ref.width, ref.height
            kwargs = ref.meta.copy()
        with rasterio.open(sat_path) as src:
            dtype_val = src.dtypes[0] if isinstance(src.dtypes, (list, tuple)) else src.dtypes
            kwargs.update({'crs': dst_crs, 'transform': dst_transform, 'width': dst_width, 'height': dst_height, 'count': src.count, 'dtype': dtype_val, 'driver': 'GTiff'})
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i), src_transform=src.transform, src_crs=src.crs, dst_transform=dst_transform, dst_crs=dst_crs, resampling=Resampling.nearest)
        return output_path
    except Exception: return sat_path 

# --- 7. BẢN ĐỒ CHÍNH (ĐỘC LẬP) ---
def render_main_map(year):
    original_sat_path = f"data/{year}/satellite.tif"
    class_path = f"data/{year}/landcover.tif"
    sat_path = process_matched_image(original_sat_path, class_path) if os.path.exists(original_sat_path) and os.path.exists(class_path) else original_sat_path

    m = leafmap.Map(center=TARGET_CENTER, zoom=TARGET_ZOOM, draw_control=False, measure_control=False, fullscreen_control=True, scale_control=True, tiles=None)
    m.add_tile_layer(url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", name="Google Satellite", attribution="Google", overlay=True, shown=False)
    m.add_tile_layer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", name="OpenStreetMap", attribution="OpenStreetMap", overlay=True, shown=False)

    if os.path.exists(sat_path) and os.path.exists(class_path):
        m.split_map(left_layer=sat_path, right_layer=class_path)
    else:
        st.warning(f"Chưa tìm thấy ảnh năm {year}")

    m.add_child(ZoomButton())

    legend_html = """
    <div style="position: fixed; bottom: 30px; right: 10px; width: 170px; background-color: white; border: 2px solid #333; z-index:9999; font-size:14px; padding: 10px; opacity: 0.95; font-family: Arial, sans-serif;">
        <b style="color:black; display:block; margin-bottom:5px; border-bottom:1px solid #ccc; padding-bottom:3px;">&#1050;&#1083;&#1072;&#1089;&#1089;&#1080;&#1092;&#1080;&#1082;&#1072;&#1094;&#1080;&#1103;</b>
        <div style="margin-bottom:4px;"><span style="background:blue; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1042;&#1086;&#1076;&#1072;</span></div>
        <div style="margin-bottom:4px;"><span style="background:#D2691E; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1055;&#1086;&#1095;&#1074;&#1072;</span></div>
        <div style="margin-bottom:4px;"><span style="background:#00CED1; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1042;&#1086;&#1076;&#1085;&#1086;-&#1073;&#1086;&#1083;&#1086;&#1090;.</span></div>
        <div style="margin-bottom:4px;"><span style="background:green; width:18px; height:18px; display:inline-block; margin-right:8px; border:1px solid #999;"></span><span>&#1056;&#1072;&#1089;&#1090;&#1077;&#1085;&#1080;&#1103;</span></div>
        <div style="margin-top:6px; padding-top:4px; border-top:1px dashed #ccc;"><span style="border: 2px solid red; background:transparent; width:18px; height:12px; display:inline-block; margin-right:8px;"></span><span>&#1043;&#1088;&#1072;&#1085;&#1080;&#1094;&#1072;</span></div>
    </div>
    """
    m.add_html(legend_html, position='bottomright')
    return m

# Hiển thị bản đồ chính
m_main = render_main_map(selected_year_main)
m_main.to_streamlit(height=500)

# ====================================================================
# --- 8. PHẦN SO SÁNH (ĐỘC LẬP HOÀN TOÀN) ---
# ====================================================================
col_comp1, col_comp2 = st.columns(2)

def render_sub_map_independent(key_suffix):
    # Mỗi ô có menu riêng, dùng KEY riêng (key_suffix) để không bị trùng
    c_y, c_t = st.columns([1, 1])
    with c_y:
        # Biến năm riêng cho ô này
        y_sel = st.selectbox("Год:", available_years, key=f"year_{key_suffix}")
    with c_t:
        # Biến loại ảnh riêng cho ô này
        t_sel = st.selectbox("Тип:", ["Спутник", "Классификация"], key=f"type_{key_suffix}")
    
    final_path = None
    if "Спутник" in t_sel: 
        final_path = f"data/{y_sel}/satellite.tif"
    else: 
        final_path = f"data/{y_sel}/landcover.tif"

    m_sub = leafmap.Map(center=TARGET_CENTER, zoom=TARGET_ZOOM, draw_control=False, measure_control=False, scale_control=True, tiles="OpenStreetMap")
    
    if final_path and os.path.exists(final_path):
        try:
            m_sub.add_raster(final_path, layer_name="Image", zoom_to_layer=False)
        except Exception as e:
            st.error("Cần cài thư viện: pip install xarray rioxarray")
    else:
        st.warning(f"Không có ảnh {y_sel}")
    
    m_sub.to_streamlit(height=400)

# Gọi hàm render cho 2 cột với key khác nhau ("left" và "right")
# Điều này đảm bảo chúng độc lập với nhau và độc lập với Main Map
with col_comp1:
    st.markdown('<div class="comp-header"></div>', unsafe_allow_html=True)
    render_sub_map_independent("left")

with col_comp2:
    st.markdown('<div class="comp-header"></div>', unsafe_allow_html=True)
    render_sub_map_independent("right")
# ====================================================================

# --- 9. THÔNG TIN ĐẢO ---
# [FIX LỖI 3] Đảm bảo unsafe_allow_html=True để render thẻ HTML
st.markdown("---")
st.subheader("ℹ️ Обзор острова Тюлений")
st.markdown("""
<div class="info-card">
    <h3>Остров Тюлений (Tyuleniy Island)</h3>
    <p>Остров Тюлений — это песчаный остров, расположенный в северо-западной части Каспийского моря в 47 км от побережья Дагестана (Россия), который, несмотря на отсутствие постоянного населения, имеет исключительное экологическое значение как ключевое место обитания краснокнижных каспийских тюленей и гнездования редких видов птиц. Остров характеризуется низменным рельефом с неустойчивой формой, постоянно меняющейся под воздействием колебаний уровня моря и ветров, а также суровым полупустынным климатом; ранее здесь существовал рыбацкий поселок, но в настоящее время территория используется исключительно для работы гидрометеорологической станции и пограничных постов с целью мониторинга уникальной экосистемы..</p>
</div>
""", unsafe_allow_html=True)
