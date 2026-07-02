# -*- coding: utf-8 -*-
"""資金繰り計算ロジック（フレームワーク非依存）。

Streamlit 版の compute_plan / compute_actual / compute_scenario /
evaluate_variance / export_to_excel をそのまま移植。
`st.session_state` への参照は、引数で受け取る dict `s` に置き換えている。
"""
import io

import numpy as np
import pandas as pd
from openpyxl import Workbook

from .constants import (
    ACTUAL_DEFAULT,
    ACTUAL_ROW_ORDER,
    MONTH_LABELS,
)


def compute_plan(s):
    """計画（予測）資金繰り表を計算して返す。

    返り値: 行=項目、列=[当月, 1ヶ月後, 2ヶ月後, 3ヶ月後, 合計] の DataFrame。
    """
    sales, purchase, capex = s['sales'], s['purchase'], s['capex']
    monthly_int = s['loan_balance'] * s['loan_rate'] / 12
    cash_sales = [sales[i] * s['collect_cash'] for i in range(2, 6)]
    coll_1m = [sales[i - 1] * s['collect_1m'] for i in range(2, 6)]
    coll_2m = [sales[i - 2] * s['collect_2m'] for i in range(2, 6)]
    op_in = [a + b + c for a, b, c in zip(cash_sales, coll_1m, coll_2m)]
    cash_purch = [purchase[i] * s['pay_cash'] for i in range(2, 6)]
    pay_1m = [purchase[i - 1] * s['pay_1m'] for i in range(2, 6)]
    pay_2m = [purchase[i - 2] * s['pay_2m'] for i in range(2, 6)]
    fixed = [s['personnel'] + s['rent'] + s['utility'] + s['telecom'] + s['other_exp'] + s['tax']] * 4
    op_out = [cash_purch[i] + pay_1m[i] + pay_2m[i] + fixed[i] for i in range(4)]
    op_diff = [op_in[i] - op_out[i] for i in range(4)]
    fin_total = [s['new_loan'] - s['loan_repay'] - monthly_int] * 4
    inv_total = [-capex[i] for i in range(2, 6)]
    month_cf = [op_diff[i] + fin_total[i] + inv_total[i] for i in range(4)]
    balances, prev_balances = [], []
    prev = s['opening_cash']
    for i in range(4):
        prev_balances.append(prev)
        prev = prev + month_cf[i]
        balances.append(prev)
    df = pd.DataFrame({
        '前月繰越現金': prev_balances, '現金売上': cash_sales,
        '売掛金回収（前月分）': coll_1m, '売掛金回収（前々月分）': coll_2m,
        '営業収入合計（A）': op_in,
        '現金仕入': cash_purch, '買掛金支払（前月分）': pay_1m,
        '買掛金支払（前々月分）': pay_2m, '固定費合計': fixed,
        '営業支出合計（B）': op_out, '営業収支差額（A－B）': op_diff,
        '財務収支合計（C）': fin_total, '投資収支合計（D）': inv_total,
        '当月収支合計': month_cf, '翌月繰越現金': balances,
    }, index=MONTH_LABELS).T
    df['合計'] = df.sum(axis=1)
    df.loc[['前月繰越現金', '翌月繰越現金'], '合計'] = np.nan
    return df


def get_actual_default_df():
    """実績入力の既定値を DataFrame（行=項目, 列=月）で返す。"""
    return pd.DataFrame(
        {k: ACTUAL_DEFAULT[k] for k in ACTUAL_ROW_ORDER},
        index=MONTH_LABELS,
    ).T


def actual_dict_to_df(actual_dict):
    """セッション保持の dict（row -> [4値]）を DataFrame に変換。"""
    return pd.DataFrame(
        {k: actual_dict[k] for k in ACTUAL_ROW_ORDER},
        index=MONTH_LABELS,
    ).T


def compute_actual(s, actual_input):
    """実績入力から実績ベースの資金繰り集計を計算する。

    actual_input: 行=入力項目, 列=月 の DataFrame。
    """
    op_in = actual_input.loc[['現金売上', '売掛金回収（前月分）', '売掛金回収（前々月分）']].sum()
    op_out = actual_input.loc[['現金仕入', '買掛金支払（前月分）', '買掛金支払（前々月分）', '固定費合計']].sum()
    op_diff = op_in - op_out
    fin_total = actual_input.loc['財務収支合計（C）']
    inv_total = actual_input.loc['投資収支合計（D）']
    month_cf = op_diff + fin_total + inv_total
    balances, prev_balances = [], []
    prev = s['opening_cash']
    for col in MONTH_LABELS:
        prev_balances.append(prev)
        prev = prev + month_cf[col]
        balances.append(prev)
    return pd.DataFrame({
        '前月繰越現金': prev_balances,
        '営業収入合計（A）': op_in.values, '営業支出合計（B）': op_out.values,
        '営業収支差額（A－B）': op_diff.values, '財務収支合計（C）': fin_total.values,
        '投資収支合計（D）': inv_total.values, '当月収支合計': month_cf.values,
        '翌月繰越現金': balances,
    }, index=MONTH_LABELS).T


def compute_scenario(s, scenario):
    """シナリオ別（楽観／基準／悲観）の月末残高推移を返す。"""
    p = {
        '楽観': dict(sales=1.10, purchase=0.95, fixed=0.98, bad=0, new_loan=0),
        '基準': dict(sales=1.00, purchase=1.00, fixed=1.00, bad=0, new_loan=0),
        '悲観': dict(sales=0.85, purchase=1.08, fixed=1.05, bad=2000, new_loan=3000),
    }[scenario]
    fixed_total = s['personnel'] + s['rent'] + s['utility'] + s['telecom'] + s['other_exp'] + s['tax']
    monthly_int = s['loan_balance'] * s['loan_rate'] / 12
    balances = [s['opening_cash']]
    for i in range(4):
        cf = (s['sales'][2 + i] * p['sales'] - s['purchase'][2 + i] * p['purchase']
              - fixed_total * p['fixed'] - s['loan_repay'] - monthly_int
              - s['capex'][2 + i] - (p['bad'] if i == 2 else 0) + (p['new_loan'] if i == 1 else 0))
        balances.append(balances[-1] + cf)
    return balances


def evaluate_variance(diff_rate, item_type):
    """差異率から評価ラベル（○良好／△要確認／×悪化）を返す。"""
    if item_type == 'revenue':
        if diff_rate >= 0:
            return '○良好'
        elif diff_rate > -0.10:
            return '△要確認'
        else:
            return '×悪化'
    else:
        if diff_rate <= 0:
            return '○良好'
        elif diff_rate < 0.10:
            return '△要確認'
        else:
            return '×悪化'


def eval_css_class(val):
    """評価ラベルから CSS クラス名を返す（Streamlit の style_eval 相当）。"""
    s = str(val)
    if '○' in s:
        return 'eval-good'
    if '△' in s:
        return 'eval-warn'
    if '×' in s:
        return 'eval-bad'
    return ''


def export_to_excel(plan_df, actual_df):
    """計画表＋実績入力表を xlsx バイト列で返す。"""
    wb = Workbook()
    ws1 = wb.active
    ws1.title = '月次資金繰り表'
    ws1.append(['項目'] + list(plan_df.columns))
    for idx, row in plan_df.iterrows():
        ws1.append([idx] + [None if pd.isna(v) else float(v) for v in row.values])
    ws2 = wb.create_sheet('実績入力')
    ws2.append(['項目'] + list(actual_df.columns))
    for idx, row in actual_df.iterrows():
        ws2.append([idx] + [None if pd.isna(v) else float(v) for v in row.values])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
