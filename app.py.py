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
    " độ chạy giá theo kỳ hạn DTE."
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
    "Độ biến động sự kiện Sigma Event (%):", value=12.81, step=0.01
)
days_to_expiry = st.sidebar.number_input(
    "Số ngày đến khi đáo hạn/ra tin:", value=1.0, step=0.01
)


# ==========================================
# 3. HÀM TRÍCH XUẤT DANH SÁCH DTE / NGÀY TỪ FILE
# ==========================================
def get_available_options(file, is_gamma=True):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)
  options = []
  if is_gamma:
    # Gamma_Exposure có dòng 1 chứa DTE (VD: '1 DTE', '5 DTE'...)
    row_dte = df_raw.iloc[1, :]
    options = [
        str(val).strip()
        for val in row_dte
        if pd.notna(val) and "DTE" in str(val).upper()
    ]
  else:
    # Open_Interest có dòng 0 chứa Ngày (VD: '21/10/2026'...)
    row_date = df_raw.iloc[0, :]
    options = [
        str(val).strip() for val in row_date if pd.notna(val) and "/" in str(val)
    ]
  return sorted(list(set(options)))


# ==========================================
# 4. HÀM XỬ LÝ DỮ LIỆU THEO LỰA CHỌN DTE / NGÀY
# ==========================================
def process_quikstrike_by_selection(file, target_val, is_gamma=True):
  file.seek(0)
  df_raw = pd.read_csv(file, header=None)

  strike = pd.to_numeric(df_raw.iloc[3:, 0], errors="coerce")

  call_col_idx = None
  put_col_idx = None

  if is_gamma:
    row_header = df_raw.iloc[1, :]  # Dòng chứa DTE
    row_cp = df_raw.iloc[2, :]  # Dòng chứa C/P
    for col_idx in range(len(row_header)):
      if str(row_header.iloc[col_idx]).strip() == target_val:
        # Tìm cột C và P kế tiếp
        for c_idx in range(col_idx, len(row_cp)):
          cp = str(row_cp.iloc[c_idx]).strip().upper()
          if cp == "C" and call_col_idx is None:
            call_col_idx = c_idx
          elif cp == "P" and put_col_idx is None:
            put_col_idx = c_idx
            break
        break
  else:
    row_header = df_raw.iloc[0, :]  # Dòng chứa Ngày
    row_cp = df_raw.iloc[1, :]  # Dòng chứa C/P
    for col_idx in range(len(row_header)):
      if str(row_header.iloc[col_idx]).strip() == target_val:
        for c_idx in range(col_idx, len(row_cp)):
          cp = str(row_cp.iloc[c_idx]).strip().upper()
          if cp == "C" and call_col_idx is None:
            call_col_idx = c_idx
          elif cp == "P" and put_col_idx is None:
            put_col_idx = c_idx
            break
        break

  if call_col_idx is not None and put_col_idx is not None:
    calls = pd.to_numeric(df_raw.iloc[3:, call_col_idx], errors="coerce").fillna(
        0
    )
    puts = pd.to_numeric(df_raw.iloc[3:, put_col_idx], errors="coerce").fillna(0)
  else:
    calls = pd.Series(0, index=df_raw.index[3:])
    puts = pd.Series(0, index=df_raw.index[3:])

  df = pd.DataFrame(
      {"Strike": strike, "Call": calls, "Put": puts}
  ).dropna(subset=["Strike"])
  return df


# ==========================================
# 5. GIAO DIỆN LỰA CHỌN DTE VÀ PHÂN TÍCH
# ==========================================
selected_dte = None
selected_oi_date = None

if uploaded_gamma is not None:
  dte_list = get_available_options(uploaded_gamma, is_gamma=True)
  if dte_list:
    selected_dte = st.sidebar.selectbox("⏳ Chọn Kỳ hạn DTE (Gamma):", dte_list)

if uploaded_oi is not None:
  oi_date_list = get_available_options(uploaded_oi, is_gamma=False)
  if oi_date_list:
    selected_oi_date = st.sidebar.selectbox(
        "📅 Chọn Ngày (Open Interest):", oi_date_list
    )

if st.button(
    "🚀 BẮT ĐẦU PHÂN TÍCH THEO KỲ HẠN DTE",
    type="primary",
    use_container_width=True,
):
  if (
      uploaded_gamma is not None
      and uploaded_oi is not None
      and selected_dte
      and selected_oi_date
  ):
    with st.spinner(
        f"Đang xử lý dữ liệu Gamma (DTE: {selected_dte}) và OI (Ngày:"
        f" {selected_oi_date})..."
    ):
      # 1. Xử lý Gamma theo DTE chọn
      df_gex = process_quikstrike_by_selection(
          uploaded_gamma, selected_dte, is_gamma=True
      )
      gex_c_idx = df_gex["Call"].idxmax()
      gex_p_idx = df_gex["Put"].idxmax()

      gex_call_wall = df_gex.loc[gex_c_idx, "Strike"]
      gex_call_val = df_gex.loc[gex_c_idx, "Call"]
      gex_put_wall = df_gex.loc[gex_p_idx, "Strike"]
      gex_put_val = df_gex.loc[gex_p_idx, "Put"]

      df_gex["Net_GEX"] = (df_gex["Call"] - df_gex["Put"]).abs()
      gamma_flip_strike = df_gex.loc[df_gex["Net_GEX"].idxmin(), "Strike"]

      # 2. Xử lý OI theo ngày chọn
      df_oi = process_quikstrike_by_selection(
          uploaded_oi, selected_oi_date, is_gamma=False
      )
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

    st.success(
        f"✅ Phân tích thành công! (Gamma DTE: **{selected_dte}** | OI Ngày:"
        f" **{selected_oi_date}**)"
    )

    col1, col2 = st.columns(2)
    with col1:
      st.subheader(f"📌 GAMMA EXPOSURE (Kỳ hạn: {selected_dte})")
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
      st.subheader(f"📌 OPEN INTEREST (Ngày: {selected_oi_date})")
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
    st.warning("⚠️ Vui lòng tải đủ file CSV và chọn các thông số ở Sidebar!")

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
