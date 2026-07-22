"""
Corporate Tax Manager — Android App
Membantu tugas bagian pajak perusahaan:
- Dashboard ringkasan pajak
- Kalkulator PPh 21, 23/26, PPN, PPh Badan
- Log transaksi PPh 23/26
- Kalender deadline pajak
- Manajemen dokumen perpajakan
"""

import os
import sys

# Ensure data package is importable
sys.path.insert(0, os.path.dirname(__file__))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line

from datetime import datetime, date, timedelta
import calendar
import threading

from data.tax_db import TaxDB
from data.tax_calculator import TaxCalculator


# ─── COLOR THEME — Old Money ───
NAVY = '#1B2A4A'
NAVY_RGB = (0.106, 0.165, 0.290, 1)
CHARCOAL = '#2C3E50'
CREAM = '#F5F0E8'
CREAM_DARK = '#E8E0D0'
COPPER = '#B87333'
COPPER_RGB = (0.722, 0.451, 0.200, 1)
GOLD = '#C9A84C'
WHITE = '#FFFFFF'
SUBTLE = '#6B7B8D'
SUBTLE_RGB = (0.42, 0.49, 0.55, 1)
ERROR_RGB = (0.753, 0.224, 0.169, 1)
GREEN_RGB = (0.149, 0.373, 0.251, 1)


def hex_rgb(h):
    """Convert hex color to Kivy RGB tuple."""
    return get_color_from_hex(h)


def card_bg(widget, bg=WHITE, radius=8):
    """Add rounded rectangle background to a widget."""
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*hex_rgb(bg))
        RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    widget.bind(pos=lambda w, v: self._redraw(w, bg, radius),
                size=lambda w, v: self._redraw(w, bg, radius))


def _redraw(w, bg, radius):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*hex_rgb(bg))
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(radius)])


# ═══════════════════════════════════════════════════
# UTILITY WIDGETS
# ═══════════════════════════════════════════════════

class HeaderBar(BoxLayout):
    """Top navigation bar with hamburger menu and title."""
    def __init__(self, title_text='', **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(56)
        self.padding = [dp(12), dp(4)]
        self.spacing = dp(8)

        with self.canvas.before:
            Color(*hex_rgb(NAVY))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[0, 0, dp(12), dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.menu_btn = Button(
            text='\u2630',  # hamburger
            size_hint_x=None, width=dp(48),
            background_normal='', background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1), font_size=sp(22),
        )
        self.add_widget(self.menu_btn)

        self.title_label = Label(
            text=title_text,
            font_size=sp(18), bold=True,
            color=(0.957, 0.941, 0.910, 1),
            halign='left', valign='middle',
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        self.add_widget(self.title_label)

        self.add_widget(WidgetSpacer())

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*hex_rgb(NAVY))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[0, 0, dp(12), dp(12)])


class WidgetSpacer(Widget):
    """Empty spacer widget."""
    pass


class StatCard(BoxLayout):
    """Dashboard stat card: label + value."""
    def __init__(self, label='', value='', **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = [dp(16), dp(8)]
        self.spacing = dp(8)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)
        self.bind(pos=self._update, size=self._update)

        lbl = Label(
            text=label, font_size=sp(12),
            color=SUBTLE_RGB, halign='left',
            size_hint_x=0.5,
        )
        lbl.bind(size=lbl.setter('text_size'))
        self.add_widget(lbl)

        val = Label(
            text=value, font_size=sp(20), bold=True,
            color=NAVY_RGB, halign='right',
            size_hint_x=0.5,
        )
        val.bind(size=val.setter('text_size'))
        self.add_widget(val)

    def _update(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)


class DeadlineCard(BoxLayout):
    """Deadline reminder card."""
    def __init__(self, title='', date_str='', status='OK', **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = [dp(12), dp(6)]
        self.spacing = dp(4)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)
        self.bind(pos=self._update, size=self._update)

        info = BoxLayout(orientation='vertical', spacing=dp(2))
        info.add_widget(Label(
            text=title, font_size=sp(13), bold=True,
            color=NAVY_RGB, halign='left', size_hint_y=0.5,
        ))
        info.add_widget(Label(
            text=date_str, font_size=sp(12),
            color=COPPER_RGB, halign='left', size_hint_y=0.5,
        ))
        self.add_widget(info)
        self.add_widget(WidgetSpacer())

        status_color = GREEN_RGB if status == 'OK' else (
            ERROR_RGB if status == 'LEWAT' else hex_rgb(GOLD)
        )
        self.add_widget(Label(
            text=status, font_size=sp(12), bold=True,
            color=status_color, size_hint_x=0.2,
        ))

    def _update(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)


