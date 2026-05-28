"""
ETF 데이터 수집 스크립트 - 기초지수 컬럼 기반 자동 분류
get_etf_ohlcv_by_ticker()의 '기초지수' 컬럼으로 지수별 자동 분류합니다.
"""

import json
import time
import os
import re
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


# -----------------------------------------------------------------
# 분류 규칙: (index_id, 기초지수 포함 키워드, 기초지수 제외 키워드)
# 우선순위 순서대로 첫 번째 매칭 규칙에 배정됩니다.
# -----------------------------------------------------------------
CLASSIFY_RULES = [
    # 국내주식
    ("kospi200",     ["코스피200", "KOSPI200", "KRX200"],
                     ["레버리지", "인버스", "배당", "ESG", "동일가중"]),
    ("kosdaq150",    ["코스닥150", "KOSDAQ150"],
                     ["레버리지", "인버스"]),
    ("kr_dividend",  ["코스피고배당", "코스피배당", "배당성장", "한국배당",
                      "코리아배당", "고배당"],
                     ["레버리지", "인버스", "미국", "해외"]),

    # 국내채권
    ("kr_gov10y",    ["국고채10년", "국채10년"],
                     ["레버리지", "인버스"]),
    ("kr_gov3y",     ["국고채3년", "국채3년"],
                     ["레버리지", "인버스"]),
    ("kr_corp",      ["회사채", "종합채권", "크레딧채"],
                     ["레버리지", "인버스", "미국", "해외"]),

    # 국내현금성
    ("kr_cd",        ["CD금리", "KOFR", "단기채", "콜금리", "머니마켓"],
                     ["미국", "해외"]),

    # 해외주식 - 구체적인 것부터
    ("sp500",        ["S&P500", "S&P 500"],
                     ["레버리지", "인버스", "나스닥", "배당", "커버드콜",
                      "섹터", "헬스케어", "금융", "에너지"]),
    ("nasdaq100",    ["나스닥100", "NASDAQ100", "NASDAQ 100"],
                     ["레버리지", "인버스", "커버드콜"]),
    ("us_dividend",  ["미국배당", "다우존스배당", "S&P배당"],
                     ["레버리지", "인버스"]),
    ("msci_world",   ["MSCI World", "MSCI WORLD", "선진국MSCI"],
                     ["레버리지", "인버스", "이머징", "신흥국"]),
    ("msci_em",      ["MSCI EM", "MSCI Emerging", "신흥국MSCI", "이머징"],
                     ["레버리지", "인버스"]),
    ("eu_equity",    ["유로STOXX", "EURO STOXX", "유럽주식"],
                     ["레버리지", "인버스"]),
    ("jp_equity",    ["TOPIX", "Nikkei", "NIKKEI", "닛케이", "일본주식"],
                     ["레버리지", "인버스"]),
    ("china_equity", ["CSI300", "항셍", "HSCEI", "중국주식", "홍콩H"],
                     ["레버리지", "인버스"]),
    ("india_equity", ["Nifty", "NIFTY", "SENSEX", "인도주식"],
                     ["레버리지", "인버스"]),

    # 해외채권 - 구체적인 것부터
    ("us30y",        ["미국채30년", "미국30년", "US Treasury 30"],
                     ["레버리지", "인버스"]),
    ("us10y",        ["미국채10년", "미국10년", "US Treasury 10",
                      "미국국채10"],
                     ["레버리지", "인버스", "30년"]),
    ("tips",         ["물가연동", "TIPS", "Treasury Inflation"],
                     ["레버리지", "인버스"]),
    ("hy_bond",      ["하이일드", "High Yield", "HIGH YIELD"],
                     ["레버리지", "인버스"]),
    ("em_bond",      ["신흥국채권", "EM Bond", "이머징채권"],
                     ["레버리지", "인버스"]),

    # 해외현금성
    ("us_tbill",     ["T-Bill", "TBILL", "미국단기국채", "미국초단기"],
                     ["레버리지", "인버스"]),

    # 대체: 원자재
    ("gold",         ["금현물", "금선물", "Gold", "GOLD", "KRX금"],
                     ["레버리지", "인버스", "금채굴"]),
    ("silver",       ["은선물", "Silver", "SILVER"],
                     ["레버리지", "인버스"]),
    ("oil",          ["WTI", "원유", "Crude Oil", "브렌트"],
                     ["레버리지", "인버스"]),
    ("commodity",    ["원자재", "Commodity", "GSCI", "농산물"],
                     ["레버리지", "인버스"]),

    # 대체: 부동산
    ("us_reit",      ["미국리츠", "미국부동산", "글로벌리츠",
                      "MSCI리츠", "FTSE리츠"],
                     ["레버리지", "인버스"]),
    ("kr_reit",      ["리츠", "부동산투자"],
                     ["레버리지", "인버스", "미국", "글로벌"]),

    # 대체: 통화
    ("usd",          ["달러인덱스", "DXY", "Dollar Index"],
                     ["레버리지", "인버스"]),
]

