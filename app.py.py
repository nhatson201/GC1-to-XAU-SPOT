import math
import pandas as pd
import streamlit as st

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN WEB STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Quant Options Web Dashboard", page_icon="📊", layout="wide"
)

st.title("📊 HỆ THỐNG TỰ ĐỘNG XỬ LÝ DỮ LIỆU QUIKSTRIKE & EVENT VOLATILITY")
st.write(
    "Tải lên các file dữ liệu QuikStrike CSV và File tính toán Event Volatility"
    " để hệ thống tự động phân tích các mốc Strike, biến động sự kiện và biên"
    " độ chạy giá."
)

# ==========================================
# 2. KHU VỰC THANH BÊN (SIDEBAR) - TẢI FILE & CẤU HÌNH
# ==========================================
st.sidebar.header("📁 Tải file dữ liệu lên")
uploaded_gamma = st.sidebar.file_uploader(
    "1. Chọn file Gamma_Exposure.csv", type=["csv"]
)
uploaded_oi = st.sidebar.file_uploader(
    "2. Chọn file Open_Interest.csv", type=["csv"]
)
uploaded_event = st.sidebar.file_uploader(
    "3. Chọn file Event Volatility (.xlsx)", type=["xlsx"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Cấu hình Day Trading & Expected Move")
current_spot = st.sidebar.number_input(
    "Giá Spot tham chiếu (GC1! / XAU):", value=4036.0, step=1.0
)
sigma_event_input = st.sidebar.number_input(
    "Độ biến động sự kiện Sigma Event (%):", value=12.81, step=0.01
)
days_to_expiry = st.sidebar.number_input(
    "Số ngày đến khi đáo hạn/ra tin:", value=1.0, step=0.01
)


# ==========================================
# 3. HÀM LẤY DANH SÁCH CÁC NGÀY CÓ TRONG FILE CSV
# ==========================================
def get_available_dates(file):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)
  date_row = df_raw.iloc[0, :]
  dates = [
      str(val).strip()
      for val in date_row
      if pd.notna(val) and "/" in str(val)
  ]
  return sorted(list(set(dates)), reverse=True)


# ==========================================
# 4. HÀM RÚT DỮ LIỆU OI & GEX THEO ĐÚNG NGÀY ĐƯỢC CHỌN
# ==========================================
def process_quikstrike_by_date(file, target_date):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)

  # Cột 0 chứa các mốc Strike (bắt đầu từ hàng thứ 3 - index 2)
  strike = pd.to_numeric(df_raw.iloc[2:, 0], errors="coerce")

  date_row = df_raw.iloc[0, :]
  c_p_row = df_raw.iloc[1, :]

  call_col_idx = None
  put_col_idx = None

  # Dò chính xác cột Call (C) và Put (P) thuộc ngày target_date
  for col_idx in range(len(date_row)):
    d_val = str(date_row.iloc[col_idx]).strip()
    if d_val == target_date:
      cp_val = str(c_p_row.iloc[col_idx]).strip().upper()
      if cp_val == "C":
        call_col_idx = col_idx
      elif cp_val == "P":
        put_col_idx = col_idx

  # Trích xuất đúng dữ liệu của ngày được chọn
  if call_col_idx is not None and put_col_idx is not None:
    calls = pd.to_numeric(df_raw.iloc[2:, call_col_idx], errors="coerce").fillna(
        0
    )
    puts = pd.to_numeric(df_raw.iloc[2:, put_col_idx], errors="coerce").fillna(0)
  else:
    calls = pd.Series(0, index=df_raw.index[2:])
    puts = pd.Series(0, index=df_raw.index[2:])

  df = pd.DataFrame(
      {"Strike": strike, "Call": calls, "Put": puts}
  ).dropna(subset=["Strike"])
  return df


# ==========================================
# 5. GIAO DIỆN PHÂN TÍCH THEO NGÀY TÙY CHỌN
# ==========================================
selected_date = None
if uploaded_gamma is not None and uploaded_oi is not None:
  dates_gamma = get_available_dates(uploaded_gamma)
  dates_oi = get_available_dates(uploaded_oi)

  # Lấy giao các ngày chung có trong cả 2 file Gamma & OI
  common_dates = sorted(
      list(set(dates_gamma).intersection(set(dates_oi))), reverse=True
  )

  if common_dates:
    selected_date = st.sidebar.selectbox(
        "📅 Chọn Ngày/Tháng/Năm Day Trading:", common_dates
    )

