import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
import re

# streamlit run e:/Test/a.py

st.set_page_config(layout="wide")
st.title("📍 Map trạm")

# =========================
# SESSION
# =========================
if "search_location" not in st.session_state:
    st.session_state.search_location = None

if "search_mode" not in st.session_state:
    st.session_state.search_mode = None

FILE_PATH = "du_lieu_tram.xlsx"

# =========================
# PARSE COORDINATE
# =========================
def dms_to_decimal(dms):

    regex = r"(\d+)[°\s]+(\d+)'([\d\.]+)\"?([NSEW])"
    match = re.search(regex, dms)

    if not match:
        return None

    deg = float(match.group(1))
    minute = float(match.group(2))
    sec = float(match.group(3))
    direction = match.group(4)

    decimal = deg + minute / 60 + sec / 3600

    if direction in ["S", "W"]:
        decimal *= -1

    return decimal


# def parse_lat_lon(lat, lon):

#     # case 1: bình thường
#     try:
#         if pd.notna(lat) and pd.notna(lon):
#             return float(lat), float(lon)
#     except:
#         pass

#     if pd.isna(lat):
#         return None, None

#     text = str(lat).strip()

#     # case 2: decimal pair
#     if "," in text and text.count(",") == 1:
#         try:
#             a, b = text.split(",")
#             return float(a), float(b)
#         except:
#             pass

#     # case 3: N E format
#     if "N" in text and "E" in text:

#         parts = text.replace(",", ".").split()

#         if len(parts) >= 2:
#             try:
#                 lat_val = float(parts[0].replace("N", ""))
#                 lon_val = float(parts[1].replace("E", ""))
#                 return lat_val, lon_val
#             except:
#                 pass

#     # case 4: DMS
#     if "°" in text:

#         lat_val = dms_to_decimal(text)
#         lon_match = re.findall(r"\d+°\d+'\d+\.?\d*\"?[EW]", text)

#         if lat_val and lon_match:
#             lon_val = dms_to_decimal(lon_match[0])
#             return lat_val, lon_val

#     return None, None

def parse_lat_lon(lat, lon):

    # ===== case 1: lat lon chuẩn =====
    try:
        if pd.notna(lat) and pd.notna(lon):
            return float(lat), float(lon)
    except:
        pass

    if pd.isna(lat):
        return None, None

    text = str(lat).strip()

    # ===== case 2: 21.195397,105.313589 =====
    if "," in text and text.count(",") == 1:
        try:
            a, b = text.split(",")
            return float(a), float(b)
        except:
            pass

    # ===== case 3: 20.987933°N, 105.636434°E =====
    pattern = r"([\d\.]+)°?\s*[NS],?\s*([\d\.]+)°?\s*[EW]"
    match = re.search(pattern, text)

    if match:
        lat_val = float(match.group(1))
        lon_val = float(match.group(2))
        return lat_val, lon_val

    # ===== case 4: 21,1708N 105,3934E =====
    if "N" in text and "E" in text:

        text = text.replace(",", ".")
        parts = text.split()

        if len(parts) >= 2:
            try:
                lat_val = float(parts[0].replace("N", ""))
                lon_val = float(parts[1].replace("E", ""))
                return lat_val, lon_val
            except:
                pass

    # ===== case 5: DMS =====
    if "°" in text and "'" in text:

        try:
            lat_match = re.search(r"\d+°\d+'\d+\.?\d*\"?[NS]", text)
            lon_match = re.search(r"\d+°\d+'\d+\.?\d*\"?[EW]", text)

            if lat_match and lon_match:
                lat_val = dms_to_decimal(lat_match.group())
                lon_val = dms_to_decimal(lon_match.group())
                return lat_val, lon_val
        except:
            pass

    return None, None
# =========================
# LOAD DATA
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
# ENSURE COLUMN
# =========================
required_cols = [
    "ma_tram",
    "ma_diem",
    "dia_chi",
    "xa_phuong",
    "tinh",
    "lat",
    "lon",
    "done"
]

for col in required_cols:
    if col not in df.columns:
        df[col] = ""

# =========================
# CLEAN DATA
# =========================
errors = []

new_lat = []
new_lon = []

for i, row in df.iterrows():

    lat, lon = parse_lat_lon(row["lat"], row["lon"])

    if lat is None or lon is None:
        errors.append(i)

    new_lat.append(lat)
    new_lon.append(lon)

df["lat"] = new_lat
df["lon"] = new_lon

# báo lỗi
if len(errors) > 0:

    st.warning(f"⚠ Có {len(errors)} dòng lỗi tọa độ không hiển thị")

    with st.expander("Xem dòng lỗi"):
        st.write(df.loc[errors][["ma_tram", "ma_diem", "lat", "lon"]])

df = df.dropna(subset=["lat", "lon"])