# 전역 제외: 기초지수에 이 키워드가 있으면 무조건 제외
GLOBAL_EXCLUDE = ["레버리지", "인버스", "곱버스", "2X", "ETN"]


# -----------------------------------------------------------------
# 유틸
# -----------------------------------------------------------------

def get_recent_business_day(offset=1):
    date = datetime.now()
    days_back = 0
    while days_back < offset or date.weekday() >= 5:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            days_back += 1
    return date.strftime("%Y%m%d")


def safe_col(df, keywords):
    for kw in keywords:
        cols = [c for c in df.columns if kw in str(c)]
        if cols:
            return cols[0]
    return None


def classify_by_index(index_name):
    """
    기초지수명으로 지수 ID 반환. 매칭 없으면 None.
    """
    if not index_name or not isinstance(index_name, str):
        return None

    name_upper = index_name.upper()

    for kw in GLOBAL_EXCLUDE:
        if kw.upper() in name_upper:
            return None

    for index_id, includes, excludes in CLASSIFY_RULES:
        if any(kw.upper() in name_upper for kw in includes):
            if not any(kw.upper() in name_upper for kw in excludes):
                return index_id

    return None


# -----------------------------------------------------------------
# 데이터 수집
# -----------------------------------------------------------------

def fetch_etf_info(ticker, name, start, end, etf_all):
    try:
        df_te = stock.get_etf_tracking_error(start, end, ticker)
        if df_te is None or not isinstance(df_te, pd.DataFrame) or df_te.empty:
            return None

        # 추적오차
        te_col = safe_col(df_te, ["추적오차", "오차", "TrackingError", "tracking"])
        tracking_error = round(float(df_te[te_col].abs().mean()), 4) if te_col else 0.0

        # 괴리율
        discount_rate = 0.0
        try:
            ohlcv = stock.get_etf_ohlcv_by_date(start, end, ticker)
            nav_col = safe_col(df_te, ["NAV", "순자산가치", "기준가", "nav"])
            if (nav_col and ohlcv is not None
                    and isinstance(ohlcv, pd.DataFrame)
                    and not ohlcv.empty and "종가" in ohlcv.columns):
                merged = pd.merge(
                    ohlcv[["종가"]], df_te[[nav_col]],
                    left_index=True, right_index=True, how="inner"
                )
                merged["gap"] = (merged["종가"] - merged[nav_col]) / merged[nav_col] * 100
                discount_rate = round(float(merged["gap"].mean()), 4)
        except Exception as e:
            print(f"    괴리율 실패: {e}")

        # 일평균 거래대금 (억원)
        daily_volume = 0.0
        try:
            df_vol = stock.get_etf_trading_volume_and_value(start, end, ticker)
            if df_vol is not None and isinstance(df_vol, pd.DataFrame) and not df_vol.empty:
                vol_col = safe_col(df_vol, ["거래대금", "value", "Value"])
                if vol_col:
                    daily_volume = round(float(df_vol[vol_col].mean()) / 1e8, 1)
        except Exception as e:
            print(f"    거래대금 실패: {e}")

        # AUM (억원) - etf_all에서 추출
        aum = 0.0
        if etf_all is not None and ticker in etf_all.index:
            aum_col = safe_col(etf_all, ["순자산총액", "순자산", "AUM", "시가총액"])
            if aum_col:
                aum = round(float(etf_all.loc[ticker, aum_col]) / 1e8, 1)

        # 상장 기간 (개월)
        listing_months = 0
        try:
            df_all = stock.get_etf_ohlcv_by_date("20000101", end, ticker)
            if df_all is not None and isinstance(df_all, pd.DataFrame) and not df_all.empty:
                first_date = df_all.index.min()
                listing_months = max(1, int(
                    (datetime.now() - pd.Timestamp(first_date)).days / 30
                ))
        except Exception as e:
            print(f"    상장일 실패: {e}")

        return {
            "name":          name,
            "ticker":        ticker,
            "trackingError": tracking_error,
            "discountRate":  discount_rate,
            "aum":           aum,
            "dailyVolume":   daily_volume,
            "listingMonths": listing_months,
        }

    except Exception as e:
        print(f"    [오류] {e}")
        return None


