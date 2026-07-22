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
from kivy.graphics import Color, RoundedRectangle

from data.tax_calculator import TaxCalculator
from data.tax_db import TaxDB

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
ERROR = hex2rgb('#B42318')
GREEN = hex2rgb('#2F7D57')
WARNING = hex2rgb('#B7791F')
BORDER = hex2rgb('#E2E8F0')

# Backward-compatible aliases used in screens
NAVY = PRIMARY
CHARCOAL = TEXT_SECONDARY
CREAM = BG
CREAM_D = SURFACE_MUTED
COPPER = ACCENT
PAPER = SURFACE


def make_label(text, size=14, color=TEXT, bold=False, halign='left', height=None):
    widget = Label(
        text=str(text),
        font_size=sp(size),
        color=color,
        bold=bold,
        halign=halign,
        valign='middle',
    )
    widget.size_hint_y = None
    widget.height = dp(height or (size + 16))
    widget.bind(size=lambda w, _v: setattr(w, 'text_size', (w.width, None)))
    return widget


def make_button(text, bg=PRIMARY, fg=WHITE, height=44):
    return Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal='',
        background_color=bg,
        color=fg,
        font_size=sp(13),
        bold=True,
    )


def paint_card(widget):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*SURFACE)
        widget._card_bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(10)])
    widget.bind(
        pos=lambda w, _v: setattr(w._card_bg, 'pos', w.pos),
        size=lambda w, _v: setattr(w._card_bg, 'size', w.size),
    )


def paint_bar(widget, color):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        widget._bar_bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[0])
    widget.bind(
        pos=lambda w, _v: setattr(w._bar_bg, 'pos', w.pos),
        size=lambda w, _v: setattr(w._bar_bg, 'size', w.size),
    )


