import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="바이크 정비노트(Cloud)", page_icon="🏍️", layout="wide")
st.title("🏍️ 마이 바이크 정비노트 (Cloud Ver.)")

# --- 구글 시트 연결 함수 (캐싱으로 속도 향상) ---
@st.cache_resource
def get_google_sheet():
    # Streamlit Secrets에서 키 정보 가져오기
    try:
        credentials = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials)
        sh = gc.open("오토바이_정비내역") # 구글 시트 파일 이름
        return sh.sheet1
    except Exception as e:
        st.error(f"구글 시트 연결 실패! Secrets 설정을 확인하세요. 오류: {e}")
        return None

# --- 탭 구성 ---
tab1, tab2 = st.tabs(["📝 정비 입력", "📋 전체 내역 조회"])

# ==========================================
# [탭 1] 입력하기
# ==========================================
with tab1:
    st.subheader("새로운 정비 내용 추가")

    with st.form(key='maintenance_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("정비 날짜", datetime.now())
            bike_model = st.text_input("차종", value="존테스 350D")
        with col2:
            mileage = st.number_input("주행 거리 (km)", step=100)
            cost = st.number_input("비용 (원)", step=1000)

        category = st.selectbox("정비 항목", ["엔진오일", "타이어", "브레이크", "구동계", "전기장치", "기타", "주유"])
        details = st.text_area("상세 내용", height=80)
        
        submit_button = st.form_submit_button(label='☁️ 구글 시트에 저장', use_container_width=True)

    if submit_button:
        sheet = get_google_sheet()
        if sheet:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 날짜를 문자열로 변환하여 저장
            date_str = date.strftime("%Y-%m-%d")
            
            row_data = [date_str, bike_model, mileage, category, details, cost, current_time]
            
            try:
                sheet.append_row(row_data)
                st.success("✅ 구글 시트에 안전하게 저장되었습니다!")
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

# ==========================================
# [탭 2] 조회하기
# ==========================================
with tab2:
    st.subheader("📋 실시간 정비 대장")
    
    if st.button("🔄 새로고침"):
        st.cache_data.clear() # 데이터 캐시 초기화
        
    sheet = get_google_sheet()
    if sheet:
        try:
            # 모든 기록 가져오기
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # 데이터 가공
                if '날짜' in df.columns:
                    df = df.sort_values(by='날짜', ascending=False)
                
                # 통계
                total_cost = df['비용(원)'].sum() if '비용(원)' in df.columns else 0
                total_count = len(df)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("총 비용", f"{total_cost:,.0f}원")
                m2.metric("총 횟수", f"{total_count}회")
                
                st.divider()
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("아직 데이터가 없습니다.")
                
        except Exception as e:
            st.warning("데이터를 불러오는 중입니다. (헤더가 없거나 비어있을 수 있음)")