# -----------------------------------------------------------------
# 메인
# -----------------------------------------------------------------

def main():
    end_date   = get_recent_business_day(1)
    start_date = get_recent_business_day(20)
    print(f"수집 기간: {start_date} ~ {end_date}")

    # 전종목 기본정보 1회 조회 (종가, 거래대금, 기초지수, NAV 포함)
    print("\n전종목 ETF 기본정보 조회 중...")
    etf_all = None
    try:
        etf_all = stock.get_etf_ohlcv_by_ticker(end_date)
        if etf_all is not None and not etf_all.empty:
            print(f"조회 완료: {len(etf_all)}개, 컬럼: {list(etf_all.columns)}")
        else:
            print("조회 결과 없음 - 스크립트 종료")
            return
    except Exception as e:
        print(f"전종목 조회 실패: {e}")
        return

    # 기초지수 컬럼으로 분류
    index_col = safe_col(etf_all, ["기초지수"])
    if not index_col:
        print(f"기초지수 컬럼 없음. 실제 컬럼: {list(etf_all.columns)}")
        return

    print(f"\n기초지수 컬럼 확인: '{index_col}'")
    print("분류 시작...")

    classified = {}   # { index_id: [(ticker, index_name), ...] }
    unclassified = []

    for ticker in etf_all.index:
        index_name = str(etf_all.loc[ticker, index_col])
        index_id = classify_by_index(index_name)
        if index_id:
            classified.setdefault(index_id, []).append((ticker, index_name))
        else:
            unclassified.append((ticker, index_name))

    print("\n분류 결과:")
    for idx, items in sorted(classified.items()):
        print(f"  {idx}: {len(items)}개")
    print(f"  미분류: {len(unclassified)}개")

    # 지수별 데이터 수집
    all_index_ids = [rule[0] for rule in CLASSIFY_RULES]
    output = {idx: [] for idx in all_index_ids}

    for index_id, ticker_list in classified.items():
        print(f"\n[{index_id}] 수집 시작 ({len(ticker_list)}개)")
        etf_list = []

        for ticker, index_name in ticker_list:
            # 종목명은 기초지수 대신 ticker로 표시 (이름 조회 불가 우회)
            # etf_all에 종목명 컬럼이 있으면 사용
            name_col = safe_col(etf_all, ["종목명", "Name", "ETF명", "name"])
            if name_col and ticker in etf_all.index:
                name = str(etf_all.loc[ticker, name_col])
            else:
                name = ticker  # fallback: 티커로 대체

            print(f"  {ticker} ({name}) 수집 중...", flush=True)
            result = fetch_etf_info(ticker, name, start_date, end_date, etf_all)
            if result:
                print(f"  -> 완료: 추적오차={result['trackingError']} "
                      f"괴리율={result['discountRate']} "
                      f"AUM={result['aum']}억 "
                      f"거래대금={result['dailyVolume']}억 "
                      f"상장={result['listingMonths']}개월")
                etf_list.append(result)
            else:
                print(f"  -> 건너뜀")
            time.sleep(0.3)

        output[index_id] = etf_list
        print(f"  [{index_id}] {len(etf_list)}개 수집 완료")

    # 저장
    os.makedirs("data", exist_ok=True)
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "data": output,
    }
    with open("data/etf_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in output.values())
    print(f"\n[완료] 총 {total}개 ETF 데이터 저장 -> data/etf_data.json")


if __name__ == "__main__":
    main()
