# -*- coding: utf-8 -*-
"""Django 設定ファイル（月次資金繰りダッシュボード）。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 開発用。本番では環境変数から読み込み、必ず変更すること。
SECRET_KEY = 'django-insecure-change-me-cashflow-dashboard-dev-key'

# 本番では False にすること。
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cashflow_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'cashflow_project.wsgi.application'

# DB は使用しないが、session をファイルベースで保持する。
DATABASES = {}
SESSION_ENGINE = 'django.contrib.sessions.backends.file'

LANGUAGE_CODE = 'ja'
# 既定は東京。環境により zoneinfo が無い場合は環境変数 TIME_ZONE で上書き可能。
TIME_ZONE = os.environ.get('TIME_ZONE', 'Asia/Tokyo')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
