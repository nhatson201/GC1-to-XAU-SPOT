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
    "Hệ thống tự động trích xuất dữ liệu theo Mã kỳ hạn / Contract / DTE một cách"
    " trực tiếp và tối ưu."
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
st.sidebar.header("⚡ Cấu hình Kỳ hạn & Expected Move")
current_spot = st.sidebar.number_input(
    "Giá Spot tham chiếu (GC1! / XAU):", value=4036.0, step=1.0
)
sigma_event_input = st.sidebar.number_input(
    "Độ biến động sự kiện Sigma Event (%):", value=21.12, step=0.01
)
days_to_expiry = st.sidebar.number_input(
    "Số ngày đến khi ra tin (DTE):", value=0.04, step=0.01
)


# ==========================================
# 3. HÀM TỰ ĐỘNG LẤY DANH SÁCH MÃ KỲ HẠN / DTE
# ==========================================
def get_available_contracts(file):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)
  contracts = []
  # Quét 2 dòng đầu để tìm mã hợp đồng hoặc DTE
  for r in range(min(2, len(df_raw))):
    for val in df_raw.iloc[r, :]:
      v_str = str(val).strip()
      if (
          pd.notna(val)
          and v_str.upper() != "STRIKE"
          and v_str != ""
          and v_str != "nan"
      ):
        if v_str not in contracts:
          contracts.append(v_str)
  return contracts


# ==========================================
# 4. HÀM XỬ LÝ DỮ LIỆU LINH HOẠT THEO MÃ KỲ HẠN
# ==========================================
def process_quikstrike_flexible(file, target_contract):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)

  # Tự động tìm dòng chứa dữ liệu Strike (cột đầu tiên là số)
  start_row = 3
  for r in range(len(df_raw)):
    val = str(df_raw.iloc[r, 0]).strip()
    if val.replace(".", "", 1).isdigit():
      start_row = r
      break

  strike = pd.to_numeric(df_raw.iloc[start_row:, 0], errors="coerce")

  call_col_idx = None
  put_col_idx = None

  # Dò tìm vị trí cột chứa target_contract và các cột C/P đi kèm
  for r in range(min(3, len(df_raw))):
    for col_idx in range(len(df_raw.columns)):
      cell_val = str(df_raw.iloc[r, col_idx]).strip()
      if cell_val == target_contract:
        for c_idx in range(col_idx, min(col_idx + 6, len(df_raw.columns))):
          cp_val = str(df_raw.iloc[r + 1 if r + 1 < len(df_raw) else r, c_idx]).strip().upper()
          if cp_val == "C" and call_col_idx is None:
            call_col_idx = c_idx
          elif cp_val == "P" and put_col_idx is None:
            put_col_idx = c_idx
            break
        break
    if call_col_idx is not None:
      break

  # Nếu không tìm thấy chính xác, lấy mặc định cột 1 (Call) và cột 2 (Put)
  if call_col_idx is None or put_col_idx is None:
    call_col_idx = 1
    put_col_idx = 2

  calls = pd.to_numeric(df_raw.iloc[start_row:, call_col_idx], errors="coerce").fillna(0)
  puts = pd.to_numeric(df_raw.iloc[start_row:, put_col_idx], errors="coerce").fillna(0)

  df = pd.DataFrame({"Strike": strike, "Call": calls, "Put": puts}).dropna(subset=["Strike"])
  return df


# ==========================================
# 5. GIAO DIỆN LỰA CHỌN & PHÂN TÍCH
# ==========================================
selected_gamma_contract = None
selected_oi_contract = None

if uploaded_gamma is not None:
  gamma_list = get_available_contracts(uploaded_gamma)
  if gamma_list:
    selected_gamma_contract = st.sidebar.selectbox("⏳ Chọn Kỳ hạn Gamma (Contract/DTE):", gamma_list)

if uploaded_oi is not None:
  oi_list = get_available_contracts(uploaded_oi)
  if oi_list:
    selected_oi_contract = st.sidebar.selectbox("📊 Chọn Kỳ hạn Open Interest (Contract/DTE):", oi_list)

if st.button("🚀 BẮT ĐẦU PHÂN TÍCH", type="primary", use_container_width=True):
  if uploaded_gamma is not None and uploaded_oi is not None and selected_gamma_contract and selected_oi_contract:
    with st.spinner("Đang xử lý dữ liệu..."):
      # Xử lý Gamma
      df_gex = process_quikstrike_flexible(uploaded_gamma, selected_gamma_contract)
      gex_c_idx = df_gex["Call"].idxmax()
      gex_p_idx = df_gex["Put"].idxmax()
      gex_call_wall = df_gex.loc[gex_c_idx, "Strike"]
      gex_call_val = df_gex.loc[gex_c_idx, "Call"]
      gex_put_wall = df_gex.loc[gex_p_idx, "Strike"]
      gex_put_val = df_gex.loc[gex_p_idx, "Put"]

      df_gex["Net_GEX"] = (df_gex["Call"] - df_gex["Put"]).abs()
      gamma_flip_strike = df_gex.loc[df_gex["Net_GEX"].idxmin(), "Strike"]

      # Xử lý Open Interest
      df_oi = process_quikstrike_flexible(uploaded_oi, selected_oi_contract)
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

    st.success("✅ Phân tích định lượng thành công!")

    col1, col2 = st.columns(2)
    with col1:
      st.subheader(f"📌 GAMMA ({selected_gamma_contract})")
      st.metric(label="GEX Call Wall", value=f"{gex_call_wall}", delta=f"GEX: {gex_call_val}")
      st.metric(label="GEX Put Wall", value=f"{gex_put_wall}", delta=f"GEX: {gex_put_val}")
      st.metric(label="Gamma Flip / Pinning", value=f"{gamma_flip_strike}")

    with col2:
      st.subheader(f"📌 OPEN INTEREST ({selected_oi_contract})")
      st.metric(label="Max Call OI", value=f"{max_call_strike}", delta=f"{max_call_val} HĐ")
      st.metric(label="Max Put OI", value=f"{max_put_strike}", delta=f"{max_put_val} HĐ")
      st.metric(label="Max Total OI (Pin)", value=f"{max_tot_strike}", delta=f"{max_tot_val} HĐ")
  else:
    st.warning("⚠️ Vui lòng tải đủ file CSV và chọn thông số kỳ hạn ở Sidebar!")

# ==========================================
# 6. MÔ HÌNH EXPECTED MOVE
# ==========================================
st.markdown("---")
st.subheader("⚡ MÔ HÌNH BIẾN ĐỘNG SỰ KIỆN & EXPECTED MOVE")
expected_move_val = current_spot * (sigma_event_input / 100.0) * math.sqrt(days_to_expiry / 365.0)
upper_bound = current_spot + expected_move_val
lower_bound = current_spot - expected_move_val

st.info(f"🎯 **Biên độ dự kiến (Expected Move):** $\\pm$ **{expected_move_val:.2f} USD** (Vùng an toàn: **{lower_bound:.2f}** đến **{upper_bound:.2f}**)")

if uploaded_event is not None:
  try:
    uploaded_event.seek(0)
    df_event = pd.read_excel(uploaded_event)
    st.dataframe(df_event.dropna(how="all"), use_container_width=True)
  except Exception as e:
    st.error(f"Lỗi đọc file Excel: {e}")
