
import re
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
CSV_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 중식 메뉴 연관규칙 분석")


# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL, encoding="utf-8")

    required_columns = ["날짜", "식사", "메뉴"]

    if not all(col in df.columns for col in required_columns):
        raise ValueError(
            "CSV에 날짜, 식사, 메뉴 열이 필요합니다."
        )

    return df


# --------------------------------------------------
# 메뉴명 정리
# --------------------------------------------------
def clean_menu(menu):
    """메뉴명에서 괄호와 괄호 안의 내용을 제거한다."""

    menu = str(menu).strip()

    previous = None

    while previous != menu:
        previous = menu

        menu = re.sub(
            r"\([^()]*\)|（[^（）]*）",
            "",
            menu
        )

    return menu.strip()


# --------------------------------------------------
# 장바구니 데이터 만들기
# --------------------------------------------------
def make_baskets(df):
    baskets = []

    for _, row in df.iterrows():

        menus = str(row["메뉴"]).split("|")

        cleaned_menus = set()

        for menu in menus:
            cleaned = clean_menu(menu)

            if cleaned:
                cleaned_menus.add(cleaned)

        baskets.append(cleaned_menus)

    return baskets


# --------------------------------------------------
# 연관규칙 분석
# --------------------------------------------------
def analyze_rules(baskets):

    total_days = len(baskets)

    item_counts = {}
    pair_counts = {}

    # 메뉴별 등장 횟수 및 메뉴 쌍 등장 횟수
    for basket in baskets:

        for menu in basket:
            item_counts[menu] = (
                item_counts.get(menu, 0) + 1
            )

        for a, b in combinations(sorted(basket), 2):

            pair_counts[(a, b)] = (
                pair_counts.get((a, b), 0) + 1
            )

    rules = []

    if total_days == 0:
        return (
            pd.DataFrame(),
            item_counts,
            pair_counts
        )

    # 연관규칙 생성
    for (a, b), both_count in pair_counts.items():

        support = both_count / total_days

        support_a = item_counts[a] / total_days
        support_b = item_counts[b] / total_days

        # A -> B
        confidence_ab = both_count / item_counts[a]
        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": a,
            "결과": b,
            "동시": both_count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        confidence_ba = both_count / item_counts[b]
        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": b,
            "결과": a,
            "동시": both_count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(
        rules,
        columns=[
            "조건",
            "결과",
            "동시",
            "지지도",
            "신뢰도",
            "향상도"
        ]
    )

    return rules_df, item_counts, pair_counts


# --------------------------------------------------
# 함께 나온 적 없는 메뉴 찾기
# --------------------------------------------------
def find_never_together(
    selected_menu,
    baskets,
    item_counts,
    min_days=10
):
    """
    선택 메뉴와 함께 나온 적이 없고,
    개별적으로 min_days 이상 등장한 메뉴를 찾는다.
    """

    # 선택 메뉴가 등장한 날의 수
    selected_days = item_counts.get(selected_menu, 0)

    # 선택 메뉴와 함께 나온 적이 있는 메뉴들
    together_menus = set()

    for basket in baskets:

        if selected_menu in basket:
            together_menus.update(basket)

    # 함께 나온 적 없는 메뉴 찾기
    results = []

    for menu, count in item_counts.items():

        if menu == selected_menu:
            continue

        if menu in together_menus:
            continue

        if count < min_days:
            continue

        results.append({
            "메뉴": menu,
            "나온 날 수": count,
            "기준 메뉴 나온 날 수": selected_days
        })

    result_df = pd.DataFrame(
        results,
        columns=[
            "메뉴",
            "나온 날 수",
            "기준 메뉴 나온 날 수"
        ]
    )

    result_df = result_df.sort_values(
        by="나온 날 수",
        ascending=False
    ).reset_index(drop=True)

    return result_df, selected_days


# --------------------------------------------------
# 데이터 분석 실행
# --------------------------------------------------
try:

    df = load_data()

    baskets = make_baskets(df)

    rules_df, item_counts, pair_counts = analyze_rules(
        baskets
    )

except Exception as e:

    st.error(
        f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


# --------------------------------------------------
# 데이터 요약
# --------------------------------------------------
total_days = len(baskets)
menu_types = len(item_counts)
total_pairs = len(pair_counts)

st.markdown("### 📊 분석 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric(
    "급식 일수",
    f"{total_days:,}일"
)

col2.metric(
    "메뉴 종류 수",
    f"{menu_types:,}개"
)

col3.metric(
    "함께 나온 메뉴 쌍",
    f"{total_pairs:,}쌍"
)

st.divider()


# --------------------------------------------------
# 연관규칙 검색
# --------------------------------------------------
st.markdown("### 🔎 연관규칙 검색")

col1, col2 = st.columns([2, 1])

with col1:

    selected_menu = st.selectbox(
        "좁혀 보기 - 메뉴 선택",
        options=["전체 메뉴"] + sorted(item_counts.keys()),
        index=0,
        key="rule_menu_filter"
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=[
            "향상도 순",
            "신뢰도 순",
            "동시 순"
        ],
        key="rule_sort"
    )


# --------------------------------------------------
# 최소 동시 일수 슬라이더
# --------------------------------------------------
min_count = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수 이상 함께 나온 메뉴 규칙만 표시합니다."
)