class RecordRow(BoxLayout):
    """Generic record row with delete button."""
    def __init__(self, title='', subtitle='', on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(56)
        self.padding = [dp(12), dp(4)]
        self.spacing = dp(8)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)), width=1)
        self.bind(pos=self._update, size=self._update)

        info = BoxLayout(orientation='vertical', spacing=dp(2))
        info.add_widget(Label(
            text=title, font_size=sp(14), bold=True,
            color=NAVY_RGB, halign='left', size_hint_y=0.5,
        ))
        info.add_widget(Label(
            text=subtitle, font_size=sp(11),
            color=SUBTLE_RGB, halign='left', size_hint_y=0.5,
        ))
        self.add_widget(info)

        btn = Button(
            text='Hapus', size_hint_x=0.18,
            background_color=ERROR_RGB,
            color=(1, 1, 1, 1), font_size=sp(12),
        )
        if on_delete:
            btn.bind(on_release=on_delete)
        self.add_widget(btn)

    def _update(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            Color(*hex_rgb(CREAM_DARK))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)), width=1)


class MenuPanel(BoxLayout):
    """Side-drawer menu panel."""
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.orientation = 'vertical'
        self.size_hint_x = 0.6

        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(16), dp(4)])
        with header.canvas.before:
            Color(*hex_rgb(NAVY))
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_head, size=self._update_head)
        header.add_widget(Label(
            text='PAJAK CORPORATE',
            font_size=sp(16), bold=True, color=(0.957, 0.941, 0.910, 1),
        ))
        self.add_widget(header)

        # Menu items
        items = [
            ('BERANDA', 'dashboard'),
            ('KALKULATOR PAJAK', 'calculator'),
            ('KALENDER PAJAK', 'calendar'),
            ('LOG PPh 23/26', 'withholding'),
            ('DOKUMEN PAJAK', 'documents'),
        ]
        for label, screen_name in items:
            btn = Button(
                text=f'    {label}',
                size_hint_y=None, height=dp(48),
                background_normal='', background_color=(0, 0, 0, 0),
                color=NAVY_RGB, halign='left', font_size=sp(15),
                padding=[dp(16), dp(4)],
            )
            btn.bind(on_release=lambda btn, s=screen_name: self.go_to(s))
            # Divider line
            with btn.canvas.before:
                Color(*hex_rgb(CREAM_DARK))
                Line(rectangle=(btn.x, btn.y, btn.width, btn.height - dp(0.5)), width=1)
            self.add_widget(btn)

        self.add_widget(WidgetSpacer())
        self.add_widget(Label(
            text='v1.0.0', font_size=sp(11),
            color=SUBTLE_RGB, size_hint_y=0.05,
        ))

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)

    def _update_head(self, obj, *args):
        obj.canvas.before.clear()
        with obj.canvas.before:
            Color(*hex_rgb(NAVY))
            Rectangle(pos=obj.pos, size=obj.size)

    def go_to(self, screen_name):
        self.app.root.current = screen_name
        self.app.close_menu()


# ═══════════════════════════════════════════════════
# MENU OVERLAY
# ═══════════════════════════════════════════════════
class MenuOverlay(FloatLayout):
    """Full-screen overlay that shows menu panel on left + dimmed background."""
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self._menu_open = False
        self.menu_panel = None

    def toggle(self):
        if self._menu_open:
            self.close()
        else:
            self.open()

    def open(self):
        self._menu_open = True
        self.clear_widgets()

        # Dimmed bg
        bg = BoxLayout()
        with bg.canvas.before:
            Color(0, 0, 0, 0.4)
            Rectangle(pos=bg.pos, size=bg.size)
        bg.bind(pos=lambda w, v: self._dim_redraw(w),
                size=lambda w, v: self._dim_redraw(w))
        bg.bind(on_touch_down=lambda w, t: self.close() if self._menu_open else None)
        self.add_widget(bg)

        # Menu panel
        self.menu_panel = MenuPanel(self.app)
        self.add_widget(self.menu_panel)

        self.opacity = 1

    def close(self):
        self._menu_open = False
        self.clear_widgets()
        self.opacity = 0

    def _dim_redraw(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0, 0, 0, 0.4)
            Rectangle(pos=w.pos, size=w.size)


