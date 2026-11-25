import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import matplotlib.pyplot as plt


# 1. 웹 페이지 HTML을 가져오는 함수
def fetch_html(url):
    # 수업 실습용임을 밝히는 User-Agent 설정 (위키백과 차단 방지)
    headers = {
        "User-Agent": "PythonClassPractice/1.0 (Educational purpose for university students)"
    }
    try:
        # timeout=10: 10초 동안 응답이 없으면 시간 초과 에러 발생
        response = requests.get(url, headers=headers, timeout=10)
        # HTTP 상태 코드가 400~500번대(오류)일 경우 예외 발생
        response.raise_for_status()
        return response.text

    except requests.exceptions.Timeout:
        st.error("요청 시간이 초과되었습니다. 인터넷 연결을 확인한 뒤 다시 시도해주세요.")
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP 오류가 발생했습니다. (상태 코드: {e.response.status_code})")
    except requests.exceptions.ConnectionError:
        st.error("서버에 연결할 수 없습니다. 인터넷 연결 상태를 확인해주세요.")
    except requests.exceptions.RequestException as e:
        st.error(f"데이터를 가져오는 중 알 수 없는 오류가 발생했습니다: {e}")
    return None


# 2. HTML에서 원하는 표를 찾아 DataFrame으로 변환하는 함수
def parse_movie_table(html):
    soup = BeautifulSoup(html, "html.parser")
    # class가 'wikitable'인 모든 표 찾기
    tables = soup.find_all("table", class_="wikitable")
    target_table = None

    # 조건에 맞는 표 찾기 (첫 줄에 '관객수'와 '감독'이 모두 포함된 첫 번째 표)
    for table in tables:
        first_row = table.find("tr")
        if first_row:
            header_text = first_row.get_text()
            if "관객수" in header_text and "감독" in header_text:
                target_table = table
                break

    # 표를 찾지 못한 경우 에러 처리
    if target_table is None:
        st.error("조건에 맞는 영화 흥행 기록 표를 찾지 못했습니다.")
        return None

    # 표 내부의 모든 각주 번호(sup 태그) 제거
    for sup in target_table.find_all("sup"):
        sup.decompose()

    rows = target_table.find_all("tr")
    # 첫 번째 줄(tr)의 th 태그에서 열 제목 추출
    headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]

    # 두 번째 줄부터 영화 데이터(td) 추출
    data = []
    for row in rows[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        # 열 개수가 제목 개수와 일치하는 정상적인 행만 추가
        if len(cols) == len(headers):
            data.append(cols)

    df = pd.DataFrame(data, columns=headers)
    return df


# 3. 수집한 데이터를 분석하기 좋게 정제하는 함수
def clean_movie_data(df):
    # 컬럼 이름에 괄호나 공백이 섞여 있을 수 있으므로 핵심 단어로 이름 통일
    col_mapping = {}
    for col in df.columns:
        if "제목" in col or "영화" in col:
            col_mapping[col] = "제목"
        elif "관객수" in col:
            col_mapping[col] = "관객수"
        elif "개봉일" in col:
            col_mapping[col] = "개봉일"
        elif "배급사" in col:
            col_mapping[col] = "한국내 배급사"
    df = df.rename(columns=col_mapping)

    # 제목 양옆의 《 》 기호 제거
    df["제목"] = df["제목"].str.replace("《", "", regex=False).str.replace("》", "", regex=False).str.strip()

    # 관객수에서 숫자만 추출하여 정수(int)로 변환 (쉼표, '명' 등 제거)
    df["관객수"] = df["관객수"].apply(lambda x: int(re.sub(r"[^0-9]", "", str(x))))

    # 개봉일 문자열에서 '연도'와 '월' 숫자 추출
    df["개봉연도"] = df["개봉일"].str.extract(r"(\d{4})").astype(int)
    df["개봉월"] = df["개봉일"].str.extract(r"\d{4}\D+(\d{1,2})").astype(int)

    return df


# 4. 상위 배급사만 묶어서 원그래프를 그리는 함수
def draw_distributor_pie_chart(df):
    # 한글 깨짐 방지를 위한 기본 폰트 설정 (윈도우: Malgun Gothic, 맥: AppleGothic)
    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    # 배급사별 영화 편수 계산 (자동으로 많은 순서대로 정렬됨)
    dist_counts = df["한국내 배급사"].value_counts()

    # 상위 4개 배급사만 남기고, 5위부터는 합쳐서 '기타'로 묶기
    top_n = 4
    if len(dist_counts) > top_n:
        top_dists = dist_counts.iloc[:top_n]
        others_sum = dist_counts.iloc[top_n:].sum()
        # 상위 4개 뒤에 '기타' 항목 추가
        pie_data = pd.concat([top_dists, pd.Series({"기타": others_sum})])
    else:
        pie_data = dist_counts

    # 원그래프 도화지(fig)와 축(ax) 생성
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        pie_data,
        labels=pie_data.index,
        autopct="%1.1f%%",  # 소수점 첫째 자리까지 퍼센트(%) 표시
        startangle=90,      # 12시 방향부터 시계 반대 방향으로 그리기
        counterclock=False  # 시계 방향으로 정렬
    )
    ax.axis("equal")  # 원이 찌그러지지 않고 정원이 되도록 고정

    # Streamlit 화면에 matplotlib 그래프 출력
    st.pyplot(fig)


# 5. 지표, 표, 차트를 화면에 출력하는 함수
def display_dashboard(df):
    st.subheader("주요 흥행 지표")

    # 관객수 기준 내림차순 정렬 (1위 찾기용)
    df_sorted = df.sort_values(by="관객수", ascending=False)
    top_movie = df_sorted.iloc[0]

    # 3개의 칸으로 나누어 핵심 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("천만 영화 수", f"{len(df)}편")
    col2.metric("역대 1위 영화", top_movie["제목"])
    col3.metric("1위 관객수", f"{top_movie['관객수']:,}명")

    st.divider()

    # 전체 데이터 표 출력 (hide_index=True로 인덱스 숨김)
    st.subheader("천만 관객 돌파 한국 영화 목록")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.divider()

    # 관객수 상위 10편 가로 막대 차트
    st.subheader("관객수 상위 10편")
    top10 = df_sorted.head(10).set_index("제목")
    st.bar_chart(top10["관객수"], horizontal=True)

    # 개봉 연도별 편수 세로 막대 차트
    st.subheader("개봉 연도별 천만 영화 편수")
    year_counts = df["개봉연도"].value_counts().sort_index()
    st.bar_chart(year_counts)

    # 한국내 배급사별 점유율 원그래프
    st.subheader("한국내 배급사별 천만 영화 점유율 (상위 4개사 및 기타)")
    draw_distributor_pie_chart(df)


# 6. 앱의 전체 흐름을 제어하는 메인 함수
def main():
    st.title("대한민국 천만 관객 영화 분석 대시보드")
    st.write("위키백과 '대한민국의 영화 흥행 기록' 문서에서 데이터를 수집해 분석합니다.")

    url = "https://ko.wikipedia.org/wiki/대한민국의_영화_흥행_기록"

    # 버튼을 눌렀을 때만 실행
    if st.button("데이터 수집 및 분석 시작"):
        with st.spinner("위키백과에서 데이터를 불러오는 중입니다..."):
            html = fetch_html(url)
            if html:
                raw_df = parse_movie_table(html)
                if raw_df is not None:
                    cleaned_df = clean_movie_data(raw_df)
                    display_dashboard(cleaned_df)


# 파이썬 파일이 직접 실행될 때 main() 함수 호출
if __name__ == "__main__":
    main()