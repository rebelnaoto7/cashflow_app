# -*- coding: utf-8 -*-
"""ビュー：ダッシュボード本体と Excel ダウンロード。

Streamlit の 5 タブ構成を、1 ページ + Bootstrap タブで再現する。
状態は Django セッションに保持し、フォーム送信のたびに全タブを再計算する。
"""
import json
from datetime import datetime

import pandas as pd
from django.http import HttpResponse
from django.shortcuts import redirect, render

from . import services
from .constants import (
    ACTUAL_ROW_ORDER,
    DEFAULTS,
    MONTH_LABELS,
    PERIOD_LABELS,
    RENAME_MAP,
    VARIANCE_COMPARE,
)
from .forms import AssumptionsForm

# セッションキー
SK_STATE = 'cf_state'
SK_ACTUAL = 'cf_actual'


# ----------------------------------------------------------------------
# セッション状態の取得・保存
# ----------------------------------------------------------------------
def _get_state(request):
    """セッションから前提条件 dict を取得（無ければ既定値）。"""
    state = request.session.get(SK_STATE)
    if not state:
        state = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    return state


def _get_actual(request):
    """セッションから実績入力 dict を取得（無ければ既定値）。"""
    actual = request.session.get(SK_ACTUAL)
    if not actual:
        from .constants import ACTUAL_DEFAULT
        actual = {k: list(v) for k, v in ACTUAL_DEFAULT.items()}
    return actual


# ----------------------------------------------------------------------
# 整形ヘルパー
# ----------------------------------------------------------------------
def _fmt(v, spec='{:,.0f}'):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    return spec.format(v)

