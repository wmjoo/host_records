import lxml
import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

import matplotlib.pyplot as plt
import seaborn as sns

from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
# plt.rc('font', family='NanumGothic') # or the name of the font you have installed

st.set_page_config(
        page_title="Baseball Data",
)
st.title('성남(토요)리그 DATA')

# DATE_COLUMN = 'date/time'
team_id_dict = {
    "코메츠 호시탐탐": 7984, "Big Hits": 36636,    "FA Members": 13621,
    "RedStorm": 17375,    "unknown`s": 33848, "그냥하자": 10318,
    "기드온스": 27811,    "다이아몬스터": 39783,     "데빌베어스(Devil Bears)": 19135,
    "라이노즈": 41236,    "미파스": 19757,    "분당스타즈": 34402,
    "블루레이커즈": 22924,    "성시야구선교단": 29105,    "와사비": 14207,
}

team_name = st.selectbox(
    '팀 선택',
    (team_id_dict.keys()))

# st.write('You selected TEAM:', option)

ALB_URL_SCHD = "http://alb.or.kr/s/schedule/schedule_team_2019.php?id=schedule_team&sc=2&team=%B7%B9%BE%CB%B7%E7%C5%B0%C1%EE&gyear=2024"

def load_data(team_name, team_id):
    urls = {
        'hitter': f"http://www.gameone.kr/club/info/ranking/hitter?club_idx={team_id}",
        'pitcher': f"http://www.gameone.kr/club/info/ranking/pitcher?club_idx={team_id}"
    }
    results = {'hitter': [], 'pitcher': []}
    for key, url in urls.items():
        response = requests.get(url)
        tables = pd.read_html(response.text)
        for table in tables:
            extracted_df = table['이름'].str.extract(r"(\w+)\((\d+)\)")
            extracted_df.columns = ['성명', '배번']
            extracted_df['배번'] = extracted_df['배번'].astype(int)
            table = pd.concat([extracted_df, table.drop(['이름'], axis=1)], axis=1)
            # 컬럼명 변경
            if '게임수' in table.columns:
                if key == 'hitter':
                    table.rename(columns={'게임수': '경기'}, inplace=True)
                else:
                    table.rename(columns={'게임수': '경기수'}, inplace=True)

            table['팀'] = team_name  # 팀 이름 컬럼 추가
            table = table.drop('순위', axis = 1)
            table.columns = [col.replace(" ", "") for col in table.columns]
            results[key].append(table)
    return {'hitter': pd.concat(results['hitter'], ignore_index=True), 
            'pitcher': pd.concat(results['pitcher'], ignore_index=True)}

# 병렬로 데이터 로딩
hitters = []
pitchers = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(load_data, team_name, team_id): team_name for team_name, team_id in team_id_dict.items()}
    for future in as_completed(futures):
        try:
            result = future.result()
            hitters.append(result['hitter'])
            pitchers.append(result['pitcher'])
        except Exception as exc:
            print(f'Team {futures[future]} generated an exception: {exc}')

# 모든 데이터를 각각의 데이터프레임으로 합침
final_hitters_data = pd.concat(hitters, ignore_index=True)
final_pitchers_data = pd.concat(pitchers, ignore_index=True)

# 데이터프레임 df에 적용할 자료형 매핑
hitter_data_types = {
    '성명': 'str', '배번': 'str', '타율': 'float', '경기': 'int', '타석': 'int', '타수': 'int',
    '득점': 'int', '총안타': 'int', '1루타': 'int', '2루타': 'int', '3루타': 'int', '홈런': 'int',
    '루타': 'int', '타점': 'int', '도루': 'int', '도실(도루자)': 'int', '희타': 'int', '희비': 'int',
    '볼넷': 'int', '고의4구': 'int', '사구': 'int', '삼진': 'int', '병살': 'int', '장타율': 'float',
    '출루율': 'float', '도루성공률': 'float', '멀티히트': 'int', 'OPS': 'float', 'BB/K': 'float',
    '장타/안타': 'float', '팀': 'str'
}
# 데이터프레임 df의 컬럼 자료형 설정
df_hitter = final_hitters_data.astype(hitter_data_types)
# 타자 데이터프레임 컬럼명 영어로
df_hitter.columns = ['Name', 'No', 'BA', 'G', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CS', 'SH', 'SF', 
                     'BB', 'IBB', 'HBP', 'SO', 'DP', 'SLG', 'OBP',  'SB%', 'MHit', 'OPS', 'BB/K', 'XBH/H', 'Team']

