import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

# streamlit run e:/a.py
st.set_page_config(layout="wide")
st.title("📍 Map trạm")

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
    "Kinh độ (long)": "lon"
})

# =========================
# 2. CLEAN
# =========================
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
df = df.dropna(subset=["lat", "lon"])

df["lat"] = df["lat"].astype(float)
df["lon"] = df["lon"].astype(float)
df["ma_tram"] = df["ma_tram"].astype(str).str.strip()
df["ma_diem"] = df["ma_diem"].astype(str).str.strip()
df["dia_chi"] = df["dia_chi"].astype(str)

# =========================
# 3. DONE COLUMN
# =========================
if "done" not in df.columns:
    df["done"] = ""

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
        "done": lambda x: "done" if "done" in x.values else ""
    })
    .reset_index()
)

# ⭐ nhiều mã điểm khác nhau tại cùng tọa độ
grouped["multi_point"] = grouped["ma_diem"].apply(
    lambda x: len(set(x)) > 1
)

# ⭐ trùng mã điểm tại cùng tọa độ (>=2 bản ghi cùng mã)
grouped["duplicate_same_ma_diem"] = grouped["ma_diem"].apply(
    lambda x: len(x) > len(set(x))
)

# =========================
# 🔍 SEARCH
# =========================
st.sidebar.header("🔍 Tìm kiếm")

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
# 🎯 CHỌN
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
# 7. MAP
# =========================
if selected_row is not None:
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
# 8. MARKER
# =========================
for _, row in grouped.iterrows():
    lat = float(row["lat"])
    lon = float(row["lon"])

    ma_diem_list = row["ma_diem"]
    dia_chi_list = row["dia_chi"]
    sn_list = row["ma_tram"]
    done_flag = row["done"]

    is_multi_diff = row["multi_point"]
    is_duplicate_same = row["duplicate_same_ma_diem"]

    unique_ma_diem = set(ma_diem_list)

    # =====================
    # 🎨 COLOR LOGIC
    # =====================
    if is_multi_diff:
        color = "blue"  # khác mã điểm
    elif is_duplicate_same:
        color = "orange"  # ⭐ trùng mã điểm → vàng
    else:
        color = "green" if done_flag == "done" else "red"

    tooltip_text = (
        f"Nhiều mã điểm ({len(unique_ma_diem)})"
        if is_multi_diff
        else f"{ma_diem_list[0]} ({len(sn_list)} SN)"
    )

    # ===============================
    # CASE: khác mã điểm -> KHÔNG popup
    # ===============================
    if is_multi_diff:
        folium.Marker(
            location=[lat, lon],
            tooltip=tooltip_text,
            icon=folium.Icon(color=color, icon="flag"),
        ).add_to(m)

    else:
        # popup scroll
        detail_html = ""
        for md, dc, sn in zip(ma_diem_list, dia_chi_list, sn_list):
            detail_html += f"""
            <b>Mã điểm:</b> {md}<br>
            <b>Địa chỉ:</b> {dc}<br>
            <b>SN:</b> {sn}<br>
            <hr>
            """

        popup_html = f"""
        <div style="max-height:150px; overflow-y:auto; width:260px; font-size:13px;">
            <b>Tọa độ:</b> {lat:.5f}, {lon:.5f}<br>
            <b>Tổng SN:</b> {len(sn_list)}<br>
            <hr>
            {detail_html}
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=tooltip_text,
            icon=folium.Icon(color=color, icon="flag"),
        ).add_to(m)

# =========================
# 9. HIỂN THỊ MAP
# =========================
st_data = st_folium(
    m,
    width=1200,
    height=700,
    returned_objects=["last_object_clicked"],
)

# =========================
# 10. DONE THEO SN
# =========================
clicked = st_data.get("last_object_clicked")

if clicked:
    lat_click = float(clicked["lat"])
    lon_click = float(clicked["lng"])

    st.success(f"Đã chọn điểm: {lat_click}, {lon_click}")

    EPS = 1e-9

    point_rows = df[
        ((df["lat"] - lat_click).abs() < EPS)
        & ((df["lon"] - lon_click).abs() < EPS)
    ].copy()

    if len(point_rows) == 0:
        st.warning("Không tìm thấy SN tại điểm này")
    else:
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