[app]

title = Corporate Tax Manager
package.name = corporatetax
package.domain = org.neofidao
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,txt
source.include_patterns = data/*.py,data/**
version = 1.2.1
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
android.extra_xml = res/xml/file_paths.xml
android.extra_manifest_application = <provider android:name="androidx.core.content.FileProvider" android:authorities="${applicationId}.fileprovider" android:exported="false" android:grantUriPermissions="true"><meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/file_paths" /></provider>
presplash.color = #1B2A4A

[buildozer]

log_level = 2
warn_on_root = 0
