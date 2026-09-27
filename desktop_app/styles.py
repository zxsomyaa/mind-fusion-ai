"""Global QSS stylesheet, built from the same color tokens the web app uses."""

from data import COLORS as C

def build_stylesheet():
    """Built on demand (not at import) so it always reflects the active theme."""
    return f"""
QWidget {{
    background: {C['bg']};
    color: {C['text']};
    font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background: {C['bg']};
}}

QScrollArea > QWidget > QWidget {{
    background: {C['bg']};
}}

/* Labels sit on top of cards, so they must not paint the page colour -
   otherwise every line of text gets a visible off-white strip behind it. */
QLabel {{
    background: transparent;
}}

QWidget#flowHost {{ background: transparent; }}

/* Small round icon buttons (mic, camera, delete, affirmation arrows). The
   normal button padding (10px 20px) would leave no room for the glyph. */
QPushButton#iconBtn {{
    background: {C['primary_pale']};
    color: {C['primary']};
    border: none;
    border-radius: 18px;
    padding: 0;
    font-size: 16px;
    font-weight: 400;
    min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
}}
QPushButton#iconBtn:hover {{ background: {C['primary_light']}; color: {C['on_primary']}; }}
QPushButton#iconBtn:disabled {{ background: {C['border']}; color: {C['text_muted']}; }}

/* --- Cards / surfaces --- */
QFrame#card {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 16px;
}}

/* --- Sidebar navigation --- */
QWidget#sidebar {{
    background: {C['surface']};
    border-right: 1px solid {C['border']};
}}
QPushButton#navBtn {{
    background: transparent;
    color: {C['text_muted']};
    text-align: left;
    padding: 11px 14px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton#navBtn:hover {{ background: {C['bg']}; color: {C['text']}; }}
QPushButton#navBtn:checked {{
    background: {C['primary_pale']};
    color: {C['primary']};
    font-weight: 700;
}}

/* --- Header bar --- */
QFrame#header {{
    background: {C['surface']};
    border-bottom: 1px solid {C['border']};
}}
QLabel#logo {{
    font-size: 18px;
    font-weight: 700;
    color: {C['primary']};
}}

/* --- Buttons --- */
QPushButton {{
    background: {C['primary']};
    color: {C['on_primary']};
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {C['primary_light']}; }}
QPushButton:pressed {{ background: {C['primary']}; padding-top: 11px; padding-bottom: 9px; }}
QPushButton:disabled {{ background: {C['border']}; color: {C['text_muted']}; }}

QPushButton#ghost {{
    background: transparent;
    color: {C['text_muted']};
    border: 2px solid {C['border']};
}}
QPushButton#ghost:hover {{ border-color: {C['primary']}; color: {C['primary']}; background: {C['primary_pale']}; }}

QPushButton#ghost:checked {{ border-color: {C['primary']}; background: {C['primary_pale']}; color: {C['primary']}; }}

QCheckBox {{ spacing: 10px; background: transparent; font-size: 14px; padding: 4px 0; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 6px;
    border: 2px solid {C['border']}; background: {C['surface']};
}}
QCheckBox::indicator:hover {{ border-color: {C['primary_light']}; }}
QCheckBox::indicator:checked {{ background: {C['sage']}; border-color: {C['sage']}; }}

QPushButton#stepBtn {{
    background: {C['primary_pale']}; color: {C['primary']}; border: none;
    padding: 0; border-radius: 8px; font-size: 16px; font-weight: 700;
    min-width: 30px; max-width: 30px; min-height: 36px; max-height: 36px;
}}
QPushButton#stepBtn:hover {{ background: {C['primary_light']}; color: {C['on_primary']}; }}

/* small round button for list rows (delete) */
QPushButton#tinyBtn {{
    background: {C['primary_pale']}; color: {C['primary']}; border: none; border-radius: 11px;
    padding: 0; font-size: 13px; font-weight: 400;
    min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px;
}}
QPushButton#tinyBtn:hover {{ background: {C['primary_light']}; color: {C['on_primary']}; }}

/* dropdown section headers (Insights) */
QFrame#sectionHeader {{
    background: transparent; border: 1px solid {C['border']}; border-radius: 10px;
}}
QFrame#sectionHeader:hover {{ background: {C['primary_pale']}; border-color: {C['primary_light']}; }}
QFrame#sectionHeader:focus {{ border-color: {C['primary']}; }}

/* time-range pills on the Insights page */
QPushButton#rangePill {{
    background: {C['surface']}; color: {C['text_muted']};
    border: 1px solid {C['border']}; border-radius: 16px;
    padding: 7px 16px; font-size: 12px; font-weight: 600;
}}
QPushButton#rangePill:hover {{ border-color: {C['primary_light']}; color: {C['primary']}; }}
QPushButton#rangePill:checked {{ background: {C['primary']}; color: {C['on_primary']}; border-color: {C['primary']}; }}

/* selectable option cards (age group) */
QPushButton#choiceCard {{
    background: {C['surface']}; color: {C['text']};
    border: 2px solid {C['border']}; border-radius: 14px;
    padding: 14px 10px; font-size: 13px; font-weight: 500; text-align: center;
    min-height: 44px;
}}
QPushButton#choiceCard:hover {{ border-color: {C['primary_light']}; background: {C['primary_pale']}; }}
QPushButton#choiceCard:checked {{
    border-color: {C['primary']}; background: {C['primary_pale']}; color: {C['primary']}; font-weight: 700;
}}

/* form field with a validation error */
QLineEdit[error="true"] {{ border-color: #E07A5F; }}

/* full-width primary/secondary buttons on the setup screens */
QPushButton#bigBtn {{ padding: 13px 22px; font-size: 15px; border-radius: 12px; min-height: 22px; }}
QPushButton#bigBtnGhost {{
    background: transparent; color: {C['text_muted']}; border: 2px solid {C['border']};
    padding: 11px 22px; font-size: 15px; border-radius: 12px; min-height: 22px; font-weight: 600;
}}
QPushButton#bigBtnGhost:hover {{ border-color: {C['primary']}; color: {C['primary']}; background: {C['primary_pale']}; }}

QPushButton#linkButton {{
    background: transparent;
    color: {C['sage']};
    border: none;
    text-decoration: underline;
    padding: 2px;
    font-weight: 400;
}}
QPushButton#linkButton:hover {{ color: {C['primary']}; background: transparent; }}

/* --- Inputs --- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox {{
    background: {C['surface']};
    border: 2px solid {C['border']};
    border-radius: 10px;
    padding: 9px 13px;
    selection-background-color: {C['primary_pale']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{
    border-color: {C['primary']};
}}
/* an editable dropdown contains its own text box - it must not get a second border */
QComboBox QLineEdit {{ border: none; background: transparent; padding: 0; }}
QComboBox QAbstractItemView {{
    background: {C['surface']}; color: {C['text']}; border: 1px solid {C['border']};
    selection-background-color: {C['primary_pale']}; selection-color: {C['primary']}; outline: none;
}}
QListWidget {{
    background: {C['surface']};
    border: 2px solid {C['border']};
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background: {C['primary_pale']};
    color: {C['primary']};
}}

/* --- Tabs --- */
QTabWidget::pane {{
    border: none;
    background: {C['bg']};
}}
QTabBar::tab {{
    background: {C['surface']};
    color: {C['text_muted']};
    padding: 12px 18px;
    margin-right: 3px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border: 1px solid {C['border']};
    border-bottom: none;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {C['primary']};
    font-weight: 700;
    background: {C['bg']};
}}
QTabBar::tab:hover:!selected {{
    color: {C['primary']};
}}

/* --- Scroll areas --- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['primary_light']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* --- Progress bar (breathing timer, model download) --- */
QProgressBar {{
    border: none;
    border-radius: 8px;
    background: {C['border']};
    text-align: center;
    height: 16px;
}}
QProgressBar::chunk {{
    background: {C['primary']};
    border-radius: 8px;
}}

/* --- Dialogs --- */
QDialog {{
    background: {C['bg']};
}}
"""


APP_STYLESHEET = build_stylesheet()  # light-theme default, kept for callers that import the constant


def card_frame_qss():
    return f"background:{C['surface']}; border:1px solid {C['border']}; border-radius:16px;"
