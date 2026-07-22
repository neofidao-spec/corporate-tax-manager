"""
App preferences (pure Python, no Kivy dependency).
Used by Android main.py for density/UI prefs persistence.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


APP_VERSION = '1.1.1'
_PREFS_FILENAME = 'ctm_prefs.json'


def prefs_path(user_data_dir: Optional[str] = None, fallback_dir: Optional[str] = None) -> str:
    """Resolve prefs file path.

    Priority:
    1) user_data_dir (Android Kivy App.user_data_dir)
    2) fallback_dir (usually project root / main.py dir)
    3) cwd
    """
    base = user_data_dir or fallback_dir or os.getcwd()
    return os.path.join(base, _PREFS_FILENAME)


def load_prefs(path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    target = path or prefs_path(**kwargs)
    try:
        if os.path.exists(target):
            with open(target, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def save_prefs(prefs: Dict[str, Any], path: Optional[str] = None, **kwargs) -> bool:
    target = path or prefs_path(**kwargs)
    try:
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