# ═══════════════════════════════════════════════════
# SCREENS
# ═══════════════════════════════════════════════════

class BaseTaxScreen(Screen):
    """Base screen with header and menu overlay support."""
    def __init__(self, title='', **kwargs):
        super().__init__(**kwargs)
        self.title = title
        root = BoxLayout(orientation='vertical')

        # Header
        header = HeaderBar(title_text=title)
        header.menu_btn.bind(on_release=lambda btn: self.open_menu())
        root.add_widget(header)

        # Main scrollable content area — subclasses fill this
        self.scroll = ScrollView()
        self.content = BoxLayout(orientation='vertical', spacing=dp(8), padding=[dp(12), dp(8)])
        self.content.size_hint_y = None
        self.content.bind(minimum_height=self.content.setter('height'))
        self.scroll.add_widget(self.content)
        root.add_widget(self.scroll)

        # Menu overlay (starts hidden)
        self.menu_overlay = MenuOverlay(App.get_running_app())
        self.menu_overlay.opacity = 0
        root.add_widget(self.menu_overlay)

        self.add_widget(root)

    def open_menu(self):
        self.menu_overlay.open()

    def close_menu(self):
        self.menu_overlay.close()

    def on_enter(self):
        self.refresh()

    def refresh(self):
        """Override in subclasses."""
        pass


# ─── DASHBOARD ───
class DashboardScreen(BaseTaxScreen):
    def __init__(self, **kwargs):
        super().__init__(title='Beranda', **kwargs)

    def refresh(self):
        self.content.clear_widgets()
        db = TaxDB()
        calc = TaxCalculator()
        now = datetime.now()
        year = now.year

        self.content.add_widget(Label(
            text=f'Ringkasan {year}',
            font_size=sp(16), bold=True,
            color=NAVY_RGB, size_hint_y=None, height=dp(32),
            halign='left',
        ))

        # Stat cards
        pph21 = db.get_total_pph21(year)
        pph23 = db.get_total_pph23(year, now.month)
        pph_final = db.get_total_pph_final(year)

        stats_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        stats_grid.bind(minimum_height=stats_grid.setter('height'))

        for label, val in [
            ('PPh 21 Tahunan', f'Rp {pph21:,.0f}'),
            ('PPh 23 Bulan Ini', f'Rp {pph23:,.0f}'),
            ('PPh Final Tahun Ini', f'Rp {pph_final:,.0f}'),
            ('Status PPN Masa', 'Perlu Dilaporkan' if pph23 < 500000 else 'Lunas'),
        ]:
            stats_grid.add_widget(StatCard(label=label, value=val))
        stats_grid.height = dp(170)
        self.content.add_widget(stats_grid)

        # Deadlines
        self.content.add_widget(Label(
            text='Deadline Mendatang',
            font_size=sp(16), bold=True,
            color=NAVY_RGB, size_hint_y=None, height=dp(32),
            halign='left',
        ))

        today = date.today()
        deadlines = [
            (today.year, today.month, 10, 'SPT Masa PPN'),
            (today.year, today.month, 20, 'PPh 21 Masa'),
            (today.year, today.month, 20, 'PPh 23/26 Masa'),
            (today.year, 3, 31, 'Penyampaian SPT PPh Badan'),
            (today.year, 4, 30, 'Lapor SPT Tahunan PPh Badan'),
        ]
        for y, m, d, title in deadlines:
            try:
                dl = date(y, m, d)
                diff = (dl - today).days
                if diff < 0:
                    status = 'LEWAT'
                    title_display = f'{title} (LEWAT)'
                elif diff <= 7:
                    status = 'SEGERA'
                    title_display = title
                else:
                    status = 'OK'
                    title_display = title
                self.content.add_widget(DeadlineCard(
                    title=title_display,
                    date_str=dl.strftime('%d %b %Y'),
                    status=status,
                ))
            except ValueError:
                pass

        # Bottom spacer
        self.content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))


