import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

# streamlit run e:/a.py

st.set_page_config(layout="wide")
st.title("📍 Map trạm")

# ===== SESSION STATE =====
if "search_location" not in st.session_state:
    st.session_state.search_location = None
if "search_mode" not in st.session_state:
    st.session_state.search_mode = None

FILE_PATH = "du_lieu_tram.xlsx"

# =========================
# 1. LOAD
# =========================
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip()

df = df.rename(columns={
    "SN": "ma_tram",
    "Mã trạm": "ma_diem",
    "Địa chỉ": "dia_chi",
    "Vĩ độ (lat)": "lat",
    "Kinh độ (long)": "lon",
    "Xã phường": "xa_phuong",
    "Tỉnh": "tinh"
})

# =========================
# 2. ĐẢM BẢO CỘT
# =========================
required_cols = [
    "ma_tram",
    "ma_diem",
    "dia_chi",
    "xa_phuong",
    "tinh",
    "lat",
    "lon",
    "done",
]

for col in required_cols:
    if col not in df.columns:
        df[col] = ""

# =========================
# 3. CLEAN
# =========================
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
df = df.dropna(subset=["lat", "lon"])

df["lat"] = df["lat"].astype(float)
df["lon"] = df["lon"].astype(float)
df["ma_tram"] = df["ma_tram"].astype(str).str.strip()
df["ma_diem"] = df["ma_diem"].astype(str).str.strip()
df["dia_chi"] = df["dia_chi"].astype(str)
df["xa_phuong"] = df["xa_phuong"].astype(str)
df["tinh"] = df["tinh"].astype(str)
df["done"] = df["done"].fillna("").astype(str)

# =========================
# 4. GROUP THEO TỌA ĐỘ
# =========================
grouped = (
    df.groupby(["lat", "lon"])
    .agg({
        "ma_diem": lambda x: list(x),
        "dia_chi": lambda x: list(x),
        "ma_tram": lambda x: list(x),
        "done": lambda x: list(x)
    })
    .reset_index()
)

grouped["all_done"] = grouped["done"].apply(
    lambda x: len(x) > 0 and all(v == "done" for v in x)
)

grouped["multi_point"] = grouped["ma_diem"].apply(
    lambda x: len(set(x)) > 1
)

grouped["duplicate_same_ma_diem"] = grouped["ma_diem"].apply(
    lambda x: len(x) > len(set(x))
)

# =========================
# 🔍 SEARCH TRẠM (GIỮ NGUYÊN)
# =========================
st.sidebar.header("🔍 Tìm kiếm trạm")

keyword = st.sidebar.text_input(
    "Nhập địa chỉ, mã điểm, SN hoặc tọa độ", ""
)

filtered = grouped.copy()

if keyword:
    key = keyword.lower().strip()
    filtered = grouped[
        grouped.apply(
            lambda r: (
                key in str(r["lat"])
                or key in str(r["lon"])
                or any(key in str(md).lower() for md in r["ma_diem"])
                or any(key in str(sn).lower() for sn in r["ma_tram"])
                or any(key in str(dc).lower() for dc in r["dia_chi"])
            ),
            axis=1,
        )
    ]

st.sidebar.write(f"🔎 Tìm thấy: {len(filtered)} điểm")

# =========================
# 📍 NHẢY THEO TỌA ĐỘ
# =========================
st.sidebar.markdown("---")
st.sidebar.header("📍 Nhảy tới tọa độ")

coord_input = st.sidebar.text_input(
    "Nhập lat,lon (vd: 21.0285,105.8542)"
)


def parse_lat_lon(text):
    try:
        parts = text.split(",")
        if len(parts) == 2:
            return float(parts[0].strip()), float(parts[1].strip())
    except:
        pass
    return None, None


if st.sidebar.button("Tới tọa độ"):
    lat_val, lon_val = parse_lat_lon(coord_input)

    if lat_val is not None and lon_val is not None:
        st.session_state.search_location = {
            "lat": lat_val,
            "lon": lon_val,
            "address": f"{lat_val}, {lon_val}"
        }
        st.session_state.search_mode = "coord"
        st.sidebar.success("✅ Đã nhảy tới tọa độ")
    else:
        st.sidebar.error("❌ Sai định dạng. Ví dụ: 21.0285,105.8542")

# =========================
# 🎯 CHỌN TRẠM
# =========================
selected_row = None

if len(filtered) == 1:
    selected_row = filtered.iloc[0]

elif len(filtered) > 1:
    options = filtered.apply(
        lambda r: f'{r["lat"]:.5f},{r["lon"]:.5f} | {len(r["ma_tram"])} SN',
        axis=1,
    ).tolist()

    choice = st.sidebar.selectbox("Chọn điểm:", options)
    selected_row = filtered.iloc[options.index(choice)]

# =========================
# MAP CENTER
# =========================
if st.session_state.search_location is not None:
    center_lat = st.session_state.search_location["lat"]
    center_lon = st.session_state.search_location["lon"]
    zoom_start = 17
elif selected_row is not None:
    center_lat = selected_row["lat"]
    center_lon = selected_row["lon"]
    zoom_start = 16
else:
    center_lat = grouped["lat"].mean()
    center_lon = grouped["lon"].mean()
    zoom_start = 12

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start,
    tiles="OpenStreetMap"
)

