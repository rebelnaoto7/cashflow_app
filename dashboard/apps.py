# -*- coding: utf-8 -*-
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = '月次資金繰りダッシュボード'
