import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 페이지 및 기본 설정
# --------------------------------------------------------------------------
st.set_page_config(page_title="바이크 정비노트(Cloud)", page_icon="🏍️", layout="wide")
st.title("🏍️ 마이 바이크 정비노트 (Cloud Ver.)")

# --------------------------------------------------------------------------
# 2. 구글 시트 연결 함수 (Secrets 활용)
# --------------------------------------------------------------------------
@st.cache_resource
def get_google_sheet():
    """Streamlit Secrets에 저장된 키를 이용해 구글 시트에 연결"""
    try:
        # secrets.toml 파일에 저장된 [gcp_service_account] 정보를 가져옵니다.
        credentials = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials)
        
        # '오토바이_정비내역'이라는 이름의 스프레드시트를 엽니다.
        sh = gc.open("오토바이_정비내역") 
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ 구글 시트 연결 실패! 오류 내용: {e}")
        return None

# --------------------------------------------------------------------------
# 3. 탭 구성 (입력하기 / 조회하기)
# --------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📝 정비 입력", "📋 전체 내역 조회"])

# ==========================================================================
# [탭 1] 새로운 정비 내용 입력
# ==========================================================================
with tab1:
    st.subheader("새로운 정비 내용 추가")

    # st.form을 사용해 '저장' 버튼을 누를 때까지 새로고침 방지
    with st.form(key='maintenance_form', clear_on_submit=True):
        
        # 날짜와 차종을 가로로 배치
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("정비 날짜", datetime.now())
            bike_model = st.text_input("차종", value="존테스 350D")
        with col2:
            mileage = st.number_input("주행 거리 (km)", step=100)
            cost = st.number_input("비용 (원)", step=1000)

        st.divider() # 구분선

        # --- [핵심] 정비 항목 선택 및 직접 입력 로직 ---
        col3, col4 = st.columns(2)
        with col3:
            # 기본 선택지
            option_list = ["엔진오일", "오일필터", "타이어", "브레이크 패드", "구동계", "배터리", "전기장치", "직접 입력"]
            selected_category = st.selectbox("정비 항목 선택", option_list)
        with col4:
            # 직접 입력을 선택했을 때 사용할 텍스트 창 (항상 보이지만 '직접 입력'일 때만 적용됨)
            manual_category = st.text_input("직접 입력 (왼쪽에서 '직접 입력' 선택 시)", placeholder="예: 쿨시트 장착")

        details = st.text_area("상세 내용", height=80, placeholder="예: 합성유 100% 교환, 공임 포함")
        
        # 저장 버튼 (화면 꽉 차게)
        submit_button = st.form_submit_button(label='☁️ 구글 시트에 저장하기', use_container_width=True)

    # 저장 버튼이 눌렸을 때 실행되는 로직
    if submit_button:
        # 항목 결정 로직: '직접 입력'을 골랐으면 텍스트창 값을, 아니면 선택창 값을 사용
        if selected_category == "직접 입력":
            final_category = manual_category
            if not final_category: # 비어있으면 경고
                st.warning("⚠️ '직접 입력'을 선택하셨습니다. 정비 항목 이름을 적어주세요.")
                st.stop() # 실행 중단
        else:
            final_category = selected_category

        # 구글 시트 연결
        sheet = get_google_sheet()
        if sheet:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_str = date.strftime("%Y-%m-%d") # 날짜를 문자열로 변환
            
            # 저장할 데이터 리스트
            row_data = [date_str, bike_model, mileage, final_category, details, cost, current_time]
            
            try:
                # 시트 맨 아래에 한 줄 추가
                sheet.append_row(row_data)
                st.success(f"✅ 저장 완료! [{final_category}] 내용이 클라우드에 기록되었습니다.")
            except Exception as e:
                st.error(f"저장 중 오류가 발생했습니다: {e}")

# ==========================================================================
# [탭 2] 전체 내역 실시간 조회
# ==========================================================================
with tab2:
    st.subheader("📋 실시간 정비 대장")
    
    # 데이터 새로고침 버튼
    if st.button("🔄 최신 데이터 불러오기"):
        st.cache_data.clear() # 캐시 비우기
    
    sheet = get_google_sheet()
    if sheet:
        try:
            # 시트의 모든 데이터를 가져옴 (리스트 형태 -> 판다스 데이터프레임 변환)
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # 날짜 기준 내림차순 정렬 (최신 날짜가 위로)
                if '날짜' in df.columns:
                    df['날짜'] = pd.to_datetime(df['날짜']).dt.date # 시간 빼고 날짜만
                    df = df.sort_values(by='날짜', ascending=False)
                
                # --- 상단 요약 통계 ---
                total_cost = df['비용(원)'].sum() if '비용(원)' in df.columns else 0
                total_count = len(df)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("총 누적 정비비", f"{total_cost:,.0f}원")
                m2.metric("총 정비 횟수", f"{total_count}회")
                if not df.empty:
                    m3.metric("최근 정비 항목", df.iloc[0]['항목'])
                
                st.divider()

                # --- 데이터 테이블 ---
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("아직 저장된 정비 기록이 없습니다. '정비 입력' 탭에서 첫 기록을 남겨보세요!")
                
        except Exception as e:
            st.warning("데이터를 불러오는 중입니다. (혹은 시트 헤더가 비어있을 수 있습니다)")
