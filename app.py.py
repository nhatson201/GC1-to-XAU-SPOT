import pandas as pd
import streamlit as st

# Cấu hình giao diện trang web
st.set_page_config(
    page_title="Quant Options Web Dashboard", page_icon="📊", layout="centered"
)

st.title("📊 HỆ THỐNG TỰ ĐỘNG XỬ LÝ DỮ LIỆU QUIKSTRIKE")
st.write(
    "Tải lên 2 file CSV của bạn để hệ thống tự động tính toán các mốc Strike và"
    " khối lượng hợp đồng cho TradingView."
)

# 1. Khu vực tải file lên (Upload files)
st.sidebar.header("Tải file dữ liệu lên")
uploaded_gamma = st.sidebar.file_uploader(
    "1. Chọn file Gamma_Exposure.csv", type=["csv"]
)
uploaded_oi = st.sidebar.file_uploader(
    "2. Chọn file Open_Interest.csv", type=["csv"]
)


# Hàm xử lý file QuikStrike giống như code Python trên máy
def process_quikstrike(file):
  df_raw = pd.read_csv(file, header=0)
  strike = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
  call_cols = [i for i in range(1, df_raw.shape[1] - 1) if i % 2 != 0]
  put_cols = [i for i in range(2, df_raw.shape[1] - 1) if i % 2 == 0]
  calls_df = (
      df_raw.iloc[:, call_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
  )
  puts_df = (
      df_raw.iloc[:, put_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
  )
  total_call = calls_df.sum(axis=1)
  total_put = puts_df.sum(axis=1)
  df = pd.DataFrame(
      {"Strike": strike, "Call": total_call, "Put": total_put}
  ).dropna(subset=["Strike"])
  return df


# 2. Nút bấm thực thi
if st.button(
    "🚀 BẮT ĐẦU XỬ LÝ DỮ LIỆU", type="primary", use_container_width=True
):
  if uploaded_gamma is not None and uploaded_oi is not None:
    with st.spinner("Đang phân tích dữ liệu QuikStrike..."):
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

    st.success("✅ Xử lý thành công! Dưới đây là các thông số để nhập TradingView:")

    # Hiển thị kết quả bằng bảng trực quan
    col1, col2 = st.columns(2)

    with col1:
      st.subheader("📌 BẢNG A: GAMMA EXPOSURE")
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
      st.subheader("📌 BẢNG B: OPEN INTEREST")
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
          delta=f"{max_tot_vol} HĐ",
      )

  else:
    st.warning("⚠️ Vui lòng tải lên đầy đủ cả 2 file CSV ở thanh bên trái!")