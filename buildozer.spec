[app]

title = Corporate Tax Manager
package.name = corporatetax
package.domain = org.neofidao
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,txt
source.include_patterns = data/*.py,data/**
version = 1.1.4
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.accept_sdk_license = True
android.allow_backup = True
android.logcat_filters = *:S python:D
presplash.color = #1B2A4A

[buildozer]

log_level = 2
warn_on_root = 0
