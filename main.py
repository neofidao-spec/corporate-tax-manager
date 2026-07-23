"""
Corporate Tax Manager — Kivy Android App
Pure Python UI. Crash-safe. Matches tax_calculator.py & tax_db.py APIs.
"""
import os
import sys
import calendar
import traceback
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.utils import get_color_from_hex as hex2rgb
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior

from data.tax_calculator import TaxCalculator
from data.tax_db import TaxDB
from data.app_prefs import APP_VERSION, load_prefs as _load_prefs, save_prefs as _save_prefs, prefs_path as _prefs_path_impl
from data.export_utils import (
    export_pph21_csv,
    export_withholding_csv,
    export_period_report_csv,
)
from data.share_utils import share_or_copy

# ═══════════════════════════════════════════════════════════
# THEME — Neutral (eye-friendly, matches web)
# ═══════════════════════════════════════════════════════════
BG = hex2rgb('#F4F6F8')
SURFACE = hex2rgb('#FFFFFF')
SURFACE_MUTED = hex2rgb('#EEF1F4')
PRIMARY = hex2rgb('#3B4F6A')
PRIMARY_HOVER = hex2rgb('#32445C')
ACCENT = hex2rgb('#4A6FA5')
TEXT = hex2rgb('#1F2937')
TEXT_SECONDARY = hex2rgb('#4B5563')
SUBTLE = hex2rgb('#6B7280')
WHITE = (1, 1, 1, 1)
ERROR = hex2rgb('#8F1A12')
GREEN = hex2rgb('#1B5E3B')
WARNING = hex2rgb('#8A5A0A')
BORDER = hex2rgb('#E2E8F0')
SURFACE_HOVER = hex2rgb('#FAFBFC')

# Dark theme tokens
BG_D = hex2rgb('#121820')
SURFACE_D = hex2rgb('#1E293B')
SURFACE_MUTED_D = hex2rgb('#1A2636')
PRIMARY_D = hex2rgb('#8EACCE')
PRIMARY_HOVER_D = hex2rgb('#7B9ABD')
ACCENT_D = hex2rgb('#A0BFE0')
TEXT_D = hex2rgb('#E2E8F0')
TEXT_SECONDARY_D = hex2rgb('#B0BED0')
SUBTLE_D = hex2rgb('#8899AF')
BORDER_D = hex2rgb('#2D3B4F')
SURFACE_HOVER_D = hex2rgb('#243348')

# Active theme (swapped by toggle_dark_mode)
THEME = {
    'bg': BG, 'surface': SURFACE, 'surface_muted': SURFACE_MUTED,
    'primary': PRIMARY, 'primary_hover': PRIMARY_HOVER, 'accent': ACCENT,
    'text': TEXT, 'text_secondary': TEXT_SECONDARY, 'subtle': SUBTLE,
    'border': BORDER, 'surface_hover': SURFACE_HOVER,
    'is_dark': False
}

# Backward-compatible aliases used in screens
NAVY = PRIMARY
CHARCOAL = TEXT_SECONDARY
CREAM = BG
CREAM_D = SURFACE_MUTED
COPPER = ACCENT
PAPER = SURFACE


def _prefs_path():
    """User prefs file — works on desktop and Android (user_data_dir)."""
    try:
        app = App.get_running_app()
        if app and getattr(app, 'user_data_dir', None):
            return _prefs_path_impl(user_data_dir=app.user_data_dir)
    except Exception:
        pass
    base = os.path.dirname(os.path.abspath(__file__))
    return _prefs_path_impl(fallback_dir=base)


def load_prefs():
    return _load_prefs(path=_prefs_path())


def save_prefs(prefs):
    return _save_prefs(prefs, path=_prefs_path())


def make_label(text, size=14, color=None, bold=False, halign='left', height=None):
    widget = Label(
        text=str(text),
        font_size=sp(size),
        color=color or THEME['text'],
        bold=bold,
        halign=halign,
        valign='middle',
    )
    widget.size_hint_y = None
    # Slightly tighter vertical rhythm for readability on small screens
    widget.height = dp(height or (size + 12))
    widget.bind(size=lambda w, _v: setattr(w, 'text_size', (w.width, None)))
    return widget


def make_button(text, bg=None, fg=None, height=42):
    btn = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal='',
        background_color=bg or THEME['primary'],
        color=fg or WHITE,
        font_size=sp(12.5),
        bold=True,
    )
    # Auto-set accessibility
    desc = text.replace('✕', 'Hapus ').replace('<', 'Sebelumnya').replace('>', 'Selanjutnya')
    try:
        btn.description_for_accessibility = desc
    except Exception:
        pass
    return btn


def paint_card(widget):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*THEME['surface'])
        widget._card_bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(12)])
    widget.bind(
        pos=lambda w, _v: setattr(w._card_bg, 'pos', w.pos),
        size=lambda w, _v: setattr(w._card_bg, 'size', w.size),
    )


def paint_bar(widget, color=None):
    widget.canvas.before.clear()
    with widget.canvas.before:
        # Use dynamic surface color when called with static SURFACE token
        if color is SURFACE or color is SURFACE_D:
            Color(*THEME['surface'])
        else:
            Color(*(color or THEME['surface']))
        widget._bar_bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[0])
    widget.bind(
        pos=lambda w, _v: setattr(w._bar_bg, 'pos', w.pos),
        size=lambda w, _v: setattr(w._bar_bg, 'size', w.size),
    )


def section_label(text):
    # Eyebrow-style section label (tax-desk; matches web uppercase muted/accent kickers)
    color = THEME.get('accent', SUBTLE) if isinstance(THEME, dict) else SUBTLE
    return make_label(str(text).upper(), 11, color, True, 'left', 22)


def accessible(widget, description, tag=True):
    """Set accessibility description for TalkBack on Android."""
    try:
        widget.description_for_accessibility = description
    except Exception:
        pass
    return widget


def accessible_input(widget, label):
    """Set accessibility on a TextInput/Spinner."""
    return accessible(widget, label)



