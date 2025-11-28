import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. 엑셀 파일 이름 설정
FILE_NAME = '오토바이_정비내역.xlsx'

# 2. 제목 및 설명
st.title("🏍️ 오토바이 정비내역 기록장")
st.write("핸드폰에서 내용을 입력하고 '저장'을 누르면 엑셀에 기록됩니다.")

# 3. 입력 폼 만들기
with st.form(key='maintenance_form'):
    date = st.date_input("정비 날짜", datetime.now())
    bike_model = st.text_input("차종 (예: 존테스 350D)")
    mileage = st.number_input("주행 거리 (km)", min_value=0, step=100)
    category = st.selectbox("정비 항목", ["엔진오일", "타이어", "브레이크 패드", "구동계", "기타 정비", "튜닝/액세서리"])
    details = st.text_area("상세 정비 내용")
    cost = st.number_input("비용 (원)", min_value=0, step=1000)
    
    # 저장 버튼
    submit_button = st.form_submit_button(label='엑셀에 저장하기')

# 4. 저장 버튼을 눌렀을 때 작동하는 로직
if submit_button:
    # 새로운 데이터 딕셔너리 생성
    new_data = {
        '날짜': [date],
        '차종': [bike_model],
        '주행거리(km)': [mileage],
        '항목': [category],
        '내용': [details],
        '비용(원)': [cost],
        '기록일시': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    
    new_df = pd.DataFrame(new_data)

    # 엑셀 파일이 이미 있으면 불러와서 합치고, 없으면 새로 만듦
    if os.path.exists(FILE_NAME):
        try:
            existing_df = pd.read_excel(FILE_NAME)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_excel(FILE_NAME, index=False)
            st.success(f"✅ 저장 완료! ({FILE_NAME})")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
    else:
        new_df.to_excel(FILE_NAME, index=False)
        st.success(f"✅ 파일 생성 및 저장 완료! ({FILE_NAME})")

    # 저장된 데이터 미리보기
    if os.path.exists(FILE_NAME):
        st.subheader("📊 최근 기록 내역")
        df_view = pd.read_excel(FILE_NAME)
        st.dataframe(df_view.tail(5)) # 최근 5개만 보여주기