df["lat"] = df["lat"].astype(float)
df["lon"] = df["lon"].astype(float)

df["ma_tram"] = df["ma_tram"].astype(str)
df["ma_diem"] = df["ma_diem"].astype(str)

df["done"] = df["done"].fillna("").astype(str)

# =========================
# GROUP
# =========================
grouped = (
    df.groupby(["lat", "lon"])
    .agg({
        "ma_diem": lambda x: list(x),
        "dia_chi": lambda x: list(x),
        "ma_tram": lambda x: list(x),
        "xa_phuong": lambda x: list(x),
        "tinh": lambda x: list(x),
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
# SEARCH
# =========================
st.sidebar.header("🔍 Tìm kiếm trạm")

keyword = st.sidebar.text_input(
    "Nhập địa chỉ, mã điểm, SN hoặc tọa độ", ""
)

filtered = grouped.copy()

if keyword:

    key = keyword.lower()

    filtered = grouped[
        grouped.apply(
            lambda r: (
                key in str(r["lat"])
                or key in str(r["lon"])
                or any(key in str(md).lower() for md in r["ma_diem"])
                or any(key in str(sn).lower() for sn in r["ma_tram"])
            ),
            axis=1,
        )
    ]

st.sidebar.write(f"🔎 Tìm thấy: {len(filtered)} điểm")

# =========================
# MAP CENTER
# =========================
if len(filtered) == 1:

    center_lat = filtered.iloc[0]["lat"]
    center_lon = filtered.iloc[0]["lon"]
    zoom_start = 16

else:

    center_lat = grouped["lat"].mean()
    center_lon = grouped["lon"].mean()
    zoom_start = 12

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start
)

# =========================
# MARKER
# =========================
for _, row in grouped.iterrows():

    lat = row["lat"]
    lon = row["lon"]

    if row["all_done"]:
        color = "green"

    elif row["multi_point"]:
        color = "blue"

    elif row["duplicate_same_ma_diem"]:
        color = "orange"

    else:
        color = "red"

    gmap = f"https://www.google.com/maps?q={lat},{lon}"

    popup_html = f"""
    <div style="width:250px">

        <b>Tọa độ:</b> {lat},{lon}

        <a href="{gmap}" target="_blank"
        style="
        display:inline-block;
        padding:3px 8px;
        border:1px solid #4285F4;
        border-radius:6px;
        color:#4285F4;
        text-decoration:none;
        font-size:12px;
        ">
        📍 Map
        </a>

        <hr>

        <b>Tổng SN:</b> {len(row['ma_tram'])}

        <hr>

        <div style="max-height:120px;overflow-y:auto">
    """

    for md, sn, dc, xp,ti, done in zip(
        row["ma_diem"],
        row["ma_tram"],
        row["dia_chi"],
        row["xa_phuong"],
        row["tinh"],
        row["done"]
    ):

        status = "✅" if done == "done" else "❌"

        popup_html += f"""
        <b>Mã điểm:</b> {md}<br>
        <b>SN:</b> {sn}<br>
        <b>Địa chỉ:</b> {dc}<br>
        <b>Xã phường:</b> {xp}<br>
        <b>Tỉnh:</b> {ti}<br>
        <hr>
        """

    popup_html += "</div></div>"

    folium.Marker(
        location=[lat, lon],
        tooltip=f"{row['ma_diem'][0]} ({len(row['ma_tram'])} SN)",
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=color, icon="flag"),
    ).add_to(m)

# =========================
# SHOW MAP
# =========================
st_data = st_folium(
    m,
    width=1200,
    height=700,
    returned_objects=["last_object_clicked"],
)

clicked = st_data.get("last_object_clicked")

# =========================
# DONE SN
# =========================
if clicked:

    lat_click = clicked["lat"]
    lon_click = clicked["lng"]

    EPS = 1e-9

    rows = df[
        ((df["lat"] - lat_click).abs() < EPS)
        & ((df["lon"] - lon_click).abs() < EPS)
    ]

    if len(rows) > 0:

        st.subheader(f"🔧 Có {len(rows)} SN tại điểm này")

        for idx, row in rows.iterrows():

            col1, col2, col3 = st.columns([3,2,2])

            with col1:
                st.write(f"SN: {row['ma_tram']}")
                st.caption(f"Mã điểm: {row['ma_diem']}")

            with col2:

                status = "✅ DONE" if row["done"]=="done" else "❌ Chưa xong"
                st.write(status)

            with col3:

                if row["done"]!="done":

                    if st.button(
                        f"Hoàn thành {row['ma_tram']}",
                        key=f"done_{idx}"
                    ):

                        df.loc[idx,"done"]="done"
                        df.to_excel(FILE_PATH,index=False)

                        st.success(f"🎉 DONE {row['ma_tram']}")
                        st.rerun()