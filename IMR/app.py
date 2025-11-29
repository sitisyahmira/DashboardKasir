import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os
from dotenv import load_dotenv

#######################################
# PAGE SETUP
#######################################
st.set_page_config(
    page_title="💰 Kasir & Laba Rugi Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💰 Aplikasi Kasir & Analisis Laba Rugi Otomatis")
st.caption("Prototype v2.0 - Rule-based & AI Commentary + Chat Mode")

#######################################
# LOAD API (Optional Groq)
#######################################
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
else:
    client = None

#######################################
# AI Commentary Function
#######################################
def generate_ai_commentary(sales_summary: pd.DataFrame) -> str:
    """Generate AI commentary for profit/loss analysis"""
    if not client:
        return "⚠️ AI Commentary tidak aktif (API Key belum diatur)."

    text_summary = sales_summary.to_string(index=False)
    prompt = f"""
    Berikut data keuntungan tiap barang:
    {text_summary}

    Buat analisis singkat dalam bahasa Indonesia:
    - Barang yang paling menguntungkan
    - Barang yang mengalami kerugian
    - Strategi perbaikan penjualan
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error AI Commentary: {e}"

#######################################
# DATA UPLOAD
#######################################
uploaded_file = st.file_uploader("📂 Upload File Penjualan (Excel/CSV)", type=["xlsx", "xls", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📜 Data Penjualan (Preview)")
    st.dataframe(df.head())

    #######################################
    # DASHBOARD
    #######################################
    st.subheader("📈 Dashboard Keuangan")

    required_cols = ["Nama Barang", "Harga Modal", "Harga Jual", "Jumlah Terjual"]

    if all(col in df.columns for col in required_cols):
        df["Total Modal"] = df["Harga Modal"] * df["Jumlah Terjual"]
        df["Total Penjualan"] = df["Harga Jual"] * df["Jumlah Terjual"]
        df["Keuntungan"] = df["Total Penjualan"] - df["Total Modal"]

        query = """
        SELECT "Nama Barang" AS Barang,
               SUM("Total Modal") AS Total_Modal,
               SUM("Total Penjualan") AS Total_Penjualan,
               SUM("Keuntungan") AS Keuntungan
        FROM df
        GROUP BY "Nama Barang"
        ORDER BY Keuntungan DESC
        """
        summary = duckdb.sql(query).df()

        # Bar chart total penjualan vs modal
        fig = px.bar(summary, x="Barang", y=["Total_Penjualan", "Total_Modal"],
                     barmode="group", title="📊 Perbandingan Modal & Penjualan per Barang")
        st.plotly_chart(fig, use_container_width=True)

        # Chart keuntungan
        fig2 = px.bar(summary, x="Barang", y="Keuntungan", color="Keuntungan",
                      title="💹 Keuntungan per Barang", text_auto=True)
        st.plotly_chart(fig2, use_container_width=True)

        #######################################
        # RULE-BASED COMMENTARY
        #######################################
        st.subheader("📝 Auto Commentary (Rule-based)")

        total_modal = summary["Total_Modal"].sum()
        total_penjualan = summary["Total_Penjualan"].sum()
        total_keuntungan = summary["Keuntungan"].sum()

        best_item = summary.iloc[0]
        worst_item = summary.iloc[-1]

        commentary = f"""
        🔍 **Ringkasan Bisnis:**
        - Total Modal: **Rp {total_modal:,.0f}**
        - Total Penjualan: **Rp {total_penjualan:,.0f}**
        - Total Keuntungan: **Rp {total_keuntungan:,.0f}**

        💰 Barang paling untung: **{best_item['Barang']}** (+Rp {best_item['Keuntungan']:,.0f})  
        ⚠️ Barang paling rugi: **{worst_item['Barang']}** ({worst_item['Keuntungan']:,.0f})
        """

        st.markdown(commentary)

        if total_keuntungan > 0:
            st.success("🎉 Bisnis dalam kondisi **UNTUNG**! Pertahankan strategi penjualan.")
        else:
            st.error("⚠️ Bisnis mengalami **RUGI**. Evaluasi harga jual atau jumlah stok.")

        #######################################
        # AI COMMENTARY
        #######################################
        st.subheader("🤖 AI Commentary")
        ai_text = generate_ai_commentary(summary)
        st.write(ai_text)

        #######################################
        # AI CHAT MODE
        #######################################
        st.subheader("💬 Chat dengan AI Keuangan")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "system", "content": "Anda adalah asisten kasir dan analis keuangan bisnis kecil."},
                {"role": "assistant", "content": ai_text}
            ]

        # tampilkan riwayat chat
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            elif msg["role"] == "assistant":
                st.chat_message("assistant").write(msg["content"])

        # input pertanyaan baru
        if question := st.chat_input("Tanyakan sesuatu tentang laporan keuangan..."):
            st.session_state.chat_history.append({"role": "user", "content": question})
            st.chat_message("user").write(question)

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=st.session_state.chat_history,
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.chat_message("assistant").write(answer)
            except Exception as e:
                st.error(f"❌ Error chat: {e}")

    else:
        st.warning("⚠️ Pastikan file memiliki kolom: Nama Barang, Harga Modal, Harga Jual, dan Jumlah Terjual.")
else:
    st.info("⬆️ Upload file Excel/CSV untuk memulai analisis penjualan.")
