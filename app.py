import streamlit as st
import pandas as pd
import random
from streamlit_mic_recorder import speech_to_text

# --- ページ設定 ---
st.set_page_config(page_title="AI配車アシスタント - デモ", layout="wide")

st.title("🚛 配車最適化AIアシスタント (Prototype)")
st.markdown("現場の状況とスタッフの相性を考慮し、最適なルートを瞬時に提案します。")

# --- 1. データ生成セクション (架空データの準備) ---
def generate_dummy_data():
    staff_data = [
        {"名前": "佐藤(A)", "スキル": "ベテラン", "性格": "慎重・確実", "苦手": "特になし", "希望": "件数を稼ぎたい"},
        {"名前": "鈴木(B)", "スキル": "中堅", "性格": "社交的", "苦手": "事務作業", "希望": "遠距離は避けたい"},
        {"名前": "田中(C)", "スキル": "新人", "性格": "内向的", "苦手": "厳しい管理人", "希望": "メンター同行希望"}
    ]
    locations = ["青葉区マンション", "中央ビル", "港北倉庫", "緑区役所", "南ショッピングモール"]
    difficulties = ["低", "中", "高(要交渉)"]
    stress_levels = ["普通", "高い(管理人が厳しい)", "低い"]
    
    site_data = []
    for loc in locations:
        site_data.append({
            "現場名": loc,
            "作業難易度": random.choice(difficulties),
            "対人ストレス": random.choice(stress_levels),
            "所要時間(分)": random.choice([30, 60, 90, 120])
        })
    return pd.DataFrame(staff_data), pd.DataFrame(site_data)

if 'df_staff' not in st.session_state:
    st.session_state.df_staff, st.session_state.df_site = generate_dummy_data()

# --- 2. データの可視化 (Expanderで開閉可能に) ---
with st.expander("📋 【参照データ】現在の要員リストと現場リストを見る (タップして展開)"):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("現在の要員 (Staff)")
        st.dataframe(st.session_state.df_staff, hide_index=True)
    with col2:
        st.subheader("本日の現場 (Sites)")
        st.dataframe(st.session_state.df_site, hide_index=True)
    
    if st.button("🔄 データをランダム更新"):
        st.session_state.df_staff, st.session_state.df_site = generate_dummy_data()
        st.rerun()

# --- 3. AIロジック ---
def get_ai_response(user_instruction, api_key):
    # データフレームをテキスト化
    staff_text = st.session_state.df_staff.to_json(orient="records", force_ascii=False)
    site_text = st.session_state.df_site.to_json(orient="records", force_ascii=False)

    system_prompt = f"""
    あなたは熟練の配車担当者です。以下のデータを元に、指示に従って人員配置を行ってください。
    
    # ルール
    - 新人(田中)には「対人ストレス:高い」「難易度:高」を避ける。
    - ベテラン(佐藤)には難所を優先的に割り当てる。
    - ユーザーの指示(体調、天候など)を最優先する。
    
    # データ
    [社員]: {staff_text}
    [現場]: {site_text}
    """

    if not api_key:
        import time
        time.sleep(1.5)
        return f"""
**(模擬モード回答)**
指示: 「{user_instruction}」に基づき配置しました。

**🚚 配置案:**
* **佐藤(A)**: 中央ビル (難易度:高) - ベテランの対応力を活かします。
* **鈴木(B)**: 港北倉庫、南モール - 移動効率重視でセットにしました。
* **田中(C)**: 青葉区マンション - 管理人が厳しくないため、新人の田中さんでも安心です。
        """
    else:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_instruction}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"エラー: {str(e)}"

# --- 4. メインインターフェース ---
st.divider()

# サイドバーにAPIキー設定
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    st.info("APIキーがない場合は模擬モードで動きます")

# チャット履歴の表示
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "おはようございます。本日の配置指示をどうぞ。（音声入力も可能です）"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 入力エリア (ワンタップボタン & 音声 & テキスト) ---
st.write("### 👇 指示を入力 (タップまたは音声)")

# ワンタップ入力ボタン
col_btn1, col_btn2, col_btn3 = st.columns(3)
user_input = None

with col_btn1:
    if st.button("☔️ 雨天・安全重視モード"):
        user_input = "今日は雨だから、全員移動距離を短くして、安全優先のルートで組んで。"
with col_btn2:
    if st.button("🔰 新人(田中)ケアモード"):
        user_input = "田中くんはまだ不慣れだから、一番簡単な現場1件だけにして。残りはベテランでカバーして。"
with col_btn3:
    if st.button("⚡️ トラブル対応モード"):
        user_input = "佐藤さんが急なクレーム対応で遅れる。佐藤さんの現場を1つ減らして、鈴木さんに回して。"

# 音声入力
st.write("🎙 **音声で指示する:**")
audio_text = speech_to_text(language='ja', start_prompt="録音開始 (押して喋る)", stop_prompt="録音終了 (もう一度押す)", just_once=True)

if audio_text:
    user_input = audio_text

# テキスト入力 (チャットバー)
chat_input_text = st.chat_input("キーボードで指示を入力...")
if chat_input_text:
    user_input = chat_input_text

# --- 処理実行 ---
if user_input:
    # ユーザーの発言を表示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # AIの回答生成
    with st.chat_message("assistant"):
        with st.spinner("ベテランAIが思考中..."):
            response = get_ai_response(user_input, openai_api_key)
            st.write(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # 処理が終わったらリランして表示を更新（ボタンの連続押し等を防ぐため）
    st.rerun()
