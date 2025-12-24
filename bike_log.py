import streamlit as st
import pandas as pd
import requests
from datetime import datetime

try:
    import gspread
except ModuleNotFoundError:
    gspread = None

# --------------------------------------------------------------------------
# 1. 페이지 및 기본 설정 (제목 변경 완료)
# --------------------------------------------------------------------------
st.set_page_config(page_title="개인 정비노트", page_icon="🏍️", layout="wide")
st.title("🏍️ 개인 정비노트")

with st.expander("ℹ️ 실행 방법", expanded=False):
    st.markdown(
        """
        1. 필요한 패키지를 설치합니다.
           ```bash
           pip install -r requirements.txt
           ```
        2. `.streamlit/secrets.toml` 파일에 `gcp_service_account` 및 `notebooklm` 설정을 추가합니다.
        3. 아래 명령으로 앱을 실행합니다.
           ```bash
           streamlit run bike_log.py
           ```
        """
    )

# --------------------------------------------------------------------------
# 2. 구글 시트 연결 함수
# --------------------------------------------------------------------------
@st.cache_resource
def get_google_sheet():
    if gspread is None:
        st.error(
            "⚠️ gspread 모듈을 찾을 수 없습니다. `pip install -r requirements.txt` 명령으로 "
            "필수 패키지를 설치한 뒤 다시 시도해주세요."
        )
        return None
    try:
        credentials = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials)
        sh = gc.open("오토바이_정비내역") 
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ 구글 시트 연결 실패! 오류 내용: {e}")
        return None

# --------------------------------------------------------------------------
# 3. 노트북LM API 클라이언트
# --------------------------------------------------------------------------


def get_notebooklm_credentials():
    try:
        notebooklm = st.secrets["notebooklm"]
        api_key = notebooklm.get("api_key")
        endpoint = notebooklm.get("endpoint")
        if not api_key or not endpoint:
            raise ValueError("API 키 또는 엔드포인트가 비어 있습니다.")
        return endpoint, api_key
    except Exception as e:
        raise RuntimeError(f"NotebookLM API 설정을 불러올 수 없습니다: {e}")


def build_notebooklm_prompt(keyword: str, model: str, symptom: str) -> str:
    return (
        "다음 정보를 바탕으로 오토바이 정비 매뉴얼 요약과 진단 가이드를 제공해 주세요.\n"
        "- 사용자가 찾는 키워드: {keyword}\n"
        "- 차량 모델: {model}\n"
        "- 증상/상태: {symptom}\n"
        "필요하다면 추가로 참고할 수 있는 매뉴얼 또는 문서 링크를 함께 제시해 주세요."
    ).format(keyword=keyword or "(미입력)", model=model or "(미입력)", symptom=symptom or "(미입력)")


@st.cache_data(show_spinner=False)
def search_notebooklm(keyword: str, model: str, symptom: str):
    endpoint, api_key = get_notebooklm_credentials()
    prompt = build_notebooklm_prompt(keyword, model, symptom)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "context": {
            "keyword": keyword,
            "model": model,
            "symptom": symptom,
        },
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


# --------------------------------------------------------------------------
# 4. 탭 구성
# --------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📝 정비 입력", "📋 전체 내역 조회", "🔍 매뉴얼/진단"])

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

# ==========================================================================
# [탭 3] 매뉴얼/진단 검색
# ==========================================================================
with tab3:
    st.subheader("🔍 NotebookLM 기반 매뉴얼/진단 검색")
    st.caption("키워드, 차종, 증상을 입력하면 NotebookLM API로 관련 요약과 참고 링크를 받아옵니다.")

    c1, c2 = st.columns(2)
    with c1:
        keyword = st.text_input("검색 키워드", placeholder="예: 체인 장력 조정 방법")
        model = st.selectbox(
            "차량 모델",
            ["존테스 350D", "혼다 PCX", "야마하 NMAX", "가와사키 Z시리즈", "기타"],
            index=0,
        )
    with c2:
        symptom = st.selectbox(
            "증상/상태",
            [
                "시동 불량",
                "이상 진동",
                "브레이크 소음",
                "체인/벨트 문제",
                "전기장치 경고",
                "기타",
            ],
            index=0,
        )
        clear_cache = st.button("🧹 NotebookLM 검색 캐시 초기화", use_container_width=True)

    if clear_cache:
        search_notebooklm.clear()
        st.info("검색 결과 캐시를 초기화했습니다. 동일한 쿼리도 새로 조회합니다.")

    search_button = st.button("🔍 NotebookLM으로 검색", type="primary", use_container_width=True)

    if search_button:
        try:
            with st.spinner("NotebookLM에서 검색 중..."):
                result = search_notebooklm(keyword, model, symptom)

            summary = None
            links = []

            if isinstance(result, dict):
                summary = result.get("summary") or result.get("answer") or result.get("message")
                links = result.get("links") or result.get("documents") or []
            else:
                summary = str(result)

            if summary:
                st.success("검색 결과")
                st.write(summary)
            else:
                st.warning("요약 결과를 찾을 수 없습니다. API 응답을 확인하세요.")

            if links:
                st.markdown("### 📎 관련 문서")
                for item in links:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("name") or "관련 문서"
                        url = item.get("url") or item.get("link")
                        if url:
                            st.markdown(f"- [{title}]({url})")
                        else:
                            st.markdown(f"- {title}")
                    else:
                        st.markdown(f"- {item}")
        except Exception as e:
            st.error("NotebookLM 검색 중 오류가 발생했습니다. 설정과 입력값을 확인하세요.")
            st.exception(e)