# ─── CALCULATOR ───
class CalculatorScreen(BaseTaxScreen):
    def __init__(self, **kwargs):
        super().__init__(title='Kalkulator Pajak', **kwargs)

    def refresh(self):
        self.content.clear_widgets()
        self._build_ui()

    def _build_ui(self):
        calc = TaxCalculator()

        # ── Tabs via simple buttons ──
        tab_bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.tab_indicators = {}
        tabs = ['PPh 21', 'PPh 23', 'PPN', 'PPh Badan']
        for i, tab_name in enumerate(tabs):
            btn = Button(
                text=tab_name, font_size=sp(13), bold=True,
                background_normal='', background_color=hex_rgb(NAVY) if i == 0 else hex_rgb(CREAM_DARK),
                color=hex_rgb(CREAM) if i == 0 else NAVY_RGB,
            )
            btn.bind(on_release=lambda b, idx=i, tn=tab_name: self._switch_tab(idx, tn))
            tab_bar.add_widget(btn)
            self.tab_indicators[i] = btn
        self.content.add_widget(tab_bar)

        # ── Tab content area ──
        self.tab_content = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        self.tab_content.bind(minimum_height=self.tab_content.setter('height'))
        self.content.add_widget(self.tab_content)

        # Result display
        self.result_label = Label(
            text='', font_size=sp(14), color=NAVY_RGB,
            size_hint_y=None, height=dp(80), halign='left', valign='middle',
            text_size=(Window.width - dp(40), None),
        )
        self.content.add_widget(self.result_label)

        self._active_tab = 0
        self._show_tab(0)

    def _switch_tab(self, idx, name):
        self._active_tab = idx
        for i, btn in self.tab_indicators.items():
            btn.background_color = hex_rgb(NAVY) if i == idx else hex_rgb(CREAM_DARK)
            btn.color = hex_rgb(CREAM) if i == idx else NAVY_RGB
        self._show_tab(idx)
        self.result_label.text = ''

    def _show_tab(self, idx):
        self.tab_content.clear_widgets()
        calc = TaxCalculator()

        if idx == 0:  # PPh 21
            self._add_input(self.tab_content, 'Gaji Bruto/Bulan (Rp)', 'pph21_gross', '50000000')
            self._add_input(self.tab_content, 'Jumlah Tanggungan (0-3)', 'pph21_dependents', '2')
            btn = Button(
                text='Hitung PPh 21 Masa',
                size_hint_y=None, height=dp(44),
                background_color=COPPER_RGB, color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda b: self._calc_pph21(calc))
            self.tab_content.add_widget(btn)

        elif idx == 1:  # PPh 23
            self._add_input(self.tab_content, 'Nilai Bruto (Rp)', 'pph23_amount', '10000000')
            spinner_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            spinner_box.add_widget(Label(
                text='Jenis:', font_size=sp(14),
                color=NAVY_RGB, size_hint_x=0.3,
            ))
            spinner = Spinner(
                text='Jasa', size_hint_x=0.7,
                values=('Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti', 'Hadiah'),
                background_color=(1, 1, 1, 1), color=NAVY_RGB,
            )
            self.pph23_spinner = spinner
            spinner_box.add_widget(spinner)
            self.tab_content.add_widget(spinner_box)

            btn = Button(
                text='Hitung PPh 23',
                size_hint_y=None, height=dp(44),
                background_color=COPPER_RGB, color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda b: self._calc_pph23(calc))
            self.tab_content.add_widget(btn)

        elif idx == 2:  # PPN
            self._add_input(self.tab_content, 'Harga DPP (Rp)', 'ppn_price', '10000000')
            spinner_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            spinner_box.add_widget(Label(
                text='Tarif:', font_size=sp(14),
                color=NAVY_RGB, size_hint_x=0.3,
            ))
            spinner = Spinner(
                text='11%', size_hint_x=0.7,
                values=('11%', '12%'),
                background_color=(1, 1, 1, 1), color=NAVY_RGB,
            )
            self.ppn_spinner = spinner
            spinner_box.add_widget(spinner)
            self.tab_content.add_widget(spinner_box)

            btn = Button(
                text='Hitung PPN',
                size_hint_y=None, height=dp(44),
                background_color=COPPER_RGB, color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda b: self._calc_ppn(calc))
            self.tab_content.add_widget(btn)

        elif idx == 3:  # PPh Badan
            self._add_input(self.tab_content, 'Laba Kena Pajak (Rp)', 'pph_badan_profit', '500000000')
            self._add_input(self.tab_content, 'Peredaran Bruto/Omzet (Rp)', 'pph_badan_omzet', '2000000000')
            btn = Button(
                text='Hitung PPh Badan',
                size_hint_y=None, height=dp(44),
                background_color=COPPER_RGB, color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda b: self._calc_pph_badan(calc))
            self.tab_content.add_widget(btn)

    def _add_input(self, container, hint, key, default=''):
        box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        inp = TextInput(
            hint_text=hint, text=default,
            multiline=False, input_filter='float',
        )
        setattr(self, key, inp)
        box.add_widget(inp)
        container.add_widget(box)

    def _get_val(self, attr):
        inp = getattr(self, attr, None)
        if inp and inp.text:
            try:
                return float(inp.text)
            except:
                return 0
        return 0

    def _calc_pph21(self, calc):
        gaji = self._get_val('pph21_gross')
        tang = int(getattr(self, 'pph21_dependents', TextInput(text='0')).text or 0)
        if gaji <= 0:
            self.result_label.text = 'Masukkan gaji bruto!'
            return
        try:
            pph, net, ptkp_desc = calc.pph21_monthly(gaji, tang)
            self.result_label.text = (
                f'PTKP: {ptkp_desc}\n'
                f'Gaji Bruto: Rp {gaji:,.0f}\n'
                f'PPh 21 Masa: Rp {pph:,.0f}\n'
                f'Take Home Pay: Rp {net - pph:,.0f}'
            )
        except Exception as e:
            self.result_label.text = f'Error: {e}'

    def _calc_pph23(self, calc):
        amount = self._get_val('pph23_amount')
        obj_type = self.pph23_spinner.text if hasattr(self, 'pph23_spinner') else 'Jasa'
        if amount <= 0:
            self.result_label.text = 'Masukkan nilai bruto!'
            return
        pph = calc.pph23(amount, obj_type)
        net = amount - pph
        self.result_label.text = (
            f'Jenis: {obj_type}\n'
            f'DPP: Rp {amount:,.0f}\n'
            f'PPh 23: Rp {pph:,.0f}\n'
            f'Dibayarkan: Rp {net:,.0f}'
        )

    def _calc_ppn(self, calc):
        price = self._get_val('ppn_price')
        tariff_str = self.ppn_spinner.text if hasattr(self, 'ppn_spinner') else '11%'
        tariff = float(tariff_str.replace('%', ''))
        if price <= 0:
            self.result_label.text = 'Masukkan harga DPP!'
            return
        ppn = calc.ppn(price, tariff)
        total = price + ppn
        self.result_label.text = (
            f'DPP: Rp {price:,.0f}\n'
            f'PPN {tariff:.0f}%: Rp {ppn:,.0f}\n'
            f'Harga + PPN: Rp {total:,.0f}'
        )

    def _calc_pph_badan(self, calc):
        profit = self._get_val('pph_badan_profit')
        omzet = self._get_val('pph_badan_omzet')
        if profit <= 0:
            self.result_label.text = 'Masukkan laba kena pajak!'
            return
        pph = calc.pph_badan(profit, omzet)
        rate = (pph / profit * 100) if profit > 0 else 0
        self.result_label.text = (
            f'Laba Kena Pajak: Rp {profit:,.0f}\n'
            f'Omzet: Rp {omzet:,.0f}\n'
            f'PPh Badan: Rp {pph:,.0f}\n'
            f'Tarif Efektif: {rate:.1f}%'
        )


