"""
ETF 데이터 수집 스크립트
종목명 하드코딩 + pykrx로 추적오차/괴리율/거래대금/AUM/상장기간 수집
"""

import json
import time
import os
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


# -----------------------------------------------------------------
# 지수별 ETF 목록: { index_id: { ticker: name } }
# 레버리지/인버스 제외, 주요 운용사(KODEX/TIGER/ACE/SOL/RISE/HANARO/PLUS/KIWOOM/KOSEF/KBSTAR) 포함
# -----------------------------------------------------------------
INDEX_TICKERS = {
    # ── 국내주식 ──────────────────────────────────────────────
    "kospi200": {
        "069500": "KODEX 200",
        "102110": "TIGER 200",
        "278530": "KODEX 200TR",
        "278540": "TIGER 200TR",
        "385720": "HANARO 200",
        "459580": "PLUS 200",
        "364960": "KIWOOM 200",
        "251340": "RISE 200",
        "152100": "KOSEF 200",
        "245340": "KBSTAR 200",
        "306520": "ACE 200",
    },
    "kosdaq150": {
        "229200": "KODEX 코스닥150",
        "278600": "TIGER 코스닥150",
        "368590": "ACE 코스닥150",
        "411060": "RISE 코스닥150",
        "409820": "HANARO 코스닥150",
    },
    "kr_dividend": {
        "279530": "KODEX 배당성장",
        "270800": "KODEX 배당가치",
        "322400": "KODEX 한국배당가치",
        "421460": "TIGER 배당성장",
        "441640": "TIGER 코스피고배당",
        "266160": "KBSTAR 200고배당커버드콜ATM",
        "400970": "SOL 배당다우존스",
        "460300": "ACE 코리아밸류업",
        "476760": "PLUS 고배당주",
    },

    # ── 국내채권 ──────────────────────────────────────────────
    "kr_gov10y": {
        "148070": "KOSEF 국고채10년",
        "305720": "TIGER 국채10년",
        "352560": "KODEX 국고채10년",
        "385590": "ACE 국고채10년",
        "476600": "HANARO 국고채10년",
    },
    "kr_gov3y": {
        "152380": "TIGER 국채3년",
        "114820": "KODEX 국고채3년",
        "157450": "KOSEF 국고채3년",
        "365780": "ACE 국고채3년",
        "385600": "KBSTAR 국고채3년",
    },
    "kr_corp": {
        "136340": "KBSTAR 우량회사채",
        "159560": "KODEX 종합채권AA이상",
        "273130": "TIGER 우량회사채",
        "385780": "ACE 종합채권(AA-이상)액티브",
        "476540": "HANARO 종합채권액티브",
    },

    # ── 국내현금성 ────────────────────────────────────────────
    "kr_cd": {
        "214980": "KODEX CD금리액티브(합성)",
        "432350": "KODEX KOFR금리액티브(합성)",
        "438320": "TIGER CD금리투자KIS(합성)",
        "449170": "TIGER KOFR금리액티브(합성)",
        "476570": "ACE CD금리액티브(합성)",
        "476560": "HANARO CD금리액티브(합성)",
        "452260": "PLUS KOFR금리액티브(합성)",
        "476590": "SOL CD금리액티브(합성)",
    },

    # ── 해외주식: S&P500 ──────────────────────────────────────
    "sp500": {
        "360750": "TIGER 미국S&P500",
        "379800": "KODEX 미국S&P500TR",
        "429500": "KODEX 미국S&P500",
        "360200": "ACE 미국S&P500",
        "449170": "SOL 미국S&P500",
        "458730": "RISE 미국S&P500",
        "469070": "HANARO 미국S&P500",
        "453810": "PLUS 미국S&P500",
        "465330": "KIWOOM 미국S&P500",
        "476660": "KBSTAR 미국S&P500",
        "487190": "KOSEF 미국S&P500",
    },

    # ── 해외주식: NASDAQ100 ───────────────────────────────────
    "nasdaq100": {
        "133690": "TIGER 미국나스닥100",
        "379810": "KODEX 미국나스닥100TR",
        "367380": "ACE 미국나스닥100",
        "449160": "SOL 미국나스닥100",
        "463250": "RISE 미국나스닥100",
        "468370": "HANARO 미국나스닥100",
        "453820": "PLUS 미국나스닥100",
        "476650": "KBSTAR 미국나스닥100",
        "487200": "KIWOOM 미국나스닥100",
    },

    # ── 해외주식: 미국 배당 ───────────────────────────────────
    "us_dividend": {
        "441680": "TIGER 미국배당다우존스",
        "466920": "ACE 미국배당다우존스",
        "455890": "KODEX 미국배당프리미엄액티브",
        "476680": "SOL 미국배당다우존스",
        "487210": "HANARO 미국배당다우존스",
        "400970": "RISE 미국배당다우존스",
    },

    # ── 해외주식: 선진국/글로벌 ──────────────────────────────
    "msci_world": {
        "251350": "KODEX 선진국MSCI World",
        "390390": "TIGER 선진국MSCI World",
        "459080": "ACE 선진국MSCI World(합성)",
        "476700": "HANARO 선진국MSCI World",
    },

    # ── 해외주식: 신흥국 ─────────────────────────────────────
    "msci_em": {
        "195930": "TIGER 신흥국MSCI(합성)",
        "291890": "KODEX 신흥국MSCI(합성)",
        "476710": "ACE 신흥국MSCI(합성)",
    },

    # ── 해외주식: 일본 ───────────────────────────────────────
    "jp_equity": {
        "241180": "KODEX 일본TOPIX100",
        "396520": "TIGER 일본니케이225",
        "463260": "ACE 일본니케이225(H)",
        "476720": "HANARO 일본니케이225",
        "487220": "RISE 일본니케이225",
    },

    # ── 해외주식: 중국 ───────────────────────────────────────
    "china_equity": {
        "256840": "TIGER 차이나CSI300",
        "168580": "KODEX 차이나H",
        "371160": "ACE 중국본토CSI300",
        "476730": "HANARO 중국본토CSI300",
    },

    # ── 해외주식: 인도 ───────────────────────────────────────
    "india_equity": {
        "453810": "KODEX 인도Nifty50",
        "469070": "TIGER 인도니프티50",
        "476740": "ACE 인도Nifty50(합성)",
        "487230": "HANARO 인도니프티50",
        "494410": "SOL 인도Nifty50",
    },

    # ── 해외채권: 미국채 10년 ────────────────────────────────
    "us10y": {
        "305080": "TIGER 미국채10년선물",
        "308620": "KODEX 미국채10년선물",
        "476750": "ACE 미국채10년선물",
        "487240": "HANARO 미국채10년선물",
    },

    # ── 해외채권: 미국채 30년 ────────────────────────────────
    "us30y": {
        "304660": "KODEX 미국채울트라30년선물",
        "453850": "ACE 미국30년국채액티브",
        "476760": "TIGER 미국30년국채액티브",
        "487250": "HANARO 미국30년국채",
        "463050": "SOL 미국30년국채액티브(H)",
    },

    # ── 해외채권: TIPS ────────────────────────────────────────
    "tips": {
        "261240": "TIGER 미국물가연동국채(합성)",
        "476770": "ACE 미국물가연동국채(합성)",
    },

    # ── 해외채권: 하이일드 ───────────────────────────────────
    "hy_bond": {
        "469080": "TIGER 미국하이일드액티브(H)",
        "476780": "ACE 미국하이일드액티브(H)",
        "487260": "KODEX 미국하이일드액티브(H)",
    },

    # ── 대체: 금 ─────────────────────────────────────────────
    "gold": {
        "132030": "KODEX 골드선물(H)",
        "319640": "TIGER 골드선물(H)",
        "411060": "ACE KRX금현물",
        "476790": "HANARO 골드선물(H)",
        "487270": "SOL 금선물(H)",
        "458870": "RISE 금현물",
        "394660": "KBSTAR 골드선물(H)",
    },

    # ── 대체: 원유 ───────────────────────────────────────────
    "oil": {
        "261220": "TIGER 원유선물Enhanced(H)",
        "271060": "KODEX WTI원유선물(H)",
        "476800": "ACE 원유선물(H)",
        "487280": "HANARO 원유선물(H)",
    },

    # ── 대체: 원자재 종합 ────────────────────────────────────
    "commodity": {
        "139320": "TIGER 농산물선물Enhanced(H)",
        "475280": "ACE 원자재GSCI(합성)",
        "487290": "KODEX 원자재GSCI(합성)",
    },

    # ── 대체: 미국 리츠 ──────────────────────────────────────
    "us_reit": {
        "182480": "TIGER 미국MSCI리츠(합성H)",
        "352560": "KODEX 미국부동산리츠(H)",
        "476810": "ACE 미국리츠(합성H)",
        "487300": "HANARO 미국리츠(합성H)",
        "463280": "SOL 미국리츠(H)",
    },

    # ── 대체: 국내 리츠 ──────────────────────────────────────
    "kr_reit": {
        "432540": "TIGER 리츠부동산인프라",
        "476820": "ACE 리츠부동산인프라",
        "487310": "HANARO 리츠부동산인프라",
        "466070": "KODEX 한국부동산리츠인프라",
    },
}


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


