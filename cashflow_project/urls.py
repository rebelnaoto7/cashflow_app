# -*- coding: utf-8 -*-
"""プロジェクトのルート URL 設定。"""
from django.urls import include, path

urlpatterns = [
    path('', include('dashboard.urls')),
]