# ─── CALENDAR ───
class TaxCalendarScreen(BaseTaxScreen):
    def __init__(self, **kwargs):
        super().__init__(title='Kalender Pajak', **kwargs)

    def refresh(self):
        self.content.clear_widgets()
        today = date.today()
        y, m = today.year, today.month
        month_name = calendar.month_name[m].upper()

        self.content.add_widget(Label(
            text=f'{month_name} {y}',
            font_size=sp(18), bold=True,
            color=NAVY_RGB, size_hint_y=None, height=dp(36),
            halign='center',
        ))

        # Day headers
        day_header = GridLayout(cols=7, spacing=dp(2), size_hint_y=None, height=dp(30))
        for d in ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']:
            day_header.add_widget(Label(
                text=d, bold=True, font_size=sp(12), color=NAVY_RGB,
            ))
        self.content.add_widget(day_header)

        # Calendar grid
        cal = calendar.monthcalendar(y, m)
        deadlines = {10: 'PPN', 15: 'PPh Final', 20: 'PPh 21/23', 21: 'PPh 26'}
        grid = GridLayout(cols=7, spacing=dp(2), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for week in cal:
            for day_num in week:
                if day_num == 0:
                    grid.add_widget(Label(text='', size_hint_y=None, height=dp(44)))
                else:
                    is_deadline = day_num in deadlines
                    d = date(y, m, day_num)
                    is_today = d == today
                    is_past = d < today

                    text = str(day_num)
                    if is_deadline:
                        text += f'\n{deadlines[day_num]}'

                    cell = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(48), padding=[dp(2)])
                    if is_today:
                        with cell.canvas.before:
                            Color(*COPPER_RGB)
                            RoundedRectangle(pos=cell.pos, size=cell.size, radius=[dp(4)])
                    elif is_deadline and not is_past:
                        with cell.canvas.before:
                            Color(*hex_rgb(GOLD), a=0.3)
                            RoundedRectangle(pos=cell.pos, size=cell.size, radius=[dp(4)])

                    lbl = Label(
                        text=text,
                        font_size=sp(10 if is_deadline else 13),
                        color=ERROR_RGB if (is_past and is_deadline) else (
                            (1, 1, 1, 1) if is_today else NAVY_RGB
                        ),
                        halign='center', valign='middle',
                    )
                    lbl.bind(size=lbl.setter('text_size'))
                    cell.add_widget(lbl)
                    grid.add_widget(cell)

        self.content.add_widget(grid)

        # Legend
        self.content.add_widget(Label(
            text='Deadline: PPN tgl 10, PPh Final tgl 15, PPh 21/23 tgl 20',
            font_size=sp(11), color=SUBTLE_RGB,
            size_hint_y=None, height=dp(28),
            halign='left',
        ))
        self.content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))