# ═══════════════════════════════════════════════════════════
# BASE SCREEN
# ═══════════════════════════════════════════════════════════
class BaseScreen(Screen):
    def __init__(self, name, title_text, **kwargs):
        super().__init__(name=name, **kwargs)
        root = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(12), dp(4)])
        paint_bar(header, SURFACE)
        header.add_widget(make_label(title_text, 17, TEXT, True, 'left'))
        root.add_widget(header)

        self.scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=[dp(12), dp(10), dp(12), dp(16)],
            size_hint_y=None,
        )
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_enter(self, *args):
        self.body.clear_widgets()
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
        self.body.add_widget(make_label(f'Ringkasan {now.year}', 16, NAVY, True, 'left', 28))

        total_month = total_year = doc_count = 0
        try:
            data = TaxDB().get_dashboard_data()
            total_month = float(data.get('total_due_this_month', 0) or 0)
            total_year = float(data.get('total_year', 0) or 0)
            doc_count = int(data.get('doc_count', 0) or 0)
        except Exception:
            pass

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(140))
        for title, value in [
            ('PPh 23/26 Bulan', f'Rp {total_month:,.0f}'),
            ('Total Tahun', f'Rp {total_year:,.0f}'),
            ('Dokumen', str(doc_count)),
            ('Status PPN', 'Dilaporkan' if now.day >= 10 else 'Menunggu'),
        ]:
            card = BoxLayout(orientation='vertical', padding=[dp(10), dp(8)], spacing=dp(2), size_hint_y=None, height=dp(64))
            paint_card(card)
            card.add_widget(make_label(title, 11, SUBTLE, False, 'center', 18))
            card.add_widget(make_label(value, 15, NAVY, True, 'center', 24))
            grid.add_widget(card)
        self.body.add_widget(grid)

        self.body.add_widget(make_label('Deadline Mendatang', 16, NAVY, True, 'left', 28))
        for day_num, name in [(10, 'SPT Masa PPN'), (15, 'PPh Final'), (20, 'PPh 21/23'), (21, 'PPh 26')]:
            try:
                dl = date(now.year, now.month, day_num)
                diff = (dl - now).days
            except ValueError:
                diff = 0
            status = 'LEWAT' if diff < 0 else ('SEGERA' if diff <= 7 else 'OK')
            color = ERROR if diff < 0 else (WARNING if diff <= 7 else GREEN)
            row = BoxLayout(size_hint_y=None, height=dp(44), padding=[dp(10), dp(6)], spacing=dp(8))
            paint_card(row)
            row.add_widget(make_label(name, 13, NAVY, True, 'left'))
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
        tab_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for idx, name in enumerate(['PPh 21', 'PPh 23', 'PPh 26', 'PPN', 'Badan', 'Final']):
            button = make_button(
                name,
                PRIMARY if idx == self.active_tab else SURFACE_MUTED,
                WHITE if idx == self.active_tab else TEXT,
                height=36,
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
            self.final_type = self.add_spinner('Jenis Final', ['Sewa Tanah 10%', 'Konstruksi', 'Pesangon'], 'Sewa Tanah 10%')
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
            else:
                result = self.calc.pph_final_pesangon(amount)
            self.result_label.text = (
                f"Jenis: {result.get('jenis', kind)}\n"
                f"Nilai: Rp {amount:,.0f}\n"
                f"Tarif: {result.get('tarif', '-')}\n"
                f"PPh Final: Rp {result.get('pph', 0):,.0f}\n"
                f"Diterima: Rp {result.get('diterima', 0):,.0f}"
            )
        except Exception as exc:
            self.result_label.text = f'Error: {exc}'


# ═══════════════════════════════════════════════════════════
# WITHHOLDING LOG
# ═══════════════════════════════════════════════════════════
class WithholdingScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__('withholding', 'Log PPh 23/26', **kwargs)

    def build_ui(self):
        add_btn = make_button('+ Tambah Transaksi', height=44)
        add_btn.bind(on_release=lambda _b: self.show_add_popup())
        self.body.add_widget(add_btn)

        try:
            rows, total = TaxDB().get_all_withholding(limit=50)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error DB: {exc}', 12, ERROR, False, 'left', 50))
            return

        if not rows:
            self.body.add_widget(make_label('Belum ada transaksi', 14, SUBTLE, False, 'center', 80))
            return

        self.body.add_widget(make_label(f'{total} transaksi', 12, SUBTLE, False, 'left', 20))
        for row in rows:
            card = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(10), dp(6)], spacing=dp(8))
            paint_card(card)
            left = f"{row.get('vendor', '-')} ({row.get('obj_type', '-')})"
            card.add_widget(make_label(left, 12, NAVY, True, 'left'))
            card.add_widget(make_label(f"Rp {float(row.get('pph_amount', 0) or 0):,.0f}", 12, ERROR, True, 'right'))
            self.body.add_widget(card)

    def show_add_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(make_label('Tambah Potongan PPh', 15, NAVY, True, 'left', 28))

        vendor = TextInput(hint_text='Nama Vendor', multiline=False, size_hint_y=None, height=dp(38))
        amount = TextInput(hint_text='Jumlah Bruto (Rp)', multiline=False, input_filter='float', size_hint_y=None, height=dp(38))
        obj_type = Spinner(text='Jasa', values=['Jasa', 'Sewa', 'Dividen', 'Bunga', 'Royalti'], size_hint_y=None, height=dp(38))
        content.add_widget(vendor)
        content.add_widget(amount)
        content.add_widget(obj_type)

        popup = Popup(title='PPh 23/26', content=content, size_hint=(0.9, 0.55), auto_dismiss=False)

        def save(_btn):
            try:
                TaxDB().add_withholding(
                    vendor=vendor.text.strip() or 'Vendor',
                    amount=float(amount.text or 0),
                    obj_type=obj_type.text,
                    tax_code='pph23',
                    tariff_label='2%',
                    description='',
                )
                popup.dismiss()
                self.on_enter()
            except Exception as exc:
                err = Popup(title='Error', content=make_label(str(exc), 12, ERROR, False, 'center', 60), size_hint=(0.8, 0.3))
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

    def build_ui(self):
        add_btn = make_button('+ Tambah Dokumen', height=44)
        add_btn.bind(on_release=lambda _b: self.show_add_popup())
        self.body.add_widget(add_btn)

        try:
            docs, total = TaxDB().get_all_documents(limit=50)
        except Exception as exc:
            self.body.add_widget(make_label(f'Error DB: {exc}', 12, ERROR, False, 'left', 50))
            return

        if not docs:
            self.body.add_widget(make_label('Belum ada dokumen', 14, SUBTLE, False, 'center', 80))
            return

        self.body.add_widget(make_label(f'{total} dokumen', 12, SUBTLE, False, 'left', 20))
        for doc in docs:
            card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(78),
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
            card.add_widget(make_label(f'{title}', 13, TEXT, True, 'left', 22))
            card.add_widget(make_label(f'{category} · {status} · {period}', 11, SUBTLE, False, 'left', 18))
            self.body.add_widget(card)

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
                    size_hint=(0.8, 0.3),
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
        self.body.add_widget(make_label(f'{month_name} {now.year}', 18, NAVY, True, 'center', 32))

        header = GridLayout(cols=7, spacing=dp(2), size_hint_y=None, height=dp(28))
        for day_name in ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']:
            header.add_widget(make_label(day_name, 11, NAVY, True, 'center', 24))
        self.body.add_widget(header)

        deadlines = {10: 'PPN', 15: 'Final', 20: 'P21/23', 21: 'P26'}
        weeks = calendar.monthcalendar(now.year, now.month)
        grid = GridLayout(cols=7, spacing=dp(2), size_hint_y=None, height=dp(len(weeks) * 44))
        for week in weeks:
            for day_num in week:
                if day_num == 0:
                    grid.add_widget(Widget(size_hint_y=None, height=dp(42)))
                    continue
                text = str(day_num)
                color = NAVY
                if day_num in deadlines:
                    text = f'{day_num}\n{deadlines[day_num]}'
                    color = ERROR if day_num < now.day else GREEN
                elif day_num == now.day:
                    color = ACCENT
                grid.add_widget(make_label(text, 10, color, True, 'center', 42))
        self.body.add_widget(grid)
        self.body.add_widget(make_label('PPN tgl 10 | Final tgl 15 | PPh 21/23 tgl 20 | PPh 26 tgl 21', 11, SUBTLE, False, 'left', 28))