# 투수 데이터프레임 df_pitcher에 적용할 자료형 매핑
pitcher_data_types = {
    '성명': 'str', '배번': 'str', '방어율': 'float', '경기수': 'int', '승': 'int', '패': 'int', '세': 'int',
    '홀드': 'int', '승률': 'float', '타자': 'int', '타수': 'int', '투구수': 'int', '이닝': 'float',
    '피안타': 'int', '피홈런': 'int', '희타': 'int', '희비': 'int', '볼넷': 'int', '고의4구': 'int',
    '사구': 'int', '탈삼진': 'int', '폭투': 'int', '보크': 'int', '실점': 'int', '자책점': 'int',
    'WHIP': 'float', '피안타율': 'float', '탈삼진율': 'float', '팀': 'str'
}

final_pitchers_data.loc[final_pitchers_data.방어율 == '-', '방어율'] = np.nan
# 투수 데이터프레임 df_pitcher의 컬럼 자료형 설정
df_pitcher = final_pitchers_data.astype(pitcher_data_types)
# 투수 데이터프레임 컬럼명 영어로
df_pitcher.columns = ['Name', 'No', 'ERA', 'GS', 'W', 'L', 'SV', 'HLD', 'WPCT', 'BF', 'AB', 'P', 'IP', 'HA', 'HR', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'WP', 'BK', 
                      'R', 'ER', 'WHIP', 'BAA', 'K9', 'Team']
# IP 컬럼을 올바른 소수 형태로 변환
df_pitcher['IP'] = df_pitcher['IP'].apply(lambda x: int(x) + (x % 1) * 10 / 3).round(2)

# 팀명을 기준으로 데이터 프레임 필터링
team_id = team_id_dict[team_name]
DATA_URL_B = "http://www.gameone.kr/club/info/ranking/hitter?club_idx={}".format(team_id)
DATA_URL_P = "http://www.gameone.kr/club/info/ranking/pitcher?club_idx={}".format(team_id)

## 탭 설정
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["성남:팀별타자", "성남:팀별투수",
                                                                            "성남:전체타자", "성남:전체투수", "성남:시각화", "용어"]) #"투수:규정이상", "투수:규정미달", "안양_일정"])

with tab1:
    df_hitter_team = df_hitter.loc[df_hitter.Team == team_name].reset_index(drop=True).drop('Team', axis = 1)
    st.subheader('타자 : {} [{}명]'.format(team_name, df_hitter_team.shape[0]))
    st.dataframe(df_hitter_team)
    st.write(DATA_URL_B)

with tab2:
    df_pitcher_team = df_pitcher.loc[df_pitcher.Team == team_name].reset_index(drop=True).drop('Team', axis = 1)
    st.subheader('투수 : {} [{}명]'.format(team_name, df_pitcher_team.shape[0]))
    st.dataframe(df_pitcher_team) 
    st.write(DATA_URL_P)