# ─── WITHHOLDING LOG ───
class WithholdingLogScreen(BaseTaxScreen):
    def __init__(self, **kwargs):
        super().__init__(title='Log PPh 23/26', **kwargs)
        self._records = []

    def refresh(self):
        self.content.clear_widgets()
        db = TaxDB()
        self._records = db.get_all_withholding()

        # Add button
        add_btn = Button(
            text='+ Tambah Potongan PPh',
            size_hint_y=None, height=dp(48),
            background_color=COPPER_RGB, color=(1, 1, 1, 1),
        )
        add_btn.bind(on_release=lambda b: self.show_add_popup())
        self.content.add_widget(add_btn)

        if not self._records:
            self.content.add_widget(Label(
                text='Belum ada data transaksi.\n\nTekan tombol di atas untuk\nmencatat potongan PPh 23/26.',
                font_size=sp(14), color=SUBTLE_RGB,
                halign='center', valign='middle',
                size_hint_y=None, height=dp(120),
            ))
            return

        for r in self._records:
            rid, vendor, amount, obj_type, pph_amount, created_at = r
            self.content.add_widget(RecordRow(
                title=f'{vendor} — Rp {amount:,.0f}',
                subtitle=f'{obj_type} | {created_at}',
                on_delete=lambda btn, rid=rid: self.delete_record(rid),
            ))

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(Label(
            text='Tambah Potongan PPh',
            font_size=sp(16), bold=True, color=NAVY_RGB,
            size_hint_y=None, height=dp(30),
        ))

        vendor_inp = TextInput(hint_text='Nama Vendor/Penerima', multiline=False)
        amount_inp = TextInput(hint_text='Jumlah Bruto (Rp)', multiline=False, input_filter='float')
        type_inp = Spinner(text='Jasa', values=('Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti'))
        tariff_inp = Spinner(text='2%', values=('2%', '15%', '20%'))

        content.add_widget(vendor_inp)
        content.add_widget(amount_inp)
        content.add_widget(type_inp)
        content.add_widget(tariff_inp)

        btn_box = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        save_btn = Button(text='Simpan', background_color=COPPER_RGB, color=(1, 1, 1, 1))
        cancel_btn = Button(text='Batal', background_color=hex_rgb(CHARCOAL), color=(1, 1, 1, 1))
        btn_box.add_widget(save_btn)
        btn_box.add_widget(cancel_btn)
        content.add_widget(btn_box)

        popup = Popup(title='PPh 23/26', content=content, size_hint=(0.85, 0.55))

        def on_save(_):
            try:
                db = TaxDB()
                db.add_withholding(
                    vendor=vendor_inp.text,
                    amount=float(amount_inp.text or 0),
                    obj_type=type_inp.text,
                    tariff_label=tariff_inp.text,
                )
                popup.dismiss()
                self.refresh()
            except Exception as e:
                err = Popup(title='Error', content=Label(text=str(e)), size_hint=(0.7, 0.3))
                err.open()

        def on_cancel(_):
            popup.dismiss()

        save_btn.bind(on_release=on_save)
        cancel_btn.bind(on_release=on_cancel)
        popup.open()

    def delete_record(self, rid):
        db = TaxDB()
        db.delete_withholding(rid)
        self.refresh()