def _man(v, spec='{:,.1f}'):
    """千円値を万円に変換して整形（1万円 = 10千円）。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    return spec.format(v / 10)

def _row_css(label):
    if '🔵' in label:
        return 'row-final'
    if '■' in label:
        return 'row-major'
    if '▶' in label:
        return 'row-cat'
    if '🟡' in label:
        return 'row-open'
    return ''


# ----------------------------------------------------------------------
# Plotly.js 用の図仕様（dict）を生成
# ----------------------------------------------------------------------
def _build_figures(state, plan_df, balances_kpi, scenarios):
    min_cash = state['min_cash']

    # Tab1-1: 現金残高推移
    fig_balance = {
        'data': [
            {
                'type': 'bar', 'name': '現金残高',
                'x': PERIOD_LABELS, 'y': [v / 10 for v in balances_kpi],
                'marker': {'color': ['#1F4E78' if v >= min_cash else '#C00000' for v in balances_kpi]},
                'text': [f'{v/10:,.1f}' for v in balances_kpi], 'textposition': 'outside',
            },
            {
                'type': 'scatter', 'mode': 'lines', 'name': '最低必要残高',
                'x': PERIOD_LABELS, 'y': [min_cash] * 5,
                'line': {'color': 'red', 'dash': 'dash'},
            },
        ],
        'layout': {'height': 420, 'yaxis': {'title': {'text': '残高（千円）'}},
                   'margin': {'t': 30}},
    }

    # Tab1-2: 月次キャッシュフロー構成
    fig_cf = {
        'data': [
            {'type': 'bar', 'name': '営業CF', 'x': MONTH_LABELS,
             'y': list(plan_df.loc['営業収支差額（A－B）', MONTH_LABELS].values),
             'marker': {'color': '#2E75B6'}},
            {'type': 'bar', 'name': '財務CF', 'x': MONTH_LABELS,
             'y': list(plan_df.loc['財務収支合計（C）', MONTH_LABELS].values),
             'marker': {'color': '#A9D18E'}},
            {'type': 'bar', 'name': '投資CF', 'x': MONTH_LABELS,
             'y': list(plan_df.loc['投資収支合計（D）', MONTH_LABELS].values),
             'marker': {'color': '#FFC000'}},
            {'type': 'scatter', 'name': '月末残高', 'mode': 'lines+markers',
             'x': MONTH_LABELS,
             'y': list(plan_df.loc['翌月繰越現金', MONTH_LABELS].values),
             'line': {'color': '#1F4E78', 'width': 3}, 'yaxis': 'y2'},
        ],
        'layout': {
            'barmode': 'relative', 'height': 420,
            'yaxis': {'title': {'text': '月次CF（千円）'}},
            'yaxis2': {'title': {'text': '月末残高（千円）'}, 'overlaying': 'y', 'side': 'right'},
            'margin': {'t': 30},
        },
    }

    # Tab4: シナリオ分析
    bo, bb, bp = scenarios['楽観'], scenarios['基準'], scenarios['悲観']
    fig_scenario = {
        'data': [
            {'type': 'scatter', 'mode': 'lines+markers', 'name': '楽観',
             'x': PERIOD_LABELS, 'y': bo, 'line': {'color': '#70AD47', 'width': 3}},
            {'type': 'scatter', 'mode': 'lines+markers', 'name': '基準',
             'x': PERIOD_LABELS, 'y': bb, 'line': {'color': '#1F4E78', 'width': 3}},
            {'type': 'scatter', 'mode': 'lines+markers', 'name': '悲観',
             'x': PERIOD_LABELS, 'y': bp, 'line': {'color': '#C00000', 'width': 3}},
            {'type': 'scatter', 'mode': 'lines', 'name': '最低必要残高',
             'x': PERIOD_LABELS, 'y': [min_cash] * 5, 'line': {'color': 'orange', 'dash': 'dash'}},
        ],
        'layout': {'height': 440, 'yaxis': {'title': {'text': '残高（千円）'}}, 'margin': {'t': 30}},
    }

    return {
        'balance': json.dumps(fig_balance),
        'cf': json.dumps(fig_cf),
        'scenario': json.dumps(fig_scenario),
    }


# ----------------------------------------------------------------------
# メインビュー
# ----------------------------------------------------------------------
def index(request):
    state = _get_state(request)
    actual = _get_actual(request)
    var_month = MONTH_LABELS[0]

    if request.method == 'POST':
        # 1) 前提条件フォーム
        form = AssumptionsForm(request.POST)
        if form.is_valid():
            state = form.to_state()
            request.session[SK_STATE] = state

        # 2) 実績入力グリッド（actual_{row}_{month}）
        new_actual = {}
        for r_idx, row in enumerate(ACTUAL_ROW_ORDER):
            vals = []
            for m_idx in range(len(MONTH_LABELS)):
                raw = request.POST.get(f'actual_{r_idx}_{m_idx}', '')
                try:
                    vals.append(float(raw))
                except (TypeError, ValueError):
                    vals.append(actual.get(row, [0, 0, 0, 0])[m_idx])
            new_actual[row] = vals
        actual = new_actual
        request.session[SK_ACTUAL] = actual

        # 3) 予実差異の表示月
        var_month = request.POST.get('var_month', MONTH_LABELS[0])
        if var_month not in MONTH_LABELS:
            var_month = MONTH_LABELS[0]
    else:
        form = AssumptionsForm(initial=AssumptionsForm.initial_from_state(state))

    # ===== 計算 =====
    plan_df = services.compute_plan(state)
    actual_df = services.actual_dict_to_df(actual)
    actual_derived = services.compute_actual(state, actual_df)

    # KPI
    balances_kpi = [state['opening_cash']] + plan_df.loc['翌月繰越現金', MONTH_LABELS].tolist()
    op_cf_total = plan_df.loc['営業収支差額（A－B）', MONTH_LABELS].sum()
    min_bal = min(balances_kpi)
    min_cash = state['min_cash']

    kpis = [
        {'label': '当月末残高', 'value': _man(balances_kpi[1]) + ' 万円',
         'delta': _man(balances_kpi[1] - state['opening_cash'], '{:+,.1f}'),
         'good': balances_kpi[1] - state['opening_cash'] >= 0},
        {'label': '3ヶ月後残高', 'value': _man(balances_kpi[-1]) + ' 万円',
         'delta': _man(balances_kpi[-1] - state['opening_cash'], '{:+,.1f}'),
         'good': balances_kpi[-1] - state['opening_cash'] >= 0},
        {'label': '期間中最低', 'value': _man(min_bal) + ' 万円',
         'delta': _man(min_bal - min_cash, '{:+,.1f}'),
         'good': min_bal >= min_cash},
        {'label': '営業CF合計', 'value': _man(op_cf_total) + ' 万円',
         'delta': '', 'good': op_cf_total >= 0},
    ]

    balance_alert_ok = min_bal >= min_cash

    # Tab2: 計画表
    plan_cols = list(plan_df.columns)  # 当月..3ヶ月後, 合計
    plan_rows = []
    for idx in plan_df.index:
        label = RENAME_MAP.get(idx, idx)
        plan_rows.append({
            'label': label,
            'css': _row_css(label),
            'values': [_man(plan_df.loc[idx, c]) for c in plan_cols],
        })

    # Tab3: 実績入力グリッド
    actual_grid = []
    for r_idx, row in enumerate(ACTUAL_ROW_ORDER):
        actual_grid.append({
            'row_index': r_idx,
            'label': row,
            'cells': [
                {'name': f'actual_{r_idx}_{m_idx}', 'value': actual[row][m_idx]}
                for m_idx in range(len(MONTH_LABELS))
            ],
        })

    # Tab3: 予実差異
    variance_rows = []
    for item, t in VARIANCE_COMPARE:
        if item not in plan_df.index or item not in actual_derived.index:
            continue
        p = plan_df.loc[item, var_month]
        a = actual_derived.loc[item, var_month]
        d = a - p
        r = d / abs(p) if p != 0 else 0
        ev = services.evaluate_variance(r, t)
        variance_rows.append({
            'item': item, 'plan': _man(p), 'actual': _man(a),
            'diff': _man(d, '{:+,.1f}'), 'rate': _fmt(r, '{:+.1%}'),
            'eval': ev, 'eval_css': services.eval_css_class(ev),
        })

    # Tab4: シナリオ
    scenarios = {name: services.compute_scenario(state, name) for name in ('楽観', '基準', '悲観')}
    bo, bb, bp = scenarios['楽観'], scenarios['基準'], scenarios['悲観']
    scenario_metrics = [
        {'label': '楽観 最終', 'value': _man(bo[-1]), 'good': True},
        {'label': '基準 最終', 'value': _man(bb[-1]), 'good': True},
        {'label': '悲観 最終', 'value': _man(bp[-1]), 'good': True},
        {'label': '悲観 最低', 'value': _man(min(bp)),
         'delta': _man(min(bp) - min_cash, '{:+,.1f}'), 'good': min(bp) >= min_cash},
    ]
    scenario_rows = []
    for i, period in enumerate(PERIOD_LABELS):
        scenario_rows.append({
            'period': period,
            'opt': _man(bo[i]), 'base': _man(bb[i]), 'pess': _man(bp[i]),
            'gap': _man(bp[i] - bo[i]),
        })
    scenario_ok = min(bp) >= min_cash
    if scenario_ok:
        scenario_actions = ['余剰資金の運用検討', '設備投資前倒しの検討',
                            '内部留保戦略の見直し', '新規事業への原資検討']
        scenario_msg = '✅ 悲観でも最低残高を上回る見込み'
    else:
        scenario_actions = ['銀行への事前相談', '売掛回収サイトの短縮交渉',
                            '買掛支払サイトの延長交渉', '固定費の緊急見直し',
                            '設備投資・大型支出の延期検討']
        scenario_msg = f'⚠️ 悲観で {_man(min_cash - min(bp))}万円 不足見込み'

    figures = _build_figures(state, plan_df, balances_kpi, scenarios)

    context = {
        'form': form,
        'form_groups': form.grouped(),
        'kpis': kpis,
        'balance_alert_ok': balance_alert_ok,
        'min_cash': _man(min_cash),
        'plan_cols': plan_cols,
        'plan_rows': plan_rows,
        'month_labels': MONTH_LABELS,
        'actual_grid': actual_grid,
        'variance_rows': variance_rows,
        'var_month': var_month,
        'scenario_metrics': scenario_metrics,
        'scenario_rows': scenario_rows,
        'scenario_ok': scenario_ok,
        'scenario_actions': scenario_actions,
        'scenario_msg': scenario_msg,
        'figures': figures,
    }
    return render(request, 'dashboard/index.html', context)


def reset_view(request):
    """セッションをクリアして既定値に戻す。"""
    request.session.pop(SK_STATE, None)
    request.session.pop(SK_ACTUAL, None)
    return redirect('dashboard:index')


def download_excel(request):
    """計画表＋実績入力表を xlsx でダウンロード。"""
    state = _get_state(request)
    actual = _get_actual(request)
    plan_df = services.compute_plan(state)
    actual_df = services.actual_dict_to_df(actual)
    data = services.export_to_excel(plan_df, actual_df)

    fn = f"資金繰り_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    resp = HttpResponse(
        data,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    from urllib.parse import quote
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(fn)}"
    return resp