if st.button(
    "🚀 BẮT ĐẦU PHÂN TÍCH THEO NGÀY", type="primary", use_container_width=True
):
  if uploaded_gamma is not None and uploaded_oi is not None and selected_date:
    with st.spinner(
        f"Đang phân tích dữ liệu OI & GEX của ngày {selected_date}..."
    ):
      # 1. Xử lý GEX của ngày được chọn
      df_gex = process_quikstrike_by_date(uploaded_gamma, selected_date)
      gex_c_idx = df_gex["Call"].idxmax()
      gex_p_idx = df_gex["Put"].idxmax()

      gex_call_wall = df_gex.loc[gex_c_idx, "Strike"]
      gex_call_val = df_gex.loc[gex_c_idx, "Call"]
      gex_put_wall = df_gex.loc[gex_p_idx, "Strike"]
      gex_put_val = df_gex.loc[gex_p_idx, "Put"]

      df_gex["Net_GEX"] = (df_gex["Call"] - df_gex["Put"]).abs()
      gamma_flip_strike = df_gex.loc[df_gex["Net_GEX"].idxmin(), "Strike"]

      # 2. Xử lý Open Interest (OI) của ngày được chọn
      df_oi = process_quikstrike_by_date(uploaded_oi, selected_date)
      oi_c_idx = df_oi["Call"].idxmax()
      oi_p_idx = df_oi["Put"].idxmax()

      max_call_strike = df_oi.loc[oi_c_idx, "Strike"]
      max_call_val = df_oi.loc[oi_c_idx, "Call"]
      max_put_strike = df_oi.loc[oi_p_idx, "Strike"]
      max_put_val = df_oi.loc[oi_p_idx, "Put"]

      df_oi["Total_OI"] = df_oi["Call"] + df_oi["Put"]
      tot_idx = df_oi["Total_OI"].idxmax()
      max_tot_strike = df_oi.loc[tot_idx, "Strike"]
      max_tot_val = df_oi.loc[tot_idx, "Total_OI"]

    st.success(f"✅ Đã trích xuất dữ liệu thành công cho ngày: {selected_date}")

    col1, col2 = st.columns(2)
    with col1:
      st.subheader(f"📌 GAMMA EXPOSURE - GEX ({selected_date})")
      st.metric(
          label="GEX Call Wall",
          value=f"{gex_call_wall}",
          delta=f"GEX: {gex_call_val}",
      )
      st.metric(
          label="GEX Put Wall",
          value=f"{gex_put_wall}",
          delta=f"GEX: {gex_put_val}",
      )
      st.metric(label="Gamma Flip / Pinning", value=f"{gamma_flip_strike}")

    with col2:
      st.subheader(f"📌 OPEN INTEREST - OI ({selected_date})")
      st.metric(
          label="Max Call OI",
          value=f"{max_call_strike}",
          delta=f"{max_call_val} HĐ",
      )
      st.metric(
          label="Max Put OI",
          value=f"{max_put_strike}",
          delta=f"{max_put_val} HĐ",
      )
      st.metric(
          label="Max Total OI (Pin)",
          value=f"{max_tot_strike}",
          delta=f"{max_tot_val} HĐ",
      )
  else:
    st.warning("⚠️ Vui lòng tải đủ file CSV và chọn ngày ở Sidebar!")

# ==========================================
# 6. MÔ HÌNH BIẾN ĐỘNG SỰ KIỆN & EXPECTED MOVE
# ==========================================
st.markdown("---")
st.subheader("⚡ MÔ HÌNH TÍNH TOÁN BIẾN ĐỘNG SỰ KIỆN & EXPECTED MOVE")

expected_move_val = (
    current_spot
    * (sigma_event_input / 100.0)
    * math.sqrt(days_to_expiry / 365.0)
)
upper_bound = current_spot + expected_move_val
lower_bound = current_spot - expected_move_val

st.info(
    f"🎯 **Biên độ dự kiến (Expected Move):** $\\pm$ **{expected_move_val:.2f}"
    f" USD** (Vùng giá dao động an toàn: **{lower_bound:.2f}** đến"
    f" **{upper_bound:.2f}**)"
)

if uploaded_event is not None:
  try:
    uploaded_event.seek(0)
    df_event = pd.read_excel(uploaded_event)
    st.dataframe(df_event.dropna(how="all"), use_container_width=True)
  except Exception as e:
    st.error(f"Lỗi đọc file Excel Event Volatility: {e}")
else:
  st.info(
      "ℹ️ Hãy tải lên file Excel `Event Volatility Calculator.xlsx` ở thanh"
      " bên trái để hiển thị bảng dữ liệu sự kiện chi tiết."
  )