# ─── DOCUMENTS ───
class DocumentScreen(BaseTaxScreen):
    def __init__(self, **kwargs):
        super().__init__(title='Dokumen Pajak', **kwargs)
        self._docs = []

    def refresh(self):
        self.content.clear_widgets()
        db = TaxDB()
        self._docs = db.get_all_documents()

        add_btn = Button(
            text='+ Tambah Dokumen',
            size_hint_y=None, height=dp(48),
            background_color=COPPER_RGB, color=(1, 1, 1, 1),
        )
        add_btn.bind(on_release=lambda b: self.show_add_popup())
        self.content.add_widget(add_btn)

        if not self._docs:
            self.content.add_widget(Label(
                text='Belum ada dokumen.\n\nTekan tombol di atas untuk\nmencatat dokumen perpajakan.',
                font_size=sp(14), color=SUBTLE_RGB,
                halign='center', valign='middle',
                size_hint_y=None, height=dp(120),
            ))
            return

        for d in self._docs:
            did, title, category, status, created_at = d
            self.content.add_widget(RecordRow(
                title=title,
                subtitle=f'{category} | {status} | {created_at}',
                on_delete=lambda btn, did=did: self.delete_doc(did),
            ))

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(Label(
            text='Tambah Dokumen',
            font_size=sp(16), bold=True, color=NAVY_RGB,
            size_hint_y=None, height=dp(30),
        ))

        title_inp = TextInput(hint_text='Nama Dokumen (e.g. Faktur Maret)', multiline=False)
        cat_inp = Spinner(text='Faktur Pajak', values=('Faktur Pajak', 'SPT', 'Bukti Potong', 'Laporan', 'Lainnya'))
        status_inp = Spinner(text='Lengkap', values=('Lengkap', 'Kurang', 'Arsip', 'Dalam Proses'))

        content.add_widget(title_inp)
        content.add_widget(cat_inp)
        content.add_widget(status_inp)

        btn_box = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        save_btn = Button(text='Simpan', background_color=COPPER_RGB, color=(1, 1, 1, 1))
        cancel_btn = Button(text='Batal', background_color=hex_rgb(CHARCOAL), color=(1, 1, 1, 1))
        btn_box.add_widget(save_btn)
        btn_box.add_widget(cancel_btn)
        content.add_widget(btn_box)

        popup = Popup(title='Dokumen Baru', content=content, size_hint=(0.85, 0.50))

        def on_save(_):
            try:
                db = TaxDB()
                db.add_document(
                    title=title_inp.text,
                    category=cat_inp.text,
                    status=status_inp.text,
                )
                popup.dismiss()
                self.refresh()
            except Exception as e:
                err = Popup(title='Error', content=Label(text=str(e)), size_hint=(0.7, 0.3))
                err.open()

        def on_cancel(_):
            popup.dismiss()

        save_btn.bind(on_release=on_save)
        cancel_btn.bind(on_release=on_cancel)
        popup.open()

    def delete_doc(self, did):
        db = TaxDB()
        db.delete_document(did)
        self.refresh()


# ═══════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════
class CorporateTaxApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Corporate Tax Manager'

    def build(self):
        # Init database
        TaxDB().init_tables()

        # Window config
        Window.clearcolor = hex_rgb(CREAM)

        # Screen manager
        sm = ScreenManager()
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(CalculatorScreen(name='calculator'))
        sm.add_widget(TaxCalendarScreen(name='calendar'))
        sm.add_widget(WithholdingLogScreen(name='withholding'))
        sm.add_widget(DocumentScreen(name='documents'))

        return sm

    def close_menu(self):
        """Close menu on any screen."""
        if self.root.current_screen:
            screen = self.root.current_screen
            if hasattr(screen, 'menu_overlay'):
                screen.menu_overlay.close()


if __name__ == '__main__':
    CorporateTaxApp().run()
