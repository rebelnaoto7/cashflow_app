# -*- coding: utf-8 -*-
"""dashboard アプリの URL 設定。"""
from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('reset/', views.reset_view, name='reset'),
    path('download/excel/', views.download_excel, name='download_excel'),
]