# ═══════════════════════════════════════════════════════════
# BASE SCREEN
# ═══════════════════════════════════════════════════════════
class BaseScreen(Screen):
    def __init__(self, name, title_text, **kwargs):
        super().__init__(name=name, **kwargs)
        root = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(14), dp(6)])
        paint_bar(header, SURFACE)
        header.add_widget(make_label(title_text, 16, TEXT, True, 'left'))
        root.add_widget(header)

        self.scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=[dp(14), dp(10), dp(14), dp(16)],
            size_hint_y=None,
        )
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_enter(self, *args):
        self.body.clear_widgets()
        # Apply persisted density before building content
        try:
            root = App.get_running_app().root
            if hasattr(root, 'apply_density_to_screen'):
                root.apply_density_to_screen(self)
        except Exception:
            pass
        try:
            self.build_ui()
        except Exception as exc:
            self.body.add_widget(make_label(f'Gagal memuat: {exc}', 13, ERROR, False, 'left', 80))

    def build_ui(self):
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════
class DashboardScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('dashboard', 'Corporate Tax Manager', **kwargs)

    def build_ui(self):
        now = date.today()
        self.body.add_widget(section_label('Meja pajak'))
        self.body.add_widget(make_label(f'Posisi masa {now.month:02d}/{now.year}', 17, TEXT, True, 'left', 28))
        self.body.add_widget(make_label('Fokus: catat → rekonsiliasi → setor', 11, SUBTLE, False, 'left', 20))

        total_month = total_year = doc_count = pph21_month = 0.0
        data = {}
        try:
            data = TaxDB().get_dashboard_data(year=now.year, month=now.month)
            total_month = float(data.get('total_due_this_month', 0) or 0)
            total_year = float(data.get('total_year', 0) or 0)
            doc_count = int(data.get('doc_count', 0) or 0)
            pph21_month = float(data.get('total_pph21_month', 0) or 0)
        except Exception:
            pass

        try:
            deadlines = TaxDB().get_upcoming_deadlines(days_ahead=45)
        except Exception:
            deadlines = []
        urgent = [d for d in deadlines if d.get('status') in ('LEWAT', 'SEGERA')]
        if urgent:
            top = urgent[0]
            banner = BoxLayout(
                orientation='vertical', size_hint_y=None, height=dp(72),
                padding=[dp(12), dp(8)], spacing=dp(2),
            )
            paint_card(banner)
            status = top.get('status', 'SEGERA')
            status_color = ERROR if status == 'LEWAT' else WARNING
            banner.add_widget(make_label(f'REMINDER · {status}', 11, status_color, True, 'left', 18))
            banner.add_widget(make_label(
                f"{top.get('title') or '-'} — {top.get('date') or ''}",
                12, TEXT, False, 'left', 22,
            ))
            if len(urgent) > 1:
                banner.add_widget(make_label(f'+{len(urgent) - 1} deadline lain', 11, SUBTLE, False, 'left', 16))
            self.body.add_widget(banner)

        hero = BoxLayout(orientation='vertical', padding=[dp(12), dp(10)], spacing=dp(2), size_hint_y=None, height=dp(118))
        paint_card(hero)
        hero.add_widget(make_label('KEWAJIBAN MASA · TOTAL PPH', 11, PRIMARY, True, 'left', 18))
        hero.add_widget(make_label(f'Rp {total_month:,.0f}', 18, TEXT, True, 'left', 28))
        try:
            wh_month = float(data.get('total_withholding_month', 0) or 0)
        except Exception:
            wh_month = max(0.0, total_month - pph21_month)
        hero.add_widget(make_label(
            f'Potongan Rp {wh_month:,.0f}  ·  PPh 21 Rp {pph21_month:,.0f}',
            11, SUBTLE, False, 'left', 20,
        ))
        self.body.add_widget(hero)

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(148))
        for title, value in [
            ('Total Tahun', f'Rp {total_year:,.0f}'),
            ('PPh 21 Bulan', f'Rp {pph21_month:,.0f}'),
            ('Dokumen', str(doc_count)),
            ('Deadline 45 hr', f'{len(urgent)} urgent' if urgent else 'Aman'),
        ]:
            card = BoxLayout(orientation='vertical', padding=[dp(10), dp(8)], spacing=dp(2), size_hint_y=None, height=dp(68))
            paint_card(card)
            card.add_widget(make_label(title, 11, SUBTLE, False, 'left', 18))
            card.add_widget(make_label(value, 14, TEXT, True, 'left', 24))
            grid.add_widget(card)
        self.body.add_widget(grid)

        self.body.add_widget(section_label('Alur masa'))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        report_btn = make_button('Laporan', PRIMARY, WHITE, 42)
        report_btn.bind(on_release=lambda _b: App.get_running_app().root.goto('report'))
        wh_btn = make_button('Potongan', SURFACE_MUTED, TEXT, 42)
        wh_btn.bind(on_release=lambda _b: App.get_running_app().root.goto('withholding'))
        p21_btn = make_button('PPh 21', SURFACE_MUTED, TEXT, 42)
        p21_btn.bind(on_release=lambda _b: App.get_running_app().root.goto('pph21'))
        dens_btn = make_button(
            'Lega' if App.get_running_app().root.compact else 'Ringkas',
            SURFACE_MUTED, TEXT, 42,
        )
        dens_btn.bind(on_release=lambda _b: App.get_running_app().root.toggle_density())
        dark_label = 'Terang' if THEME['is_dark'] else 'Gelap'
        dark_btn = make_button(f'{dark_label}', SURFACE_MUTED, TEXT, 42)
        dark_btn.bind(on_release=lambda _b: App.get_running_app().root.toggle_dark_mode())
        actions.add_widget(wh_btn)
        actions.add_widget(p21_btn)
        actions.add_widget(report_btn)
        self.body.add_widget(actions)
        tools = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        docs_btn = make_button('Dokumen', SURFACE_MUTED, TEXT, 42)
        docs_btn.bind(on_release=lambda _b: App.get_running_app().root.goto('documents'))
        tools.add_widget(docs_btn)
        tools.add_widget(dens_btn)
        tools.add_widget(dark_btn)
        self.body.add_widget(tools)

        self.body.add_widget(section_label('Deadline masa'))
        if not deadlines:
            self.body.add_widget(make_label('Window 45 hari bersih — tetapkan jadwal setor bila perlu', 12, SUBTLE, False, 'center', 36))
        for item in deadlines[:6]:
            status = item.get('status', 'OK')
            color = ERROR if status == 'LEWAT' else (WARNING if status == 'SEGERA' else GREEN)
            row = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(12), dp(8)], spacing=dp(8))
            paint_card(row)
            title_lbl = make_label(str(item.get('title') or '-'), 13, TEXT, True, 'left')
            # Wrap long deadlines
            title_lbl.bind(size=lambda w, _v: setattr(w, 'text_size', (w.width, None)))
            row.add_widget(title_lbl)
            row.add_widget(Widget())
            row.add_widget(make_label(status, 12, color, True, 'right'))
            self.body.add_widget(row)


