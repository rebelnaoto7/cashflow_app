#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Django の管理コマンド用エントリポイント。"""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cashflow_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django をインポートできませんでした。仮想環境が有効か、"
            "Django がインストールされているか確認してください。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