# --------------------------------------------------
# 규칙 필터링
# --------------------------------------------------
filtered_df = rules_df.copy()

# 최소 동시 일수 적용
filtered_df = filtered_df[
    filtered_df["동시"] >= min_count
]

# 메뉴 선택 적용
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]


# --------------------------------------------------
# 정렬
# --------------------------------------------------
sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

filtered_df = filtered_df.sort_values(
    by=sort_columns[sort_option],
    ascending=False
).reset_index(drop=True)


# --------------------------------------------------
# 필터 적용 후 규칙 개수 표시
# --------------------------------------------------
st.markdown(
    f"**현재 조건에 해당하는 연관규칙: {len(filtered_df):,}개**"
)


# --------------------------------------------------
# 연관규칙 표
# --------------------------------------------------
st.markdown("### 📋 연관규칙 분석 결과")

if filtered_df.empty:

    st.warning(
        "선택한 조건에 해당하는 연관규칙이 없습니다."
    )

else:

    display_df = filtered_df.copy()

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    st.dataframe(
        display_df[
            [
                "조건",
                "결과",
                "동시",
                "지지도",
                "신뢰도",
                "향상도"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=450
    )


# --------------------------------------------------
# 향상도 TOP 10 그래프
# --------------------------------------------------
st.divider()

st.markdown("### 📈 향상도 TOP 10")

st.caption(
    "선택한 메뉴와 최소 동시 일수 조건을 적용한 "
    "연관규칙 중 향상도가 높은 10개를 표시합니다."
)

if filtered_df.empty:

    st.info(
        "그래프에 표시할 데이터가 없습니다."
    )

else:

    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=False
        )
        .head(10)
        .copy()
    )

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10["향상도"].map(
            lambda x: f"{x:.2f}"
        ),
        color="향상도",
        color_continuous_scale="Blues",
        labels={
            "향상도": "Lift (향상도)",
            "규칙": "연관규칙"
        },
        title="향상도 상위 10개 연관규칙"
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=450,
        showlegend=False,
        yaxis_title="",
        xaxis_title="향상도 (Lift)",
        margin=dict(
            l=20,
            r=50,
            t=60,
            b=30
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# --------------------------------------------------
# 함께 나온 적 없는 짝
# --------------------------------------------------
st.divider()

st.markdown("### 🚫 함께 나온 적 없는 짝")

st.caption(
    "선택한 메뉴와 같은 날 한 번도 함께 나오지 않았으며, "
    "개별적으로 10일 이상 등장한 메뉴를 찾습니다."
)

# 위의 좁혀 보기와 별개의 메뉴 선택 상자
never_together_menu = st.selectbox(
    "함께 나온 적 없는 짝 - 기준 메뉴 선택",
    options=sorted(item_counts.keys()),
    index=0 if item_counts else None,
    key="never_together_menu"
)

if never_together_menu:

    never_df, selected_days = find_never_together(
        selected_menu=never_together_menu,
        baskets=baskets,
        item_counts=item_counts,
        min_days=10
    )

    # 기준 메뉴 등장 일수 표시
    col1, col2 = st.columns(2)

    col1.metric(
        "선택한 기준 메뉴",
        never_together_menu
    )

    col2.metric(
        "기준 메뉴가 나온 날",
        f"{selected_days:,}일"
    )

    st.markdown(
        f"**함께 나온 적 없는 메뉴: {len(never_df):,}개**"
    )

    if never_df.empty:

        st.info(
            "조건에 맞는 메뉴가 없습니다."
        )

    else:

        st.dataframe(
            never_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )


# --------------------------------------------------
# 분석 지표 설명
# --------------------------------------------------
st.divider()

with st.expander("📖 연관규칙 분석 지표 설명"):

    st.markdown("""
    | 지표 | 의미 | 계산 방법 |
    |---|---|---|
    | 조건 | 기준이 되는 메뉴 A | - |
    | 결과 | 함께 등장하는 메뉴 B | - |
    | 동시 | A와 B가 같은 날 나온 횟수 | 교집합 |
    | 지지도 | 전체 급식일 중 A와 B가 함께 나온 비율 | P(A ∩ B) |
    | 신뢰도 | A가 나온 날 B도 나온 비율 | P(B \| A) |
    | 향상도 | A와 B의 연관성 정도 | P(B \| A) / P(B) |

    **향상도 해석**

    - 1보다 크면 양의 연관성이 있습니다.
    - 1이면 독립적으로 등장합니다.
    - 1보다 작으면 음의 연관성이 있습니다.

    **함께 나온 적 없는 짝 해석**

    - 기준 메뉴와 같은 날 한 번도 등장하지 않은 메뉴입니다.
    - 해당 메뉴 자체는 10일 이상 등장해야 합니다.
    - 나온 날 수가 많은 순서로 정렬합니다.
    - 기준 메뉴의 등장 일수도 함께 표시합니다.

    ※ 연관성은 인과관계를 의미하지 않습니다.
    """)