# ═══════════════════════════════════════════════════════════
# ERROR FALLBACK SCREEN
# ═══════════════════════════════════════════════════════════
class ErrorScreen(Screen):
    def __init__(self, message, **kwargs):
        super().__init__(name='error', **kwargs)
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        paint_bar(box, CREAM)
        box.add_widget(make_label('Gagal Memulai Aplikasi', 18, ERROR, True, 'center', 36))
        box.add_widget(make_label(message, 12, NAVY, False, 'left', 220))
        self.add_widget(box)


# ═══════════════════════════════════════════════════════════
# ROOT LAYOUT WITH BOTTOM NAV
# ═══════════════════════════════════════════════════════════
class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(DashboardScreen())
        self.sm.add_widget(CalculatorScreen())
        self.sm.add_widget(WithholdingScreen())
        self.sm.add_widget(DocumentsScreen())
        self.sm.add_widget(CalendarScreen())
        self.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(2), padding=[dp(4), dp(4)])
        paint_bar(nav, SURFACE)
        self.nav_buttons = {}
        for screen_name, title in [
            ('dashboard', 'Beranda'),
            ('calculator', 'Hitung'),
            ('withholding', 'Log'),
            ('documents', 'Dokumen'),
            ('calendar', 'Kalender'),
        ]:
            button = make_button(
                title,
                PRIMARY if screen_name == 'dashboard' else SURFACE_MUTED,
                WHITE if screen_name == 'dashboard' else TEXT,
                44,
            )
            button.bind(on_release=lambda _b, n=screen_name: self.goto(n))
            nav.add_widget(button)
            self.nav_buttons[screen_name] = button
        self.add_widget(nav)

    def goto(self, screen_name):
        self.sm.current = screen_name
        for name, button in self.nav_buttons.items():
            selected = name == screen_name
            button.background_color = PRIMARY if selected else SURFACE_MUTED
            button.color = WHITE if selected else TEXT


# ═══════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════
class CorporateTaxApp(App):
    def build(self):
        Window.clearcolor = CREAM
        self.title = 'Corporate Tax Manager'
        try:
            TaxDB().init_tables()
            return RootLayout()
        except Exception as exc:
            detail = f'{exc}\n\n{traceback.format_exc()}'
            return ErrorScreen(detail)


if __name__ == '__main__':
    CorporateTaxApp().run()
