[app]
title = Smart Expense Tracker
package.name = smart_expense_tracker
package.domain = com.smartexpense.tracker
source.dir = .
source.include_exts = py,png,jpg,jpeg,svg,html,css,js,db,json,txt
source.exclude_dirs = tests, .venv, .github, .git, exports, ml_models
version = 1.0.0
requirements = python3, sqlite3, flask, flask-sqlalchemy, flask-login, flask-wtf, wtforms, werkzeug, python-dotenv, requests, openpyxl

orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# (str) Bootstrap to use for android builds
# Options are: sdl2, webview, service_only
p4a.bootstrap = webview

# (int) Port to use for webview bootstrap
p4a.port = 5000

# Android SDK / NDK Specifications
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