with tab3:
    st.subheader('성남 : 전체타자 [{}명]'.format(df_hitter.shape[0]))
    st.dataframe(df_hitter)
    st.subheader('팀별 기록')
    hitter_sumcols = [    'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'DP', 'MHit']
    hitter_grpby = df_hitter[hitter_sumcols + ['Team']].groupby('Team').sum().reset_index()

    # 타율(BA), 출루율(OBP), 장타율(SLG), OPS 계산 & 반올림
    hitter_grpby['BA'] = (hitter_grpby['H'] / hitter_grpby['AB']).round(3)
    hitter_grpby['OBP'] = ((hitter_grpby['H'] + hitter_grpby['BB'] + hitter_grpby['HBP']) / (hitter_grpby['AB'] + hitter_grpby['BB'] + hitter_grpby['HBP'] + hitter_grpby['SF'])).round(3)
    hitter_grpby['SLG'] = (hitter_grpby['TB'] / hitter_grpby['AB']).round(3)
    hitter_grpby['OPS'] = (hitter_grpby['OBP'] + hitter_grpby['SLG']).round(3)
    
    # 'Team' 컬럼 바로 다음에 계산된 컬럼들 삽입
    for col in ['OPS', 'SLG', 'OBP', 'BA']:
        team_idx = hitter_grpby.columns.get_loc('Team') + 1
        hitter_grpby.insert(team_idx, col, hitter_grpby.pop(col))
        
    st.dataframe(hitter_grpby)

with tab4:
    st.subheader('성남 : 전체투수 [{}명]'.format(df_pitcher.shape[0]))
    st.dataframe(df_pitcher)
    st.subheader('팀별 기록')
    # df = df_pitcher.copy() #pd.read_csv(file_path)
    # 팀별로 그룹화하고 정수형 변수들의 합계 계산
    pitcher_sumcols = df_pitcher.select_dtypes(include=['int64']).columns.tolist() + ['IP'] # Sum 컬럼 선택
    grouped_df = df_pitcher.groupby('Team')[pitcher_sumcols].sum().reset_index()  # 팀별 합계
    # st.write(grouped_df)
    # 파생 변수 추가
    # 방어율(ERA) 계산: (자책점 / 이닝) * 9 (예제로 자책점과 이닝 컬럼 필요)
    if 'ER' in df_pitcher.columns and 'IP' in df_pitcher.columns:
        grouped_df['ERA'] = (grouped_df['ER'] / grouped_df['IP']) * 9
    
    # 이닝당 삼진/볼넷/피안타 계산 (예제로 삼진(K), 볼넷(BB), 피안타(HA) 컬럼 필요)
    if 'K' in df_pitcher.columns and 'BB' in df_pitcher.columns and 'HA' in df.columns:
        grouped_df['K/9'] = (grouped_df['K'] / grouped_df['IP']) * 9
        grouped_df['BB/9'] = (grouped_df['BB'] / grouped_df['IP']) * 9
        grouped_df['H/9'] = (grouped_df['HA'] / grouped_df['IP']) * 9
    
    # WHIP 계산: (볼넷 + 피안타) / 이닝
    if 'BB' in df_pitcher.columns and 'HA' in df_pitcher.columns:
        grouped_df['WHIP'] = (grouped_df['BB'] + grouped_df['HA']) / grouped_df['IP']
    
    # 'Team' 컬럼 바로 다음에 계산된 컬럼들 삽입
    new_cols = ['ERA', 'K/9', 'BB/9', 'H/9', 'WHIP']
    for col in new_cols:
        if col in grouped_df.columns:
            team_idx = grouped_df.columns.get_loc('Team') + 1
            grouped_df.insert(team_idx, col, grouped_df.pop(col).round(3))
    
    # 결과 확인
    st.write(grouped_df)


# Tab5 내용 구성
with tab5:
    df = df_hitter    
    st.subheader('야구 통계 시각화')
    col1, col2, col3 = st.columns(3)

    with col1:
            # 데이터셋 선택을 위한 토글 버튼
            dataset_choice = '타자'
            dataset_choice = st.radio('데이터셋 선택', ('타자', '투수'))

    with col2:
            # 그래프 유형 선택을 위한 토글 버튼
            graph_type = '히스토그램'
            graph_type = st.radio('그래프 유형', ('히스토그램', '박스플롯'))

    with col3:
            colsNo = st.selectbox( '1부터 4 사이의 숫자를 선택하세요:',
                                    options=[1, 2, 3, 4], index=2  # 'options' 리스트에서 '3'이 위치한 인덱스는 2 (0부터 시작)
                                )
    # 선택된 데이터셋에 따라 데이터 프레임 설정
    if dataset_choice == '타자':
        df = df_hitter
    else:
        df = df_pitcher

   # 수치형 데이터만 필터링
    numeric_columns = df.select_dtypes(include=['float', 'int']).columns

    # rows 수 결정
    rows = (len(numeric_columns) + colsNo - 1) // colsNo

   # "Plotting" 버튼 추가
    if st.button('Plotting'):
        # 선택된 그래프 유형에 따라 그래프 생성
        fig, axs = plt.subplots(rows, colsNo, figsize=(15, 5 * rows))
        axs = np.array(axs).reshape(-1)  # 차원을 일정하게 유지

        for i, var in enumerate(numeric_columns):
            ax = axs[i // colsNo, i % colsNo]
            if graph_type == '히스토그램':
                sns.histplot(df[var].dropna(), kde=False, ax=ax)
                ax.set_title(f'{var}')
            elif graph_type == '박스플롯':
                sns.boxplot(x=df[var].dropna(), ax=ax)
                ax.set_title(f'{var}')

            # 빈 서브플롯 숨기기
            for j in range(len(numeric_columns), rows * colsNo):
                axs[j].set_visible(False)

        plt.tight_layout()
        st.pyplot(fig)

with tab6:
    st.subheader('야구 기록 설명')
    col1, col2 = st.columns(2)
    # 스트림릿 페이지 제목 설정
    with col1:
        # 타자 데이터 설명
        st.markdown("""
        ### 타자(Hitters) 컬럼명 약어:
        | ENG | KOR | Desc                    |
        |--------------|-------------|--------------------------------|
        | Name         | 성명        | Player's name                  |
        | No           | 배번        | Jersey number                  |
        | BA           | 타율        | Batting average                |
        | G            | 경기        | Games played                   |
        | PA           | 타석        | Plate appearances              |
        | AB           | 타수        | At bats                        |
        | R            | 득점        | Runs                           |
        | H            | 총안타      | Hits                           |
        | 1B           | 1루타       | Singles                        |
        | 2B           | 2루타       | Doubles                        |
        | 3B           | 3루타       | Triples                        |
        | HR           | 홈런        | Home runs                      |
        | TB           | 루타        | Total bases                    |
        | RBI          | 타점        | Runs batted in                 |
        | SB           | 도루        | Stolen bases                   |
        | CS           | 도실(도루자)| Caught stealing                |
        | SH           | 희타        | Sacrifice hits                 |
        | SF           | 희비        | Sacrifice flies                |
        | BB           | 볼넷        | Walks                          |
        | IBB          | 고의4구     | Intentional walks              |
        | HBP          | 사구        | Hit by pitch                   |
        | SO           | 삼진        | Strikeouts                     |
        | DP           | 병살        | Double plays                   |
        | SLG          | 장타율      | Slugging percentage            |
        | OBP          | 출루율      | On-base percentage             |
        | SB%          | 도루성공률  | Stolen base percentage         |
        | MHit         | 멀티히트    | Multi-hit games                |
        | OPS          | OPS         | On-base plus slugging          |
        | BB/K         | BB/K       | Walks per strikeout            |
        | XBH/H        | 장타/안타   | Extra base hits per hit        |
        | Team         | 팀          | Team name                      |
        """)
    with col2:
        # 투수 데이터 설명
        st.markdown("""
        ### 투수(Pitchers) 컬럼명 약어:
        | ENG | KOR | Desc                    |
        |--------------|-------------|--------------------------------|
        | Name         | 성명        | Player's name                  |
        | No           | 배번        | Jersey number                  |
        | ERA          | 방어율      | Earned run average             |
        | GS           | 경기수      | Games started                  |
        | W            | 승          | Wins                           |
        | L            | 패          | Losses                         |
        | SV           | 세          | Saves                          |
        | HLD          | 홀드        | Holds                          |
        | WPCT         | 승률        | Winning percentage             |
        | BF           | 타자        | Batters faced                  |
        | AB           | 타수        | At bats against                |
        | P            | 투구수      | Pitches thrown                 |
        | IP           | 이닝        | Innings pitched                |
        | HA           | 피안타      | Hits allowed                   |
        | HR           | 피홈런      | Home runs allowed              |
        | SH           | 희타        | Sacrifice hits allowed         |
        | SF           | 희비        | Sacrifice flies allowed        |
        | BB           | 볼넷        | Walks allowed                  |
        | IBB          | 고의4구     | Intentional walks allowed      |
        | HBP          | 사구        | Hit by pitch allowed           |
        | SO           | 탈삼진      | Strikeouts                     |
        | WP           | 폭투        | Wild pitches                   |
        | BK           | 보크        | Balks                          |
        | R            | 실점        | Runs allowed                   |
        | ER           | 자책점      | Earned runs allowed            |
        | WHIP         | WHIP        | Walks plus hits per inning     |
        | BAA          | 피안타율    | Batting average against        |
        | K9           | 탈삼진율    | Strikeouts per nine innings    |
        | Team         | 팀          | Team name                      |
        """)