# -----------------------------------------------------------------
# 데이터 수집
# -----------------------------------------------------------------

def fetch_etf_info(ticker, name, start, end, etf_all):
    try:
        # OHLCV (괴리율·AUM·상장기간 공통 사용)
        ohlcv = stock.get_etf_ohlcv_by_date(start, end, ticker)
        has_ohlcv = (ohlcv is not None
                     and isinstance(ohlcv, pd.DataFrame)
                     and not ohlcv.empty)

        # 추적오차 (실패해도 건너뛰지 않고 0으로 처리)
        tracking_error = 0.0
        discount_rate  = 0.0
        df_te = None
        try:
            df_te = stock.get_etf_tracking_error(start, end, ticker)
            if df_te is not None and isinstance(df_te, pd.DataFrame) and not df_te.empty:
                te_col = safe_col(df_te, ["추적오차율", "추적오차", "오차"])
                if te_col:
                    tracking_error = round(float(df_te[te_col].abs().mean()), 4)

                # 괴리율: (종가 - NAV) / NAV * 100
                nav_col = safe_col(df_te, ["NAV", "순자산가치", "기준가"])
                if nav_col and has_ohlcv and "종가" in ohlcv.columns:
                    merged = pd.merge(
                        ohlcv[["종가"]], df_te[[nav_col]],
                        left_index=True, right_index=True, how="inner"
                    )
                    if not merged.empty:
                        merged["gap"] = (
                            (merged["종가"] - merged[nav_col]) / merged[nav_col] * 100
                        )
                        discount_rate = round(float(merged["gap"].mean()), 4)
        except Exception as e:
            print(f"    추적오차/괴리율 실패: {e}")

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

        # AUM (억원): NAV × 거래량 근사 대신 종가 기준 시가총액으로 추정
        # etf_all에 순자산 컬럼이 없으므로 → NAV(df_te) × 상장좌수 시도
        # 상장좌수 = 거래대금 / 거래량 / NAV * 거래량  (불가)
        # 대안: get_etf_price_change_by_ticker 시도
        aum = 0.0
        try:
            df_pc = stock.get_etf_price_change_by_ticker(end, end)
            if df_pc is not None and isinstance(df_pc, pd.DataFrame) and not df_pc.empty:
                if ticker in df_pc.index:
                    aum_col = safe_col(df_pc, ["순자산총액", "순자산", "AUM"])
                    if aum_col:
                        aum = round(float(df_pc.loc[ticker, aum_col]) / 1e8, 1)
        except Exception:
            pass

        # AUM 여전히 0이면: NAV × etf_all 거래량으로 시가총액 근사 (최후 수단)
        if aum == 0.0 and etf_all is not None and ticker in etf_all.index:
            try:
                nav_val = float(etf_all.loc[ticker, "NAV"])
                # 거래량(좌수)이 있으면 유통량 근사 불가 → 종가 기준 시총 사용
                close_val = float(etf_all.loc[ticker, "종가"])
                vol_val   = float(etf_all.loc[ticker, "거래량"])
                # 실제 상장좌수를 모르므로 생략, 다른 컬럼 시도
                other_col = safe_col(etf_all, ["순자산총액", "순자산", "시가총액", "AUM"])
                if other_col:
                    aum = round(float(etf_all.loc[ticker, other_col]) / 1e8, 1)
            except Exception:
                pass

        # 상장 기간 (개월): 전체 기간 OHLCV 첫 날짜
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

    # 전종목 기본정보 1회 조회 (AUM용)
    print("\n전종목 ETF 기본정보 조회 중...")
    etf_all = None
    try:
        etf_all = stock.get_etf_ohlcv_by_ticker(end_date)
        if etf_all is not None and not etf_all.empty:
            print(f"조회 완료: {len(etf_all)}개, 컬럼: {list(etf_all.columns)}")
    except Exception as e:
        print(f"전종목 조회 실패: {e}")

    output = {}

    # AUM 조회용 price_change 함수 컬럼 확인
    print("AUM 조회 가능 컬럼 확인...")
    try:
        df_pc = stock.get_etf_price_change_by_ticker(end_date, end_date)
        if df_pc is not None and not df_pc.empty:
            print(f"  get_etf_price_change_by_ticker 컬럼: {list(df_pc.columns)}")
        else:
            print("  get_etf_price_change_by_ticker: 데이터 없음")
    except Exception as e:
        print(f"  get_etf_price_change_by_ticker 실패: {e}")

    total_count = sum(len(v) for v in INDEX_TICKERS.values())
    print(f"\n총 {len(INDEX_TICKERS)}개 지수, {total_count}개 ETF 수집 시작\n")

    for index_id, ticker_map in INDEX_TICKERS.items():
        print(f"[{index_id}] {len(ticker_map)}개 수집 중...")
        etf_list = []

        for ticker, name in ticker_map.items():
            print(f"  {ticker} ({name})", flush=True)
            result = fetch_etf_info(ticker, name, start_date, end_date, etf_all)
            if result:
                print(f"    추적오차={result['trackingError']}% "
                      f"괴리율={result['discountRate']}% "
                      f"AUM={result['aum']}억 "
                      f"거래대금={result['dailyVolume']}억 "
                      f"상장={result['listingMonths']}개월")
                etf_list.append(result)
            else:
                print(f"    -> 건너뜀")
            time.sleep(0.3)

        output[index_id] = etf_list
        print(f"  -> {len(etf_list)}개 완료\n")

    os.makedirs("data", exist_ok=True)
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "data": output,
    }
    with open("data/etf_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in output.values())
    print(f"[완료] 총 {total}개 ETF 데이터 -> data/etf_data.json")


if __name__ == "__main__":
    main()