# ═══════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════
class CalculatorScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('calculator', 'Kalkulator Pajak', **kwargs)
        self.active_tab = 0
        self.calc = TaxCalculator()
        self.tab_buttons = {}

    def build_ui(self):
        tab_box = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        for idx, name in enumerate(['PPh 21', 'PPh 23', 'PPh 26', 'PPN', 'Badan', 'Final']):
            button = make_button(
                name,
                PRIMARY if idx == self.active_tab else SURFACE_MUTED,
                WHITE if idx == self.active_tab else TEXT,
                height=40,
            )
            button.bind(on_release=lambda _b, i=idx: self.switch_tab(i))
            tab_box.add_widget(button)
            self.tab_buttons[idx] = button
        self.body.add_widget(tab_box)

        self.input_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        self.input_box.bind(minimum_height=self.input_box.setter('height'))
        self.body.add_widget(self.input_box)

        self.result_label = make_label('', 13, TEXT, False, 'left', 140)
        self.body.add_widget(self.result_label)
        self.load_tab(self.active_tab)

    def switch_tab(self, idx):
        self.active_tab = idx
        for i, button in self.tab_buttons.items():
            selected = i == idx
            button.background_color = PRIMARY if selected else SURFACE_MUTED
            button.color = WHITE if selected else TEXT
        self.input_box.clear_widgets()
        self.result_label.text = ''
        self.load_tab(idx)

    def add_field(self, title, default='', numeric=False):
        self.input_box.add_widget(make_label(title, 12, SUBTLE, False, 'left', 18))
        field = TextInput(
            text=str(default),
            multiline=False,
            input_filter='float' if numeric else None,
            size_hint_y=None,
            height=dp(38),
            background_color=WHITE,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=[dp(8), dp(8)],
        )
        self.input_box.add_widget(field)
        return field

    def add_spinner(self, title, values, default=None):
        self.input_box.add_widget(make_label(title, 12, SUBTLE, False, 'left', 18))
        spinner = Spinner(
            text=default or values[0],
            values=values,
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=WHITE,
            color=TEXT,
        )
        self.input_box.add_widget(spinner)
        return spinner

    def load_tab(self, idx):
        if idx == 0:
            self.gaji = self.add_field('Gaji Bruto / Bulan (Rp)', '15000000', True)
            self.ptkp = self.add_spinner('Status PTKP', ['TK0', 'TK1', 'TK2', 'TK3', 'K0', 'K1', 'K2', 'K3'], 'K0')
            button = make_button('Hitung PPh 21', height=40)
            button.bind(on_release=lambda _b: self.calc_pph21())
            self.input_box.add_widget(button)
        elif idx == 1:
            self.amt23 = self.add_field('Nilai Bruto (Rp)', '50000000', True)
            self.obj23 = self.add_spinner('Jenis Objek', ['Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti'], 'Jasa')
            button = make_button('Hitung PPh 23', height=40)
            button.bind(on_release=lambda _b: self.calc_pph23())
            self.input_box.add_widget(button)
        elif idx == 2:
            self.amt26 = self.add_field('Nilai Bruto (Rp)', '100000000', True)
            self.obj26 = self.add_spinner('Jenis Objek', ['Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti'], 'Jasa')
            self.npwp26 = self.add_spinner('Punya NPWP', ['Tidak', 'Ya'], 'Tidak')
            button = make_button('Hitung PPh 26', height=40)
            button.bind(on_release=lambda _b: self.calc_pph26())
            self.input_box.add_widget(button)
        elif idx == 3:
            self.price = self.add_field('Harga DPP (Rp)', '10000000', True)
            self.ppn_rate = self.add_spinner('Tarif PPN', ['11%', '12%'], '11%')
            button = make_button('Hitung PPN', height=40)
            button.bind(on_release=lambda _b: self.calc_ppn())
            self.input_box.add_widget(button)
        elif idx == 4:
            self.laba = self.add_field('Laba Kena Pajak (Rp)', '500000000', True)
            self.omzet = self.add_field('Omzet / Peredaran Bruto (Rp)', '2000000000', True)
            button = make_button('Hitung PPh Badan', height=40)
            button.bind(on_release=lambda _b: self.calc_badan())
            self.input_box.add_widget(button)
        else:
            self.final_type = self.add_spinner(
                'Jenis Final',
                ['Sewa Tanah 10%', 'Konstruksi', 'Pesangon', 'Penjualan Tanah 2.5%', 'Bunga Deposito 20%'],
                'Sewa Tanah 10%',
            )
            self.final_amt = self.add_field('Nilai (Rp)', '200000000', True)
            self.final_rank = self.add_spinner('Peringkat Konstruksi', ['kecil', 'menengah', 'lainnya'], 'lainnya')
            button = make_button('Hitung PPh Final', height=40)
            button.bind(on_release=lambda _b: self.calc_final())
            self.input_box.add_widget(button)

    def calc_pph21(self):
        try:
            gross = float(self.gaji.text or 0)
            result = self.calc.pph21(gross, self.ptkp.text)
            self.result_label.text = (
                f"Gaji Bruto: Rp {gross:,.0f}\n"
                f"PTKP: Rp {result.get('ptkp', 0):,.0f}\n"
                f"PPh 21 / Bulan: Rp {result.get('pph_monthly', 0):,.0f}\n"
                f"Take Home: Rp {result.get('take_home_pay', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'

    def calc_pph23(self):
        try:
            amount = float(self.amt23.text or 0)
            result = self.calc.pph23(amount, self.obj23.text)
            self.result_label.text = (
                f"Jenis: {self.obj23.text}\n"
                f"DPP: Rp {amount:,.0f}\n"
                f"Tarif: {result.get('tarif', '-')}\n"
                f"PPh 23: Rp {result.get('pph', 0):,.0f}\n"
                f"Diterima: Rp {result.get('diterima', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'

    def calc_pph26(self):
        try:
            amount = float(self.amt26.text or 0)
            have_npwp = self.npwp26.text == 'Ya'
            result = self.calc.pph26(amount, self.obj26.text, have_npwp=have_npwp)
            self.result_label.text = (
                f"Jenis: {result.get('jenis_pajak', 'PPh 26')}\n"
                f"DPP: Rp {amount:,.0f}\n"
                f"Tarif: {result.get('tarif', '-')}\n"
                f"PPh: Rp {result.get('pph', 0):,.0f}\n"
                f"Diterima: Rp {result.get('diterima', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'

    def calc_ppn(self):
        try:
            price = float(self.price.text or 0)
            tariff = float(self.ppn_rate.text.replace('%', ''))
            result = self.calc.ppn(price, tariff)
            self.result_label.text = (
                f"DPP: Rp {price:,.0f}\n"
                f"Tarif: {tariff}%\n"
                f"PPN: Rp {result.get('ppn', 0):,.0f}\n"
                f"Total: Rp {result.get('total', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'

    def calc_badan(self):
        try:
            laba = float(self.laba.text or 0)
            omzet = float(self.omzet.text or 0)
            result = self.calc.pph_badan(laba, omzet)
            self.result_label.text = (
                f"Laba: Rp {laba:,.0f}\n"
                f"Omzet: Rp {omzet:,.0f}\n"
                f"Metode: {result.get('metode', '-')}\n"
                f"PPh Badan: Rp {result.get('pph', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'

    def calc_final(self):
        try:
            amount = float(self.final_amt.text or 0)
            kind = self.final_type.text
            if kind.startswith('Sewa'):
                result = self.calc.pph_final_sewa_tanah(amount)
            elif kind.startswith('Konstruksi'):
                result = self.calc.pph_final_konstruksi(amount, self.final_rank.text)
            elif kind.startswith('Penjualan') or kind.startswith('Tanah'):
                result = self.calc.pph_final_penjualan_tanah(amount)
            elif kind.startswith('Bunga') or kind.startswith('Deposito'):
                result = self.calc.pph_final_bunga_deposito(amount)
            else:
                result = self.calc.pph_final_pesangon(amount)
            lines = [
                f"Jenis: {result.get('jenis', kind)}",
                f"Nilai: Rp {amount:,.0f}",
                f"Tarif: {result.get('tarif', '-')}",
                f"PPh Final: Rp {result.get('pph', 0):,.0f}",
            ]
            if 'diterima' in result:
                lines.append(f"Diterima: Rp {result.get('diterima', 0):,.0f}")
            if 'ppn' in result:
                lines.append(f"PPN terkait: Rp {result.get('ppn', 0):,.0f}")
            self.result_label.text = '\n'.join(lines) if lines else TaxCalculator().summary(result)
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'


# ═══════════════════════════════════════════════════════════
# TOAST — Lightweight feedback (auto-dismiss)
# ═══════════════════════════════════════════════════════════
def show_toast(msg, duration=2.0, color=TEXT):
    """Show a lightweight auto-dismiss banner at the top of the app.
    Falls back to a small Popup if app root is unavailable."""
    try:
        root = App.get_running_app().root
        if hasattr(root, 'show_toast'):
            root.show_toast(msg, duration, color)
            return
    except Exception:
        pass
    # Fallback popup for safety
    content = BoxLayout(padding=dp(12))
    content.add_widget(make_label(str(msg)[:120], 12, color, False, 'center', 50))
    p = Popup(title='', content=content, size_hint=(0.88, 0.22), separator_height=0)
    p.open()
    Clock.schedule_once(lambda _dt: p.dismiss(), duration)


# ═══════════════════════════════════════════════════════════
# WITHHOLDING LOG
# ═══════════════════════════════════════════════════════════
def _android_export_dir():
    try:
        app = App.get_running_app()
        if app and getattr(app, 'user_data_dir', None):
            return os.path.join(app.user_data_dir, 'exports')
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')


def _show_export_result(title, msg, error=False, path=None):
    """Show export result. When path is set, offer Bagikan (share sheet / clipboard)."""
    content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(14))
    content.add_widget(make_label(
        msg, 12, ERROR if error else TEXT, False,
        'left' if not error else 'center', 140 if not error else 80,
    ))
    actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
    popup = Popup(title=title, content=content, size_hint=(0.92, 0.48 if path and not error else 0.42 if not error else 0.32))

    if path and not error:
        share_btn = make_button('Bagikan', PRIMARY, WHITE, 38)

        def do_share(_btn):
            result = share_or_copy(path, title=title)
            if result.get('shared'):
                status = 'Dibuka di menu bagikan Android'
            elif result.get('copied'):
                status = 'Path disalin ke clipboard'
            else:
                status = f"Share tidak tersedia\n{path}"
            info = Popup(
                title='Bagikan',
                content=make_label(status, 12, TEXT, False, 'left', 90),
                size_hint=(0.88, 0.32),
            )
            info.open()

        share_btn.bind(on_release=do_share)
        actions.add_widget(share_btn)

    close_btn = make_button('Tutup', SURFACE_MUTED, TEXT, 38)
    close_btn.bind(on_release=lambda _b: popup.dismiss())
    actions.add_widget(close_btn)
    content.add_widget(actions)
    popup.open()


class WithholdingScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('withholding', 'Log PPh 23/26', **kwargs)

    def build_ui(self):
        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        add_btn = make_button('+ Tambah', PRIMARY, WHITE, 40)
        add_btn.bind(on_release=lambda _b: self.show_add_popup())
        export_btn = make_button('Export CSV', SURFACE_MUTED, TEXT, 40)
        export_btn.bind(on_release=lambda _b: self.export_csv())
        actions.add_widget(add_btn)
        actions.add_widget(export_btn)
        self.body.add_widget(actions)

        try:
            rows, total = TaxDB().get_all_withholding(limit=50)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error DB: {exc}', 12, ERROR, False, 'left', 50))
            return

        if not rows:
            icon = make_label('📋', 24, SUBTLE, False, 'center', 40)
            icon.halign = 'center'
            self.body.add_widget(icon)
            self.body.add_widget(make_label('Belum ada potongan di masa ini', 13, TEXT, True, 'center', 28))
            self.body.add_widget(make_label('Langkah berikutnya: catat PPh 23/26/Final dari invoice vendor', 11, SUBTLE, False, 'center', 40))
            return

        self.body.add_widget(make_label(f'{total} transaksi', 12, SUBTLE, False, 'left', 20))
        for row in rows:
            card = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(10), dp(6)], spacing=dp(8))
            paint_card(card)
            left = f"{row.get('vendor', '-')} ({row.get('obj_type', '-')})"
            card.add_widget(make_label(left, 12, TEXT, True, 'left'))
            card.add_widget(make_label(f"Rp {float(row.get('pph_amount', 0) or 0):,.0f}", 12, TEXT, True, 'right'))
            # Delete button with confirm
            del_btn = make_button('✕', ERROR, WHITE, 32)
            rid = row.get('id')
            def make_delete_cb(rid, title):
                def cb(_b):
                    confirm = Popup(
                        title='Konfirmasi Hapus',
                        content=make_label(f'Hapus "{title}"?', 13, TEXT, False, 'center', 50),
                        size_hint=(0.84, 0.32),
                    )
                    def do_delete(_btn):
                        try:
                            TaxDB().cursor.execute('DELETE FROM withholding WHERE id=?', (rid,))
                            TaxDB().conn.commit()
                        except Exception as exc:
                            pass
                        confirm.dismiss()
                        Clock.schedule_once(lambda _dt: self.on_enter())
                    btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
                    btn_row.add_widget(make_button('Hapus', ERROR, WHITE, 36))
                    btn_row.children[-1].bind(on_release=do_delete)
                    btn_row.add_widget(make_button('Batal', SURFACE_MUTED, TEXT, 36))
                    btn_row.children[-1].bind(on_release=lambda _b2: confirm.dismiss())
                    confirm.content.add_widget(btn_row)
                    # Adjust confirm height
                    confirm.size_hint_y = 0.38
                    confirm.open()
                return cb
            del_btn.bind(on_release=make_delete_cb(rid, row.get('vendor', '-')))
            card.add_widget(del_btn)
            self.body.add_widget(card)

    def export_csv(self):
        try:
            rows, _ = TaxDB().get_all_withholding(limit=10000)
            if not rows:
                raise ValueError('Belum ada data potongan untuk diekspor')
            path, count, total = export_withholding_csv(rows, _android_export_dir())
            msg = (
                f'CSV tersimpan\n{count} baris · total PPh Rp {total:,.0f}\n\n'
                f'{path}'
            )
            _show_export_result('Export PPh 23/26', msg, path=path)
        except Exception as exc:
            _show_export_result('Export gagal', str(exc), error=True)

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Tambah Potongan PPh', 15, TEXT, True, 'left', 28))

        vendor = TextInput(hint_text='Nama Vendor', multiline=False, size_hint_y=None, height=dp(38))
        amount = TextInput(hint_text='Jumlah Bruto (Rp)', multiline=False, input_filter='float', size_hint_y=None, height=dp(38))
        obj_type = Spinner(text='Jasa', values=['Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti', 'Hadiah'], size_hint_y=None, height=dp(38))
        tax_code = Spinner(text='pph23', values=['pph23', 'pph26', 'pph_final'], size_hint_y=None, height=dp(38))
        tariff_sel = Spinner(text='2%', values=['2%', '15%', '20%', '10%', '0.5%'], size_hint_y=None, height=dp(38))
        description = TextInput(hint_text='Keterangan', multiline=True, size_hint_y=None, height=dp(60))
        for w in (vendor, amount, obj_type, tax_code, tariff_sel, description):
            content.add_widget(w)

        # Scrollable wrapper for keyboard handling
        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(content)

        popup = Popup(title='PPh 23/26', content=scroll, size_hint=(0.92, 0.72), auto_dismiss=False)

        def save(_btn):
            try:
                TaxDB().add_withholding(
                    vendor=vendor.text.strip() or 'Vendor',
                    amount=float(amount.text or 0),
                    obj_type=obj_type.text,
                    tax_code=tax_code.text,
                    tariff_label=tariff_sel.text,
                    description=(description.text or '').strip()[:200],
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(title='Error', content=make_label(str(exc), 12, ERROR, False, 'center', 60), size_hint=(0.88, 0.44))
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()


# ═══════════════════════════════════════════════════════════
# PPH 21 LOG
# ═══════════════════════════════════════════════════════════
class Pph21Screen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('pph21', 'Log PPh 21', **kwargs)
        self.filter_year = date.today().year
        self.filter_month = 0  # 0 = all months

    def build_ui(self):
        now = date.today()
        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        add_btn = make_button('+ Tambah', PRIMARY, WHITE, 40)
        add_btn.bind(on_release=lambda _b: self.show_add_popup())
        export_btn = make_button('Export CSV', SURFACE_MUTED, TEXT, 40)
        export_btn.bind(on_release=lambda _b: self.export_csv())
        actions.add_widget(add_btn)
        actions.add_widget(export_btn)
        self.body.add_widget(actions)

        # Year/month filter parity with web
        filter_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6), padding=[dp(0), dp(4)])
        yr = Spinner(
            text=str(self.filter_year),
            values=[str(y) for y in range(2020, now.year + 2)],
            size_hint_y=None, height=dp(36),
        )
        yr.bind(text=lambda _s, _v: self._apply_filter(int(yr.text), self.filter_month))
        filter_row.add_widget(yr)
        mon = Spinner(
            text='Semua bulan' if self.filter_month == 0 else f'{self.filter_month:02d}',
            values=['Semua bulan'] + [f'{m:02d}' for m in range(1, 13)],
            size_hint_y=None, height=dp(36),
        )
        mon.bind(text=lambda _s, _v: self._apply_filter(
            self.filter_year,
            0 if mon.text == 'Semua bulan' else int(mon.text.split(':')[0] if ':' in mon.text else mon.text),
        ))
        filter_row.add_widget(mon)
        self.body.add_widget(filter_row)

        self._apply_filter(self.filter_year, self.filter_month)

    def _apply_filter(self, year, month):
        self.filter_year = year
        self.filter_month = month
        # Clear existing list items (keep actions + filter row)
        # Rebuild body below filter
        self.body.clear_widgets()
        # Re-add actions + filter (they get rebuilt by build_ui, so call build_ui tail)
        self.build_ui_tail(year, month)

    def build_ui_tail(self, year, month):
        try:
            rows, total = TaxDB().get_pph21_log(year=year if month else None, month=month or None, limit=50)
            year_total = TaxDB().get_total_pph21(year)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error DB: {exc}', 12, ERROR, False, 'left', 50))
            return

        if month:
            filter_desc = f'{month:02d}/{year}'
        else:
            filter_desc = f'tahun {year}'
        self.body.add_widget(make_label(
            f'{total} data · {filter_desc} · total tahun: Rp {year_total:,.0f}',
            12, SUBTLE, False, 'left', 22,
        ))
        if not rows:
            icon = make_label('👤', 24, SUBTLE, False, 'center', 40)
            icon.halign = 'center'
            self.body.add_widget(icon)
            self.body.add_widget(make_label('Belum ada payroll PPh 21 untuk filter ini', 13, TEXT, True, 'center', 28))
            self.body.add_widget(make_label('Langkah berikutnya: input gaji bruto + PTKP pegawai', 11, SUBTLE, False, 'center', 40))
            return

        for row in rows:
            card = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(10), dp(6)], spacing=dp(6))
            paint_card(card)
            left = f"{row.get('employee_name', '-')} · {row.get('ptkp_status', '-')}"
            period = f"{row.get('period_year')}-{int(row.get('period_month') or 0):02d}"
            card.add_widget(make_label(f'{left}\n{period}', 11, TEXT, True, 'left', 42))
            card.add_widget(make_label(f"Rp {float(row.get('pph21_amount', 0) or 0):,.0f}", 12, TEXT, True, 'right', 42))
            # Delete button with confirm
            del_btn = make_button('✕', ERROR, WHITE, 32)
            rid = row.get('id')
            def make_delete_cb(rid, name):
                def cb(_b):
                    confirm = Popup(
                        title='Konfirmasi Hapus',
                        content=make_label(f'Hapus "{name}"?', 13, TEXT, False, 'center', 50),
                        size_hint=(0.84, 0.32),
                    )
                    def do_delete(_btn):
                        try:
                            TaxDB().cursor.execute('DELETE FROM pph21_log WHERE id=?', (rid,))
                            TaxDB().conn.commit()
                        except Exception:
                            pass
                        confirm.dismiss()
                        Clock.schedule_once(lambda _dt: self._apply_filter(self.filter_year, self.filter_month))
                    btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
                    btn_row.add_widget(make_button('Hapus', ERROR, WHITE, 36))
                    btn_row.children[-1].bind(on_release=do_delete)
                    btn_row.add_widget(make_button('Batal', SURFACE_MUTED, TEXT, 36))
                    btn_row.children[-1].bind(on_release=lambda _b2: confirm.dismiss())
                    confirm.content.add_widget(btn_row)
                    confirm.size_hint_y = 0.38
                    confirm.open()
                return cb
            del_btn.bind(on_release=make_delete_cb(rid, row.get('employee_name', '-')))
            card.add_widget(del_btn)
            self.body.add_widget(card)

    def export_csv(self):
        try:
            rows, _ = TaxDB().get_pph21_log(limit=10000)
            if not rows:
                raise ValueError('Belum ada data PPh 21 untuk diekspor')
            path, count, total = export_pph21_csv(rows, _android_export_dir())
            msg = (
                f'CSV tersimpan\n{count} baris · total PPh Rp {total:,.0f}\n\n'
                f'{path}'
            )
            _show_export_result('Export PPh 21', msg, path=path)
        except Exception as exc:
            _show_export_result('Export gagal', str(exc), error=True)

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Tambah PPh 21', 15, TEXT, True, 'left', 28))
        name = TextInput(hint_text='Nama pegawai', multiline=False, size_hint_y=None, height=dp(38))
        gross = TextInput(hint_text='Gaji bruto', text='15000000', multiline=False, input_filter='float', size_hint_y=None, height=dp(38))
        ptkp = Spinner(
            text='TK0',
            values=['TK0', 'TK1', 'TK2', 'TK3', 'K0', 'K1', 'K2', 'K3'],
            size_hint_y=None,
            height=dp(38),
        )
        now = date.today()
        period_year = TextInput(hint_text='Tahun', text=str(now.year), multiline=False, input_filter='int', size_hint_y=None, height=dp(38))
        period_month = TextInput(hint_text='Bulan (1-12)', text=str(now.month), multiline=False, input_filter='int', size_hint_y=None, height=dp(38))
        pph_input = TextInput(hint_text='PPh 21 (opsional — kosongkan untuk auto)', multiline=False, input_filter='float', size_hint_y=None, height=dp(38))
        for w in (name, gross, ptkp, period_year, period_month, pph_input):
            content.add_widget(w)

        # Scrollable wrapper for keyboard handling
        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(content)

        popup = Popup(title='PPh 21', content=scroll, size_hint=(0.92, 0.76), auto_dismiss=False)

        def save(_btn):
            try:
                employee = (name.text or '').strip()
                if not employee:
                    raise ValueError('Nama pegawai harus diisi')
                gaji = float(gross.text or 0)
                status = ptkp.text
                year = int(period_year.text or now.year)
                month = int(period_month.text or now.month)
                if month < 1 or month > 12:
                    raise ValueError('Bulan harus 1-12')
                pph_val = (pph_input.text or '').strip()
                if pph_val:
                    pph_amount = float(pph_val)
                else:
                    result = TaxCalculator().pph21(gaji, status)
                    pph_amount = float(result.get('pph_monthly') or 0)
                deps = {'TK0': 0, 'TK1': 1, 'TK2': 2, 'TK3': 3, 'K0': 0, 'K1': 1, 'K2': 2, 'K3': 3}.get(status, 0)
                TaxDB().add_pph21(
                    employee_name=employee,
                    gross_salary=gaji,
                    dependents=deps,
                    ptkp_status=status,
                    pph21_amount=pph_amount,
                    year=year,
                    month=month,
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(
                    title='Error',
                    content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                    size_hint=(0.88, 0.44),
                )
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()


# ═══════════════════════════════════════════════════════════
# DOCUMENTS
# ═══════════════════════════════════════════════════════════
class DocumentsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('documents', 'Dokumen Pajak', **kwargs)
        self.search_query = ''

    def build_ui(self):
        # Search row
        search_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.search_input = TextInput(
            text=self.search_query,
            hint_text='Cari judul / kategori / catatan',
            multiline=False,
            size_hint_x=0.72,
            size_hint_y=None,
            height=dp(38),
            background_color=WHITE,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=[dp(8), dp(8)],
        )
        search_btn = make_button('Cari', PRIMARY, WHITE, 38)
        search_btn.size_hint_x = 0.28
        search_btn.bind(on_release=lambda _b: self.apply_search())
        search_row.add_widget(self.search_input)
        search_row.add_widget(search_btn)
        self.body.add_widget(search_row)

        add_btn = make_button('+ Tambah Dokumen', height=40)
        add_btn.bind(on_release=lambda _b: self.show_add_popup())
        self.body.add_widget(add_btn)

        try:
            q = self.search_query.strip() or None
            docs, total = TaxDB().get_all_documents(limit=50, q=q)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error DB: {exc}', 12, ERROR, False, 'left', 50))
            return

        if not docs:
            msg = 'Tidak ada hasil pencarian' if self.search_query.strip() else 'Arsip masa masih kosong — simpan bukti potong/SPT'
            icon = make_label('📁', 24, SUBTLE, False, 'center', 40)
            icon.halign = 'center'
            self.body.add_widget(icon)
            self.body.add_widget(make_label(msg, 14, SUBTLE, False, 'center', 50))
            return

        label = f'{total} dokumen'
        if self.search_query.strip():
            label += f' · filter: {self.search_query.strip()}'
        self.body.add_widget(make_label(label, 12, SUBTLE, False, 'left', 20))
        for doc in docs:
            card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(96),
                padding=[dp(10), dp(8)],
                spacing=dp(2),
            )
            paint_card(card)
            title = str(doc.get('title') or '-')
            status = str(doc.get('status') or '-')
            category = str(doc.get('category') or '-')
            year = doc.get('tax_year')
            month = doc.get('tax_month')
            period = f'{year}-{int(month):02d}' if year and month else (str(year) if year else '-')
            top = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
            top.add_widget(make_label(f'{title}', 13, TEXT, True, 'left', 22))
            edit_btn = make_button('Edit', SURFACE_MUTED, TEXT, 24)
            edit_btn.size_hint_x = None
            edit_btn.width = dp(56)
            edit_btn.bind(on_release=lambda _b, d=doc: self.show_edit_popup(d))
            top.add_widget(edit_btn)
            card.add_widget(top)
            card.add_widget(make_label(f'{category} · {status} · {period}', 11, SUBTLE, False, 'left', 18))
            self.body.add_widget(card)

    def apply_search(self):
        self.search_query = (self.search_input.text or '').strip()
        self.on_enter()

    def show_edit_popup(self, doc):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Edit Dokumen', 15, TEXT, True, 'left', 28))
        title = TextInput(
            text=str(doc.get('title') or ''),
            hint_text='Nama dokumen',
            multiline=False,
            size_hint_y=None,
            height=dp(38),
        )
        cats = ['Faktur Pajak', 'SPT Tahunan', 'SPT Masa', 'Bukti Potong', 'Laporan', 'Lainnya', 'Umum']
        cat_text = str(doc.get('category') or 'Faktur Pajak')
        if cat_text not in cats:
            cats = [cat_text] + cats
        category = Spinner(text=cat_text, values=cats, size_hint_y=None, height=dp(38))
        statuses = ['Lengkap', 'Kurang', 'Arsip', 'Dalam Proses']
        st_text = str(doc.get('status') or 'Lengkap')
        if st_text not in statuses:
            statuses = [st_text] + statuses
        status = Spinner(text=st_text, values=statuses, size_hint_y=None, height=dp(38))
        year_in = TextInput(
            text=str(doc.get('tax_year') or ''),
            hint_text='Tahun pajak',
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=dp(38),
        )
        month_in = TextInput(
            text=str(doc.get('tax_month') or ''),
            hint_text='Bulan (1-12)',
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=dp(38),
        )
        notes = TextInput(
            text=str(doc.get('notes') or ''),
            hint_text='Catatan',
            multiline=True,
            size_hint_y=None,
            height=dp(64),
        )
        for w in (title, category, status, year_in, month_in, notes):
            content.add_widget(w)

        popup = Popup(title='Edit Dokumen', content=content, size_hint=(0.92, 0.78), auto_dismiss=False)

        def save(_btn):
            try:
                name = (title.text or '').strip()
                if not name:
                    raise ValueError('Nama dokumen harus diisi')
                ty = int(year_in.text) if (year_in.text or '').strip() else None
                tm = int(month_in.text) if (month_in.text or '').strip() else None
                TaxDB().update_document(
                    int(doc['id']),
                    title=name,
                    category=category.text,
                    status=status.text,
                    tax_year=ty,
                    tax_month=tm,
                    notes=notes.text or '',
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(
                    title='Error',
                    content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                    size_hint=(0.88, 0.44),
                )
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Tambah Dokumen', 15, TEXT, True, 'left', 28))
        title = TextInput(hint_text='Nama dokumen', multiline=False, size_hint_y=None, height=dp(38))
        category = Spinner(
            text='Faktur Pajak',
            values=['Faktur Pajak', 'SPT Tahunan', 'SPT Masa', 'Bukti Potong', 'Laporan', 'Lainnya'],
            size_hint_y=None,
            height=dp(38),
        )
        status = Spinner(
            text='Lengkap',
            values=['Lengkap', 'Kurang', 'Arsip', 'Dalam Proses'],
            size_hint_y=None,
            height=dp(38),
        )
        content.add_widget(title)
        content.add_widget(category)
        content.add_widget(status)

        popup = Popup(title='Dokumen', content=content, size_hint=(0.9, 0.55), auto_dismiss=False)

        def save(_btn):
            try:
                name = (title.text or '').strip()
                if not name:
                    raise ValueError('Nama dokumen harus diisi')
                now = date.today()
                TaxDB().add_document(
                    title=name,
                    category=category.text,
                    status=status.text,
                    tax_year=now.year,
                    tax_month=now.month,
                    notes='',
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(
                    title='Error',
                    content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                    size_hint=(0.88, 0.44),
                )
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()


# ═══════════════════════════════════════════════════════════
# CALENDAR
# ═══════════════════════════════════════════════════════════
class CalendarScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('calendar', 'Kalender Pajak', **kwargs)

    def build_ui(self):
        now = date.today()
        month_name = calendar.month_name[now.month].upper()
        self.body.add_widget(make_label(f'{month_name} {now.year}', 16, TEXT, True, 'center', 28))

        try:
            db = TaxDB()
            deadlines = db.get_calendar_deadlines_map(year=now.year, month=now.month)
            reminders = db.list_reminders(active_only=False)
        except Exception:
            deadlines = {10: 'PPN', 15: 'Final', 20: 'P21/23', 21: 'P26'}
            reminders = []

        add_btn = make_button('+ Deadline', PRIMARY, WHITE, 38)
        add_btn.bind(on_release=lambda _b: self.show_add_reminder())
        self.body.add_widget(add_btn)

        header = GridLayout(cols=7, spacing=dp(2), size_hint_y=None, height=dp(28))
        for day_name in ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']:
            header.add_widget(make_label(day_name, 11, TEXT, True, 'center', 24))
        self.body.add_widget(header)

        weeks = calendar.monthcalendar(now.year, now.month)
        grid = GridLayout(cols=7, spacing=dp(2), size_hint_y=None, height=dp(len(weeks) * 44))
        for week in weeks:
            for day_num in week:
                if day_num == 0:
                    grid.add_widget(Widget(size_hint_y=None, height=dp(42)))
                    continue
                text_day = str(day_num)
                color = TEXT
                if day_num in deadlines:
                    short = deadlines[day_num]
                    if len(short) > 10:
                        short = short[:9] + '...'
                    text_day = f'{day_num}\n{short}'
                    color = ERROR if day_num < now.day else GREEN
                elif day_num == now.day:
                    color = ACCENT
                grid.add_widget(make_label(text_day, 10, color, True, 'center', 42))
        self.body.add_widget(grid)

        self.body.add_widget(section_label('Jadwal setor'))
        if not reminders:
            self.body.add_widget(make_label('🗓', 24, SUBTLE, False, 'center', 40))
            self.body.add_widget(make_label('Belum ada jadwal setor custom', 12, TEXT, True, 'center', 28))
            self.body.add_widget(make_label('Tetapkan deadline berulang/sekali agar naik ke beranda', 11, SUBTLE, False, 'center', 36))
        for rem in reminders:
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6), padding=[dp(8), dp(4)])
            paint_card(row)
            active = bool(rem.get('is_active'))
            is_rec = bool(rem.get('is_recurring', 1))
            kind = 'berulang' if is_rec else 'sekali'
            label = f"{rem.get('deadline_date')} · {rem.get('title')} ({kind})"
            if not active:
                label += ' (nonaktif)'
            row.add_widget(make_label(label, 11, TEXT if active else SUBTLE, False, 'left', 40))
            edit_btn = make_button('Edit', SURFACE_MUTED, TEXT, 30)
            edit_btn.size_hint_x = None
            edit_btn.width = dp(52)
            edit_btn.bind(on_release=lambda _b, r=rem: self.show_edit_reminder(r))
            del_btn = make_button('Hapus', ERROR, WHITE, 30)
            del_btn.size_hint_x = None
            del_btn.width = dp(58)
            del_btn.bind(on_release=lambda _b, rid=rem.get('id'): self.delete_reminder(rid))
            row.add_widget(edit_btn)
            row.add_widget(del_btn)
            self.body.add_widget(row)

    def show_add_reminder(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Tambah Deadline', 15, TEXT, True, 'left', 28))
        title = TextInput(hint_text='Judul (contoh: SPT Masa PPN)', multiline=False, size_hint_y=None, height=dp(38))
        kind = Spinner(text='Berulang bulanan', values=['Berulang bulanan', 'Sekali saja'], size_hint_y=None, height=dp(38))
        day = TextInput(hint_text='Hari 1-31 (jika berulang)', text='10', multiline=False, input_filter='int', size_hint_y=None, height=dp(38))
        once = TextInput(hint_text='YYYY-MM-DD (jika sekali)', multiline=False, size_hint_y=None, height=dp(38))
        code = TextInput(hint_text='Kode (ppn/pph23)', multiline=False, size_hint_y=None, height=dp(38))
        desc = TextInput(hint_text='Deskripsi (opsional)', multiline=False, size_hint_y=None, height=dp(38))
        for w in (title, kind, day, once, code, desc):
            content.add_widget(w)
        popup = Popup(title='Deadline', content=content, size_hint=(0.92, 0.72), auto_dismiss=False)

        def save(_btn):
            try:
                is_rec = kind.text.startswith('Berulang')
                TaxDB().add_reminder(
                    title=(title.text or '').strip(),
                    deadline_day=int(day.text or 0) if is_rec else None,
                    description=desc.text or '',
                    tax_code=code.text or '',
                    is_recurring=is_rec,
                    is_active=True,
                    one_time_date=None if is_rec else (once.text or '').strip(),
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(
                    title='Error',
                    content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                    size_hint=(0.88, 0.44),
                )
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()

    def show_edit_reminder(self, rem):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Edit Deadline', 15, TEXT, True, 'left', 28))
        is_rec0 = bool(rem.get('is_recurring', 1))
        title = TextInput(text=str(rem.get('title') or ''), multiline=False, size_hint_y=None, height=dp(38))
        kind = Spinner(
            text='Berulang bulanan' if is_rec0 else 'Sekali saja',
            values=['Berulang bulanan', 'Sekali saja'],
            size_hint_y=None,
            height=dp(38),
        )
        raw = str(rem.get('deadline_date') or '')
        day = TextInput(
            text=raw if is_rec0 else '10',
            hint_text='Hari 1-31',
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=dp(38),
        )
        once = TextInput(
            text='' if is_rec0 else raw,
            hint_text='YYYY-MM-DD',
            multiline=False,
            size_hint_y=None,
            height=dp(38),
        )
        code = TextInput(text=str(rem.get('tax_code') or ''), multiline=False, size_hint_y=None, height=dp(38))
        desc = TextInput(text=str(rem.get('description') or ''), multiline=False, size_hint_y=None, height=dp(38))
        active_spin = Spinner(
            text='Aktif' if rem.get('is_active') else 'Nonaktif',
            values=['Aktif', 'Nonaktif'],
            size_hint_y=None,
            height=dp(38),
        )
        for w in (title, kind, day, once, code, desc, active_spin):
            content.add_widget(w)
        popup = Popup(title='Edit Deadline', content=content, size_hint=(0.92, 0.78), auto_dismiss=False)

        def save(_btn):
            try:
                is_rec = kind.text.startswith('Berulang')
                TaxDB().update_reminder(
                    int(rem['id']),
                    title=(title.text or '').strip(),
                    deadline_day=int(day.text or 0) if is_rec else None,
                    description=desc.text or '',
                    tax_code=code.text or '',
                    is_recurring=is_rec,
                    is_active=(active_spin.text == 'Aktif'),
                    one_time_date=None if is_rec else (once.text or '').strip(),
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(
                    title='Error',
                    content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                    size_hint=(0.88, 0.44),
                )
                err.open()

        actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = make_button('Simpan', PRIMARY, WHITE, 36)
        save_btn.bind(on_release=save)
        cancel_btn = make_button('Batal', SURFACE_MUTED, TEXT, 36)
        cancel_btn.bind(on_release=lambda _b: popup.dismiss())
        actions.add_widget(save_btn)
        actions.add_widget(cancel_btn)
        content.add_widget(actions)
        popup.open()

    def delete_reminder(self, rid):
        try:
            TaxDB().delete_reminder(int(rid))
            self.on_enter()
        except Exception as exc:
            err = Popup(
                title='Error',
                content=make_label(str(exc), 12, ERROR, False, 'center', 60),
                size_hint=(0.8, 0.3),
            )
            err.open()


# ═══════════════════════════════════════════════════════════
# PERIOD REPORT (Android)
# ═══════════════════════════════════════════════════════════
class ReportScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('report', 'Laporan Periode', **kwargs)
        self.view_year = date.today().year
        self.view_month = date.today().month

    def build_ui(self):
        self.body.add_widget(section_label('Arsip masa'))
        nav = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        prev_btn = make_button('<', SURFACE_MUTED, TEXT, 38)
        prev_btn.size_hint_x = None
        prev_btn.width = dp(44)
        prev_btn.bind(on_release=lambda _b: self.shift_period(-1))
        next_btn = make_button('>', SURFACE_MUTED, TEXT, 38)
        next_btn.size_hint_x = None
        next_btn.width = dp(44)
        next_btn.bind(on_release=lambda _b: self.shift_period(1))
        nav.add_widget(prev_btn)
        nav.add_widget(make_label(
            f'{self.view_month:02d}/{self.view_year}', 16, TEXT, True, 'center', 38,
        ))
        nav.add_widget(next_btn)
        self.body.add_widget(nav)

        export_btn = make_button('Export CSV', SURFACE_MUTED, TEXT, 40)
        export_btn.bind(on_release=lambda _b: self.export_csv())
        self.body.add_widget(export_btn)

        try:
            summary = TaxDB().get_summary_by_period(self.view_year, self.view_month)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error: {exc}', 12, ERROR, False, 'left', 50))
            return

        hero = BoxLayout(orientation='vertical', padding=[dp(12), dp(10)], spacing=dp(2), size_hint_y=None, height=dp(74))
        paint_card(hero)
        hero.add_widget(make_label('TOTAL PPH', 11, PRIMARY, True, 'left', 18))
        hero.add_widget(make_label(f"Rp {float(summary.get('grand_total') or 0):,.0f}", 18, TEXT, True, 'left', 28))
        self.body.add_widget(hero)

        stats = BoxLayout(orientation='vertical', spacing=dp(6), size_hint_y=None)
        stats.bind(minimum_height=stats.setter('height'))
        for title, value in [
            ('PPh 23/26/Final', f"Rp {float(summary.get('withholding_total') or 0):,.0f}"),
            ('PPh 21', f"Rp {float(summary.get('pph21_total') or 0):,.0f}"),
            ('Transaksi', str(summary.get('transaction_count') or 0)),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(44), padding=[dp(12), dp(8)])
            paint_card(row)
            row.add_widget(make_label(title, 12, SUBTLE, False, 'left', 30))
            row.add_widget(make_label(value, 13, TEXT, True, 'right', 30))
            stats.add_widget(row)
        self.body.add_widget(stats)

        self.body.add_widget(section_label('Buku masa · rincian'))
        details = summary.get('details') or []
        if not details:
            self.body.add_widget(make_label('📊', 24, SUBTLE, False, 'center', 40))
            self.body.add_widget(make_label('Belum ada beban PPh di masa ini', 12, TEXT, True, 'center', 28))
            self.body.add_widget(make_label('Catat potongan atau input PPh 21, lalu export arsip', 11, SUBTLE, False, 'center', 36))
            return

        labels = {
            'pph23': 'PPh 23', 'pph26': 'PPh 26',
            'pph_final': 'PPh Final', 'pph21': 'PPh 21',
        }
        for d in details:
            code = labels.get(d.get('tax_code'), d.get('tax_code') or '-')
            card = BoxLayout(
                orientation='vertical', size_hint_y=None, height=dp(64),
                padding=[dp(12), dp(8)], spacing=dp(2),
            )
            paint_card(card)
            card.add_widget(make_label(
                f"{code} · {d.get('obj_type') or '-'} · {d.get('count') or 0}x",
                12, TEXT, True, 'left', 22,
            ))
            card.add_widget(make_label(
                f"PPh Rp {float(d.get('total_tax') or 0):,.0f}",
                12, ERROR, False, 'left', 20,
            ))
            self.body.add_widget(card)

    def export_csv(self):
        try:
            summary = TaxDB().get_summary_by_period(self.view_year, self.view_month)
            details = summary.get('details') or []
            if not details and not float(summary.get('grand_total') or 0):
                raise ValueError('Belum ada data periode ini untuk diekspor')
            path, count, total = export_period_report_csv(
                summary, self.view_year, self.view_month, _android_export_dir(),
            )
            msg = (
                f'CSV tersimpan\n{count} baris rincian · total PPh Rp {total:,.0f}\n'
                f'Periode {self.view_month:02d}/{self.view_year}\n\n{path}'
            )
            _show_export_result('Export Laporan', msg, path=path)
        except Exception as exc:
            _show_export_result('Export gagal', str(exc), error=True)

    def shift_period(self, delta):
        m = self.view_month + delta
        y = self.view_year
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        self.view_month = m
        self.view_year = y
        self.on_enter()


# ═══════════════════════════════════════════════════════════
# ERROR FALLBACK SCREEN
# ═══════════════════════════════════════════════════════════
class ErrorScreen(Screen):
    def __init__(self, message, **kwargs):
        super().__init__(name='error', **kwargs)
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        paint_bar(box, SURFACE)
        box.add_widget(make_label('Gagal Memulai Aplikasi', 18, ERROR, True, 'center', 36))
        box.add_widget(make_label(message, 12, TEXT, False, 'left', 220))
        self.add_widget(box)


# ═══════════════════════════════════════════════════════════
# ROOT LAYOUT WITH BOTTOM NAV
# ═══════════════════════════════════════════════════════════
class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        prefs = load_prefs()
        self.compact = bool(prefs.get('compact', False))
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(DashboardScreen())
        self.sm.add_widget(CalculatorScreen())
        self.sm.add_widget(WithholdingScreen())
        self.sm.add_widget(Pph21Screen())
        self.sm.add_widget(ReportScreen())
        self.sm.add_widget(DocumentsScreen())
        self.sm.add_widget(CalendarScreen())
        self.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2), padding=[dp(4), dp(4)])
        paint_bar(nav, SURFACE)
        self.nav_buttons = {}
        for screen_name, title in [
            ('dashboard', 'Beranda'),
            ('calculator', 'Hitung'),
            ('withholding', 'Log'),
            ('pph21', 'PPh21'),
            ('documents', 'Dokumen'),
            ('calendar', 'Kalender'),
        ]:
            button = make_button(
                title,
                PRIMARY if screen_name == 'dashboard' else SURFACE_MUTED,
                WHITE if screen_name == 'dashboard' else TEXT,
                40,
            )
            accessible(button, f'Navigasi ke {title}')
            button.bind(on_release=lambda _b, s=screen_name: self.goto(s))
            nav.add_widget(button)
            self.nav_buttons[screen_name] = button
        self.add_widget(nav)

    def show_toast(self, msg, duration=2.0, color=TEXT):
        """Lightweight overlay banner that auto-dismisses."""
        toast = BoxLayout(
            size_hint_y=None, height=dp(38),
            padding=[dp(10), dp(6)],
            pos_hint={'top': 1.0},
        )
        paint_bar(toast, SURFACE)
        toast.add_widget(make_label(str(msg)[:120], 12, color, False, 'left', 28))
        self.add_widget(toast)
        Clock.schedule_once(lambda _dt: self.remove_widget(toast), duration)

    def goto(self, screen_name):
        self.sm.current = screen_name
        for name, button in self.nav_buttons.items():
            selected = name == screen_name
            button.background_color = PRIMARY if selected else SURFACE_MUTED
            button.color = WHITE if selected else TEXT

    def apply_density_to_screen(self, screen):
        if not hasattr(screen, 'body'):
            return
        if self.compact:
            screen.body.spacing = dp(5)
            screen.body.padding = [dp(10), dp(6), dp(10), dp(10)]
        else:
            screen.body.spacing = dp(8)
            screen.body.padding = [dp(14), dp(10), dp(14), dp(16)]

    def toggle_density(self):
        """Compact mode: slightly tighter body spacing; persisted to local prefs."""
        self.compact = not self.compact
        prefs = load_prefs()
        prefs['compact'] = self.compact
        save_prefs(prefs)
        screen = self.sm.current_screen
        self.apply_density_to_screen(screen)
        if hasattr(screen, 'on_enter'):
            screen.on_enter()

    def toggle_dark_mode(self):
        """Dark mode: swap THEME tokens and rebuild screens."""
        is_dark = not THEME['is_dark']
        if is_dark:
            THEME['bg'] = BG_D
            THEME['surface'] = SURFACE_D
            THEME['surface_muted'] = SURFACE_MUTED_D
            THEME['primary'] = PRIMARY_D
            THEME['primary_hover'] = PRIMARY_HOVER_D
            THEME['accent'] = ACCENT_D
            THEME['text'] = TEXT_D
            THEME['text_secondary'] = TEXT_SECONDARY_D
            THEME['subtle'] = SUBTLE_D
            THEME['border'] = BORDER_D
            THEME['surface_hover'] = SURFACE_HOVER_D
            Window.clearcolor = BG_D
        else:
            THEME['bg'] = BG
            THEME['surface'] = SURFACE
            THEME['surface_muted'] = SURFACE_MUTED
            THEME['primary'] = PRIMARY
            THEME['primary_hover'] = PRIMARY_HOVER
            THEME['accent'] = ACCENT
            THEME['text'] = TEXT
            THEME['text_secondary'] = TEXT_SECONDARY
            THEME['subtle'] = SUBTLE
            THEME['border'] = BORDER
            THEME['surface_hover'] = SURFACE_HOVER
            Window.clearcolor = BG
        THEME['is_dark'] = is_dark
        prefs = load_prefs()
        prefs['dark_mode'] = is_dark
        save_prefs(prefs)
        screen = self.sm.current_screen
        if hasattr(screen, 'on_enter'):
            screen.on_enter()


# ═══════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════
class CorporateTaxApp(App):
    def build(self):
        Window.clearcolor = THEME['bg']
        self.title = f'Corporate Tax Manager {APP_VERSION}'
        try:
            TaxDB().init_tables()
            return RootLayout()
        except Exception as exc:
            detail = f'{exc}\n\n{traceback.format_exc()}'
            return ErrorScreen(detail)


if __name__ == '__main__':
    CorporateTaxApp().run()
