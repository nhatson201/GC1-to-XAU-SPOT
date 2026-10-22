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
st.sidebar.header("⚙️ Cấu hình Expected Move")
current_spot = st.sidebar.number_input(
    "Giá Spot tham chiếu (GC1! / XAU):", value=4036.0, step=1.0
)
sigma_event_input = st.sidebar.number_input(
    "Độ biến động sự kiện Sigma Event (%):", value=15.0, step=0.5
)
days_to_expiry = st.sidebar.number_input(
    "Số ngày đến khi đáo hạn/ra tin:", value=1.0, step=0.5
)


# ==========================================
# 3. HÀM XỬ LÝ DỮ LIỆU QUIKSTRIKE CSV (Định dạng văn bản động C/P)
# ==========================================
def process_quikstrike(file):
  # Đọc toàn bộ dữ liệu thô không có header cố định
  df_raw = pd.read_csv(file, header=None)

  # Cột 0 là mốc Strike (bắt đầu từ hàng thứ 3 - index 2)
  strike = pd.to_numeric(df_raw.iloc[2:, 0], errors="coerce")

  # Tự động tìm hàng chứa ký hiệu 'C' và 'P' (hàng index 1)
  c_p_row = df_raw.iloc[1, 1:]

  call_col_indices = [
      i + 1
      for i, val in enumerate(c_p_row)
      if str(val).strip().upper() == "C"
  ]
  put_col_indices = [
      i + 1
      for i, val in enumerate(c_p_row)
      if str(val).strip().upper() == "P"
  ]

  # Trích xuất và ép kiểu số toàn bộ dữ liệu Call & Put
  calls_df = (
      df_raw.iloc[2:, call_col_indices]
      .apply(pd.to_numeric, errors="coerce")
      .fillna(0)
  )
  puts_df = (
      df_raw.iloc[2:, put_col_indices]
      .apply(pd.to_numeric, errors="coerce")
      .fillna(0)
  )

  total_call = calls_df.sum(axis=1)
  total_put = puts_df.sum(axis=1)

  df = pd.DataFrame(
      {"Strike": strike, "Call": total_call, "Put": total_put}
  ).dropna(subset=["Strike"])
  return df


# ==========================================
# 4. KHU VỰC PHÂN TÍCH QUIKSTRIKE (GEX & OI)
# ==========================================
if st.button(
    "🚀 BẮT ĐẦU PHÂN TÍCH QUIKSTRIKE", type="primary", use_container_width=True
):
  if uploaded_gamma is not None and uploaded_oi is not None:
    with st.spinner("Đang xử lý ma trận Options QuikStrike..."):
      # Xử lý GEX
      df_gex = process_quikstrike(uploaded_gamma)
      gex_c_idx = df_gex["Call"].idxmax()
      gex_p_idx = df_gex["Put"].idxmax()

      gex_call_wall = df_gex.loc[gex_c_idx, "Strike"]
      gex_call_val = df_gex.loc[gex_c_idx, "Call"]
      gex_put_wall = df_gex.loc[gex_p_idx, "Strike"]
      gex_put_val = df_gex.loc[gex_p_idx, "Put"]

      df_gex["Net_GEX"] = (df_gex["Call"] - df_gex["Put"]).abs()
      gamma_flip_strike = df_gex.loc[df_gex["Net_GEX"].idxmin(), "Strike"]

      # Xử lý OI
      df_oi = process_quikstrike(uploaded_oi)
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

    st.success("✅ Phân tích QuikStrike thành công!")

    col1, col2 = st.columns(2)
    with col1:
      st.subheader("📌 BẢNG A: GAMMA EXPOSURE (GEX)")
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
      st.subheader("📌 BẢNG B: OPEN INTEREST (OI)")
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
    st.warning(
        "⚠️ Vui lòng tải lên cả 2 file `Gamma_Exposure.csv` và"
        " `Open_Interest.csv` ở thanh bên trái!"
    )

# ==========================================
# 5. KHU VỰC MÔ HÌNH BIẾN ĐỘNG SỰ KIỆN & EXPECTED MOVE
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
    df_event = pd.read_excel(uploaded_event)
    st.dataframe(df_event.dropna(how="all"), use_container_width=True)
  except Exception as e:
    st.error(f"Lỗi đọc file Excel Event Volatility: {e}")
else:
  st.info(
      "ℹ️ Hãy tải lên file Excel `Event Volatility Calculator.xlsx` ở thanh"
      " bên trái để hiển thị bảng dữ liệu sự kiện chi tiết."
  )
