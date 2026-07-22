"""
Share helpers for exported files.

Pure-Python core (testable without Kivy/Android). Android Intent is attempted
via pyjnius when available; otherwise falls back to clipboard/path text.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional, Tuple


def build_share_message(path: str, title: str = 'Export CSV') -> str:
    name = os.path.basename(path) if path else ''
    return f'{title}\n{name}\n{path}'.strip()


def try_android_share_file(
    path: str,
    title: str = 'Bagikan CSV',
    mime: str = 'text/csv',
    jnius_autoclass: Optional[Callable[[str], Any]] = None,
) -> Tuple[bool, str]:
    """Attempt Android ACTION_SEND share sheet.

    Returns (ok, detail). Inject jnius_autoclass for tests.
    """
    if not path or not os.path.exists(path):
        return False, 'File tidak ditemukan'

    try:
        autoclass_fn: Callable[[str], Any]
        if jnius_autoclass is None:
            from jnius import autoclass as _autoclass  # type: ignore
            autoclass_fn = _autoclass
        else:
            autoclass_fn = jnius_autoclass

        Intent = autoclass_fn('android.content.Intent')
        Uri = autoclass_fn('android.net.Uri')
        File = autoclass_fn('java.io.File')
        PythonActivity = autoclass_fn('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity

        intent = Intent()
        intent.setAction(Intent.ACTION_SEND)
        intent.setType(mime)
        java_file = File(path)
        uri = Uri.fromFile(java_file)
        intent.putExtra(Intent.EXTRA_STREAM, uri)
        intent.putExtra(Intent.EXTRA_SUBJECT, title)
        intent.putExtra(Intent.EXTRA_TEXT, build_share_message(path, title))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        chooser = Intent.createChooser(intent, title)
        activity.startActivity(chooser)
        return True, 'share_sheet'
    except Exception as exc:
        return False, str(exc)


def try_clipboard_copy(
    text: str,
    clipboard_paste: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """Copy text to clipboard. Inject clipboard_paste for tests."""
    if not text:
        return False, 'Teks kosong'
    try:
        paste_fn: Callable[[str], None]
        if clipboard_paste is None:
            from kivy.core.clipboard import Clipboard  # type: ignore
            paste_fn = Clipboard.copy
        else:
            paste_fn = clipboard_paste
        paste_fn(text)
        return True, 'clipboard'
    except Exception as exc:
        return False, str(exc)


def share_or_copy(
    path: str,
    title: str = 'Bagikan CSV',
    jnius_autoclass: Optional[Callable[[str], Any]] = None,
    clipboard_paste: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Prefer Android share sheet; fall back to clipboard path text."""
    result: Dict[str, Any] = {
        'path': path,
        'shared': False,
        'copied': False,
        'mode': None,
        'detail': '',
        'message': build_share_message(path, title),
    }
    ok, detail = try_android_share_file(
        path, title=title, jnius_autoclass=jnius_autoclass,
    )
    if ok:
        result.update(shared=True, mode='share_sheet', detail=detail)
        return result

    cop_ok, cop_detail = try_clipboard_copy(
        result['message'], clipboard_paste=clipboard_paste,
    )
    if cop_ok:
        result.update(copied=True, mode='clipboard', detail=cop_detail)
        return result

    result['detail'] = f'share={detail}; clipboard={cop_detail}'
    result['mode'] = 'path_only'
    return result
