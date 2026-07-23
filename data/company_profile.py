"""
Company profile persistence — shared by Flask web + Kivy Android.
Stores company identity, preferences, NPWP, currency settings.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_PROFILE_FILENAME = 'ctm_company.json'

DEFAULT: Dict[str, Any] = {
    'company_name': '',
    'npwp': '',
    'address': '',
    'currency': 'IDR',
    'tax_year': 2026,
    'theme': 'light',
    'compact': False,
}


def profile_path(user_data_dir: Optional[str] = None,
                 fallback_dir: Optional[str] = None) -> str:
    base = user_data_dir or fallback_dir or os.getcwd()
    return os.path.join(base, _PROFILE_FILENAME)


def load_profile(path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    target = path or profile_path(**kwargs)
    try:
        if os.path.exists(target):
            with open(target, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = dict(DEFAULT)
                    merged.update(data)
                    return merged
    except Exception:
        pass
    return dict(DEFAULT)


def save_profile(profile: Dict[str, Any], path: Optional[str] = None,
                 **kwargs) -> bool:
    target = path or profile_path(**kwargs)
    try:
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
