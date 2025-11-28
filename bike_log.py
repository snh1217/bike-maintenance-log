import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 페이지 및 기본 설정 (제목 변경 완료)
# --------------------------------------------------------------------------
st.set_page_config(page_title="개인 정비노트", page_icon="🏍️", layout="wide")
st.title("🏍️ 개인 정비노트")

# --------------------------------------------------------------------------
# 2. 구글 시트 연결 함수
# --------------------------------------------------------------------------
@st.cache_resource
def get_google_sheet():
    try:
        credentials = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials)
        sh = gc.open("오토바이_정비내역") 
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ 구글 시트 연결 실패! 오류 내용: {e}")
        return None

# --------------------------------------------------------------------------
# 3. 탭 구성
# --------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📝 정비 입력", "📋 전체 내역 조회"])

# ==========================================================================
# [탭 1] 새로운 정비 내용 입력
# ==========================================================================
with tab1:
    st.subheader("새로운 정비 내용 추가")

    # 폼(Form) 시작
    with st.form(key='maintenance_form', clear_on_submit=True):
        
        # 1행: 날짜 / 차종
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("정비 날짜", datetime.now())
            bike_model = st.text_input("차종", value="존테스 350D")
        with col2:
            mileage = st.number_input("주행 거리 (km)", step=100)
            cost = st.number_input("비용 (원)", step=1000)

        st.divider() # 구분선

        # --- 스마트 항목 선택 로직 (자동 감지) ---
        st.caption("👇 항목을 선택하거나, 직접 입력하고 싶으면 아래 빈칸에 바로 적으세요.")
        
        c1, c2 = st.columns(2)
        with c1:
            # 기본 리스트
            option_list = ["엔진오일", "오일필터", "타이어", "브레이크 패드", "구동계", "배터리", "전기장치", "주유"]
            selected_category = st.selectbox("기본 항목 선택", option_list)
        
        with c2:
            # 우선순위 입력창
            manual_category = st.text_input("직접 입력 (여기에 적으면 이게 우선 저장됨)", placeholder="예: 핸들 열선 장착")
        
        # ----------------------------------------

        details = st.text_area("상세 내용", height=80, placeholder="예: 합성유 100% 교환, 공임 포함")
        
        # 저장 버튼
        submit_button = st.form_submit_button(label='☁️ 구글 시트에 저장하기', use_container_width=True)

    # 저장 로직
    if submit_button:
        # [우선순위 로직] 직접 입력칸에 글자가 있으면 -> 그걸 씀. 없으면 -> 선택박스 값을 씀.
        if manual_category:     
            final_category = manual_category
        else:
            final_category = selected_category

        sheet = get_google_sheet()
        if sheet:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_str = date.strftime("%Y-%m-%d")
            
            row_data = [date_str, bike_model, mileage, final_category, details, cost, current_time]
            
            try:
                sheet.append_row(row_data)
                st.success(f"✅ 저장 완료! 항목: [{final_category}]")
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

# ==========================================================================
# [탭 2] 전체 내역 조회
# ==========================================================================
with tab2:
    st.subheader("📋 정비 기록 대장")
    
    if st.button("🔄 최신 데이터 불러오기"):
        st.cache_data.clear()
    
    sheet = get_google_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                
                # 날짜 정렬
                if '날짜' in df.columns:
                    df['날짜'] = pd.to_datetime(df['날짜']).dt.date
                    df = df.sort_values(by='날짜', ascending=False)
                
                # 통계
                total_cost = df['비용(원)'].sum() if '비용(원)' in df.columns else 0
                total_count = len(df)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("총 누적 정비비", f"{total_cost:,.0f}원")
                m2.metric("총 정비 횟수", f"{total_count}회")
                if not df.empty:
                    m3.metric("최근 정비 항목", df.iloc[0]['항목'])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("데이터가 없습니다.")
        except Exception as e:
            st.warning("데이터 로딩 중...")
