# -*- coding: utf-8 -*-
"""サイドバー（前提条件）入力フォーム。

Streamlit の st.number_input 群を Django フォームに移植。
6ヶ月分のリスト項目（sales / purchase / capex）は *_0〜*_5 の個別フィールドで表現する。
"""
from django import forms

from .constants import LABELS6


def _num(widget_attrs, **kwargs):
    attrs = {'class': 'form-control form-control-sm'}
    attrs.update(widget_attrs)
    return forms.FloatField(widget=forms.NumberInput(attrs=attrs), **kwargs)


class AssumptionsForm(forms.Form):
    """前提条件（資金繰りの入力パラメータ）。"""

    # 回収サイト（%）
    collect_cash = _num({'step': 'any', 'min': '0', 'max': '1'}, label='当月現金売上比率')
    collect_1m   = _num({'step': 'any', 'min': '0', 'max': '1'}, label='翌月入金比率')
    collect_2m   = _num({'step': 'any', 'min': '0', 'max': '1'}, label='翌々月入金比率')

    # 支払サイト（%）
    pay_cash = _num({'step': 'any', 'min': '0', 'max': '1'}, label='当月現金仕入比率')
    pay_1m   = _num({'step': 'any', 'min': '0', 'max': '1'}, label='翌月支払比率')
    pay_2m   = _num({'step': 'any', 'min': '0', 'max': '1'}, label='翌々月支払比率')

    # 固定費（万円/月）
    personnel = _num({'step': 'any'}, label='人件費')
    rent      = _num({'step': 'any'}, label='家賃')
    utility   = _num({'step': 'any'}, label='水道光熱費')
    telecom   = _num({'step': 'any'}, label='通信費')
    other_exp = _num({'step': 'any'}, label='その他経費')
    tax       = _num({'step': 'any'}, label='税金支払')

    # 借入金
    loan_balance = _num({'step': 'any'}, label='借入金残高（万円）')
    loan_rate    = _num({'step': 'any', 'min': '0', 'max': '0.20'}, label='年利率')
    loan_repay   = _num({'step': 'any'}, label='月次返済（万円）')
    new_loan     = _num({'step': 'any'}, label='月次新規借入（万円）')

    # 現金（万円）
    opening_cash = _num({'step': 'any'}, label='期首現金残高')
    min_cash     = _num({'step': 'any'}, label='最低必要残高')

    # リスト項目（sales/purchase/capex）は __init__ で動的に追加する。
    LIST_FIELDS = (
        ('sales', '売上', 'any'),
        ('purchase', '仕入', 'any'),
        ('capex', '設備投資', 'any'),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for prefix, label, step in self.LIST_FIELDS:
            for i, lab in enumerate(LABELS6):
                self.fields[f'{prefix}_{i}'] = _num(
                    {'step': step}, label=f'{label} {lab}'
                )

        # 金額項目（万円で入力 → 内部は千円: ×10）
    MONEY_FIELDS = (
        'personnel', 'rent', 'utility', 'telecom', 'other_exp', 'tax',
        'loan_balance', 'loan_repay', 'new_loan',
        'opening_cash', 'min_cash',
    )
    # 比率項目（変換しない）
    RATE_FIELDS = (
        'collect_cash', 'collect_1m', 'collect_2m',
        'pay_cash', 'pay_1m', 'pay_2m',
        'loan_rate',
    )

    def to_state(self):
        """バリデーション済みデータを services が期待する dict 形式へ変換。
        金額は万円入力 → 千円（×10）に変換。比率はそのまま。"""
        cd = self.cleaned_data
        state = {
            'sales': [cd[f'sales_{i}'] * 10 for i in range(6)],
            'purchase': [cd[f'purchase_{i}'] * 10 for i in range(6)],
            'capex': [cd[f'capex_{i}'] * 10 for i in range(6)],
        }
        for key in self.MONEY_FIELDS:
            state[key] = cd[key] * 10
        for key in self.RATE_FIELDS:
            state[key] = cd[key]
        return state

    @classmethod
    def initial_from_state(cls, state):
        """state dict（千円）から、フォーム初期値 dict（万円）を作る。"""
        initial = dict(state)
        # 金額項目: 千円 → 万円（÷10）で入力欄に表示
        for key in cls.MONEY_FIELDS:
            if key in initial and initial[key] is not None:
                initial[key] = initial[key] / 10
        for prefix in ('sales', 'purchase', 'capex'):
            for i in range(6):
                initial[f'{prefix}_{i}'] = state[prefix][i] / 10
            initial.pop(prefix, None)
        return initial
    
    # ---- テンプレート用：アコーディオングルーピング ----
    def grouped(self):
        """サイドバーをカテゴリ別（expander 相当）に並べるための構造を返す。"""
        def f(name):
            return self[name]

        list_rows = {}
        for prefix, _label, _step in self.LIST_FIELDS:
            list_rows[prefix] = [self[f'{prefix}_{i}'] for i in range(6)]

        return [
            ('💴 売上計画（万円）', list_rows['sales']),
            ('📅 回収サイト（％）', [f('collect_cash'), f('collect_1m'), f('collect_2m')]),
            ('📦 仕入計画（万円）', list_rows['purchase']),
            ('💳 支払サイト（％）', [f('pay_cash'), f('pay_1m'), f('pay_2m')]),
            ('🏢 固定費（万円/月）', [f('personnel'), f('rent'), f('utility'),
                                f('telecom'), f('other_exp'), f('tax')]),
            ('🏦 借入金', [f('loan_balance'), f('loan_rate'), f('loan_repay'), f('new_loan')]),
            ('🏗 投資計画（万円）', list_rows['capex']),
            ('💰 現金（万円）', [f('opening_cash'), f('min_cash')]),
        ]

