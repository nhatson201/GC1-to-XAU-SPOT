import pandas as pd
import streamlit as st

# Cấu hình giao diện trang web
st.set_page_config(
    page_title="Quant Options Web Dashboard", page_icon="📊", layout="wide"
)

st.title("📊 HỆ THỐNG TỰ ĐỘNG XỬ LÝ DỮ LIỆU QUIKSTRIKE & EVENT VOLATILITY")
st.write(
    "Tải lên các file dữ liệu QuikStrike CSV và File tính toán Event Volatility"
    " để hệ thống tự động phân tích các mốc Strike, biến động sự kiện và biên"
    " độ chạy giá."
)

# 1. Khu vực tải file lên (Upload files) ở Sidebar
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


# Hàm xử lý file QuikStrike CSV
def process_quikstrike(file):
  df_raw = pd.read_csv(file, header=0)
  strike = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
  call_cols = [i for i in range(1, df_raw.shape[1] - 1) if i % 2 != 0]
  put_cols = [i for i in range(2, df_raw.shape[1] - 1) if i % 2 == 0]
  calls_df = (
      df_raw.iloc[:, call_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
  )
  puts_df = (
      df_raw.iloc[:, put_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
  )
  total_call = calls_df.sum(axis=1)
  total_put = puts_df.sum(axis=1)
  df = pd.DataFrame(
      {"Strike": strike, "Call": total_call, "Put": total_put}
  ).dropna(subset=["Strike"])
  return df


# 2. Nút bấm thực thi chính
if st.button(
    "🚀 BẮT ĐẦU PHÂN TÍCH QUANTRIC", type="primary", use_container_width=True
):

  # Xử lý phần QuikStrike GEX & OI
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

    # Hiển thị kết quả Options qua các cột giao diện
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
        " `Open_Interest.csv` để hiển thị phần QuikStrike!"
    )

  # Xử lý phần Event Volatility Calculator mở rộng
  if uploaded_event is not None:
    st.markdown("---")
    st.subheader("⚡ MÔ HÌNH TÍNH TOÁN BIẾN ĐỘNG SỰ KIỆN (EVENT VOLATILITY)")
    try:
      df_event = pd.read_excel(uploaded_event)
      st.dataframe(df_event.dropna(how="all"), use_container_width=True)
      st.info(
          "💡 **Gợi ý Quant:** Sử dụng các thông số $\\sigma_{\\text{EVENT}}$ từ"
          " bảng trên để đánh giá mức độ co giãn phí quyền chọn trước và sau"
          " tin tức lớn (như FOMO, CPI, NFP), phục vụ chiến lược quản trị rủi"
          " ro hoặc giao dịch biên độ breakout cho XAU/USD."
      )
    except Exception as e:
      st.error(f"Lỗi đọc file Excel Event Volatility: {e}")
  else:
    st.markdown("---")
    st.info(
        "ℹ️ Bạn có thể tải lên file Excel `Event Volatility Calculator.xlsx` ở"
        " thanh bên trái để hiển thị bảng phân tích độ biến động sự kiện."
    )
