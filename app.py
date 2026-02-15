import streamlit as st
import pandas as pd
import json
import random

# --- ページ設定 ---
st.set_page_config(page_title="AI配車アシスタント - デモ", layout="wide")

st.title("🚛 配車最適化AIアシスタント (Prototype)")
st.markdown("""
このデモは、**「ベテラン配車担当者の頭の中（判断ロジック）」**をAIに移植し、
自然言語の指示で最適なルート組みを提案させるプロトタイプです。
""")

# --- 1. データ生成セクション (架空データの準備) ---
def generate_dummy_data():
    # 社員データ
    staff_data = [
        {"名前": "佐藤(A)", "スキル": "ベテラン", "性格": "慎重・確実", "苦手": "特になし", "希望": "件数を稼ぎたい"},
        {"名前": "鈴木(B)", "スキル": "中堅", "性格": "社交的", "苦手": "事務作業", "希望": "遠距離は避けたい"},
        {"名前": "田中(C)", "スキル": "新人", "性格": "内向的", "苦手": "厳しい管理人", "希望": "メンター同行希望"}
    ]
    
    # 現場データ
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

# セッション状態にデータを保持
if 'df_staff' not in st.session_state:
    st.session_state.df_staff, st.session_state.df_site = generate_dummy_data()

# --- サイドバー: データ確認と設定 ---
with st.sidebar:
    st.header("🛠️ 設定・データ確認")
    openai_api_key = st.text_input("OpenAI API Key (未入力なら模擬モード)", type="password")
    
    st.subheader("📋 現在の要員リスト")
    st.dataframe(st.session_state.df_staff, hide_index=True)
    
    st.subheader("📍 今日の現場リスト")
    st.dataframe(st.session_state.df_site, hide_index=True)
    
    if st.button("データを再生成する"):
        st.session_state.df_staff, st.session_state.df_site = generate_dummy_data()
        st.rerun()

# --- 2. AIロジック定義 (ここが「ベテランの脳内」) ---
def get_ai_response(user_instruction, df_staff, df_site, api_key):
    # データフレームをテキスト(JSON/CSV)に変換してプロンプトに埋め込む
    staff_text = df_staff.to_json(orient="records", force_ascii=False)
    site_text = df_site.to_json(orient="records", force_ascii=False)

    # システムプロンプト：ベテラン配車係の役割定義
    system_prompt = f"""
    あなたは熟練の配車担当者です。以下の「社員データ」と「現場データ」をもとに、
    ユーザーの指示に従って最適な人員配置（ルート組み）を提案してください。
    
    # 判断基準
    1. 新人や内向的な社員には「対人ストレス」が高い現場（管理人が厳しい等）を避ける。
    2. ベテランには難易度が高い現場や、件数を多く割り当てる。
    3. ユーザーからの特記事項（体調不良など）を最優先する。
    
    # 出力形式
    提案は以下のフォーマットで行ってください。
    - **配置案の概要**: なぜこの配置にしたかの全体的な理由
    - **個別割り当て**:
      - [社員名]: [担当現場名] (理由: ...)
    
    # データ
    [社員リスト]: {staff_text}
    [現場リスト]: {site_text}
    """

    if not api_key:
        # APIキーがない場合の模擬レスポンス (Mock)
        import time
        time.sleep(2) # 思考時間を演出
        return f"""
**(模擬モードでの回答です)**
承知いたしました。ご指示の「{user_instruction}」を考慮し、以下の配置を提案します。

**配置案の概要:**
{user_instruction[:10]}... という点を重視し、田中(C)さんには心理的負担の少ない現場を、佐藤(A)さんには難所を任せる構成にしました。

**個別割り当て:**
* **佐藤(A)**: 中央ビル、緑区役所
    * *理由*: 難易度「高」の現場ですが、ベテランの佐藤さんなら確実に対応可能です。
* **鈴木(B)**: 港北倉庫、南ショッピングモール
    * *理由*: 移動距離を考慮し、近隣エリアでまとめました。
* **田中(C)**: 青葉区マンション
    * *理由*: 内向的な性格を考慮し、対人ストレスが「低い」現場を選定しました。指示通り無理のない配置です。
        """
    
    else:
        # 実際にOpenAI APIを叩く
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # コスト重視で3.5、精度重視ならgpt-4
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_instruction}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

# --- 3. メインチャットインターフェース ---
st.subheader("💬 AI配車アシスタントへの指示")

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "おはようございます。本日の配置はどうしますか？「田中さんは今日メンタル不調なので優しめで」のように指示してください。"}]

# チャット履歴の表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ユーザー入力
if prompt := st.chat_input("指示を入力してください..."):
    # ユーザーの入力を表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # AIの思考中表示
    with st.chat_message("assistant"):
        with st.spinner("ベテランの思考ロジックで検討中..."):
            response = get_ai_response(
                prompt, 
                st.session_state.df_staff, 
                st.session_state.df_site, 
                openai_api_key
            )
            st.write(response)
            
            # 「裏側のプロンプト」を見せる（デモ効果用）
            with st.expander("👀 AIが見ているデータと指示（プロンプトの中身）"):
                st.code(f"User Instruction: {prompt}\n\nData Context Used:\nStaff: {len(st.session_state.df_staff)} records\nSites: {len(st.session_state.df_site)} records", language="yaml")
    
    st.session_state.messages.append({"role": "assistant", "content": response})