# =========================
# MARKER TRẠM (CÓ POPUP)
# =========================
for _, row in grouped.iterrows():

    lat = float(row["lat"])
    lon = float(row["lon"])

    if row["all_done"]:
        color = "green"
    elif row["multi_point"]:
        color = "blue"
    elif row["duplicate_same_ma_diem"]:
        color = "orange"
    else:
        color = "red"

    tooltip_text = f"{row['ma_diem'][0]} ({len(row['ma_tram'])} SN)"

    lat_str = f"{lat:.8f}"
    lon_str = f"{lon:.8f}"
    gg_link = f"https://www.google.com/maps?q={lat_str},{lon_str}"

    popup_html = f"""
    <div style="width:260px;font-size:13px">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <b>Tọa độ: {lat_str}, {lon_str}</b>
            <a href="{gg_link}" target="_blank"
            style="text-decoration:none;">
                <button style="
                    background:#4285F4;
                    color:white;
                    border:none;
                    padding:4px 10px;
                    border-radius:6px;
                    cursor:pointer;
                    font-size:10px;">
                    📍 Map
                </button>
            </a>
        </div>
        <hr style="margin:6px 0">
        <div><b>Tổng SN:</b> {len(row['ma_tram'])}</div>
        <br>
        <div><b>Mã điểm:</b> {row['ma_diem'][0]}</div>
        <div><b>Địa chỉ:</b> {row['dia_chi'][0]}</div>
        <div><b>SN:</b> {row['ma_tram'][0]}</div>
    </div>
    """

    folium.Marker(
        location=[lat, lon],
        tooltip=tooltip_text,
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=color, icon="flag"),
    ).add_to(m)

# =========================
# 📍 MARKER SEARCH (ICON GIỐNG GOOGLE MAP)
# =========================
if st.session_state.search_location:
    folium.Marker(
        location=[
            st.session_state.search_location["lat"],
            st.session_state.search_location["lon"],
        ],
        popup=folium.Popup(
            f"<b>📍 Điểm tìm kiếm</b><br>{st.session_state.search_location['address']}",
            max_width=300,
        ),
        tooltip="📍 Điểm nhập tọa độ",
        icon=folium.Icon(color="purple", icon="search", prefix="fa"),
    ).add_to(m)

# =========================
# HIỂN THỊ MAP
# =========================
st_data = st_folium(
    m,
    width=1200,
    height=700,
    returned_objects=["last_object_clicked"],
)

clicked = st_data.get("last_object_clicked")

# =========================
# ➕➖ ADD / DELETE ĐIỂM TỌA ĐỘ
# =========================
if (
    clicked
    and st.session_state.search_location
    and st.session_state.search_mode == "coord"
):

    lat_click = float(clicked["lat"])
    lon_click = float(clicked["lng"])
    EPS = 1e-9

    is_same_search_point = (
        abs(lat_click - st.session_state.search_location["lat"]) < EPS
        and abs(lon_click - st.session_state.search_location["lon"]) < EPS
    )

    if is_same_search_point:

        existed_rows = df[
            ((df["lat"] - lat_click).abs() < EPS)
            & ((df["lon"] - lon_click).abs() < EPS)
        ]

        st.subheader("⚙️ Quản lý điểm tọa độ")

        # ===== ADD =====
        if len(existed_rows) == 0:
            if st.button("➕ Add điểm này"):
                new_row = {
                    "ma_tram": "n/a",
                    "ma_diem": "n/a",
                    "dia_chi": "n/a",
                    "xa_phuong": "n/a",
                    "tinh": "n/a",
                    "lat": lat_click,
                    "lon": lon_click,
                    "done": ""
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_excel(FILE_PATH, index=False)

                st.success("✅ Đã thêm điểm mới")
                st.rerun()

        # ===== DELETE =====
        else:
            if st.button("🗑️ Delete điểm này"):
                df = df.drop(existed_rows.index)
                df.to_excel(FILE_PATH, index=False)

                st.success("🗑️ Đã xóa điểm")
                st.rerun()

# =========================
# DONE THEO SN (GIỮ NGUYÊN)
# =========================
if clicked:
    lat_click = float(clicked["lat"])
    lon_click = float(clicked["lng"])

    EPS = 1e-9

    point_rows = df[
        ((df["lat"] - lat_click).abs() < EPS)
        & ((df["lon"] - lon_click).abs() < EPS)
    ].copy()

    if len(point_rows) > 0:

        st.subheader(f"🔧 Có {len(point_rows)} SN tại điểm này")

        for idx, row in point_rows.iterrows():
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.write(f"**SN:** {row['ma_tram']}")
                st.caption(f"Mã điểm: {row['ma_diem']}")

            with col2:
                status = "✅ DONE" if row.get("done") == "done" else "❌ Chưa xong"
                st.write(status)

            with col3:
                if row.get("done") != "done":
                    if st.button(
                        f"Hoàn thành {row['ma_tram']}",
                        key=f"done_{idx}",
                    ):
                        df.loc[idx, "done"] = "done"
                        df.to_excel(FILE_PATH, index=False)
                        st.success(f"🎉 Đã DONE SN {row['ma_tram']}")
                        st.rerun()