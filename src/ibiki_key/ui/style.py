from __future__ import annotations


APP_STYLE = r"""
* {
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #F4F6FF;
}
QMainWindow, QWidget#AppRoot, QDialog { background: #090A10; }
QWidget { outline: none; }
QFrame#Sidebar { background: #0D0E14; border-right: 1px solid #1E202A; }
QFrame#TopBar { background: #0D0E14; border-bottom: 1px solid #1E202A; }
QFrame#Card {
    background: #12131A;
    border: 1px solid #20232D;
    border-radius: 15px;
}
QFrame#Card:hover { border-color: #2B2F3B; }
QFrame#Card[dashboardPanel="true"] { background: #111219; }
QFrame#Card[keyboardCard="true"] { background: #101117; border-color: #1D202A; }
QFrame#NowCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #171321, stop:1 #11131A);
    border: 1px solid #332651;
    border-radius: 16px;
}
QLabel#AppTitle { font-size: 20px; font-weight: 700; }
QLabel#PageTitle { font-size: 25px; font-weight: 750; }
QLabel#SectionTitle { font-size: 16px; font-weight: 650; }
QLabel#Muted, QLabel[muted="true"] { color: #9299B2; }
QLabel#Metric { font-size: 28px; font-weight: 750; color: #FFFFFF; }
QLabel#Accent { color: #A78BFA; font-weight: 650; }
QLabel#StatusDotOn { color: #2DD4BF; font-size: 18px; }
QLabel#StatusDotOff { color: #FB7185; font-size: 18px; }
QLabel#PanelIcon { font-size: 18px; font-weight: 750; }
QLabel#CountBadge {
    min-width: 23px;
    min-height: 23px;
    background: #211A35;
    border: 1px solid #3A2A5D;
    border-radius: 11px;
    color: #C4B5FD;
    font-size: 11px;
    font-weight: 750;
    qproperty-alignment: AlignCenter;
}
QLabel#Eyebrow { color: #A78BFA; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
QLabel#NowStatus { font-size: 12px; font-weight: 700; }
QLabel#LayerBadge {
    background: #221A38;
    border: 1px solid #3D2C62;
    border-radius: 8px;
    color: #C4B5FD;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 650;
}
QFrame#NowSurface { background: #0E1017; border: 1px solid #242735; border-radius: 10px; }
QLabel#AppMark { color: #8B5CF6; font-size: 20px; }
QLabel#NowApp { color: #F7F5FF; font-size: 13px; font-weight: 700; }
QFrame#MiniStat { background: #11121A; border: 1px solid #252836; border-radius: 9px; }
QLabel#MiniStatValue { color: #EDE9FE; font-size: 14px; font-weight: 750; }
QLabel#MiniStatCaption { color: #7F879D; font-size: 9px; }
QFrame#ActivitySurface { background: #11121A; border: 1px solid #29243A; border-radius: 10px; }
QLabel#ActivityInput { color: #E9E5FF; font-size: 12px; font-weight: 700; }
QLabel#MacroName { color: #ECEEFA; font-size: 12px; font-weight: 650; }
QLabel#MacroMeta { color: #7F879D; font-size: 10px; }
QLabel#DashboardEmpty { color: #6F7589; font-size: 12px; }
QFrame#MacroQuickRow { background: #0E1017; border: 1px solid #20232D; border-radius: 10px; }
QFrame#MacroQuickRow[running="true"] { background: #171229; border-color: #594094; }
QPushButton {
    min-height: 36px;
    padding: 0 14px;
    background: #20253A;
    border: 1px solid #313851;
    border-radius: 9px;
    font-weight: 600;
}
QPushButton:hover { background: #292F47; border-color: #46506E; }
QPushButton:pressed { background: #171B2A; }
QPushButton:disabled { color: #5D647C; background: #151824; border-color: #242838; }
QPushButton[primary="true"] {
    background: #7C3AED;
    border-color: #8B5CF6;
    color: white;
}
QPushButton[primary="true"]:hover { background: #8B5CF6; }
QPushButton[danger="true"] { background: #3B1B28; border-color: #713044; color: #FDA4AF; }
QPushButton[dashboardLink="true"] {
    min-height: 29px;
    background: transparent;
    border: 0;
    color: #A78BFA;
    font-size: 11px;
}
QPushButton[dashboardLink="true"]:hover { background: #191522; color: #D8CCFF; }
QPushButton[miniToggle="true"] {
    min-width: 32px;
    max-width: 32px;
    min-height: 25px;
    max-height: 25px;
    padding: 0;
    background: #191B25;
    border: 1px solid #303342;
    border-radius: 7px;
    color: #747B90;
    font-size: 9px;
    font-weight: 800;
}
QPushButton[miniToggle="true"]:checked {
    background: #2A1C4A;
    border-color: #704BC0;
    color: #D8CCFF;
}
QPushButton[iconButton="true"] {
    min-width: 27px;
    max-width: 27px;
    min-height: 27px;
    max-height: 27px;
    padding: 0;
    background: #1A1C27;
    border-color: #2D3040;
    border-radius: 8px;
    color: #B9BFD1;
}
QPushButton[iconButton="true"]:hover { background: #2A2040; color: #D8CCFF; }
QPushButton[iconButton="true"][running="true"] { background: #3B1B28; color: #FDA4AF; }
QPushButton[quickAction="true"] {
    min-height: 29px;
    padding: 0 9px;
    background: #191724;
    border-color: #2F2941;
    color: #C4B5FD;
    font-size: 10px;
}
QPushButton[quickAction="true"]:hover { background: #272038; border-color: #55417A; }
QPushButton[nav="true"] {
    min-height: 42px;
    text-align: left;
    padding-left: 15px;
    border: 0;
    background: transparent;
    color: #A8AEC3;
}
QPushButton[nav="true"]:hover { background: #171B29; color: #FFFFFF; }
QPushButton[nav="true"]:checked {
    background: #21183D;
    color: #C4B5FD;
    border-left: 3px solid #8B5CF6;
    border-radius: 7px;
}
QPushButton[nav="true"][compact="true"] {
    text-align: center;
    padding: 0;
    font-size: 17px;
}
QPushButton[topIcon="true"] {
    min-width: 34px;
    max-width: 34px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    margin-right: 8px;
    background: transparent;
    border: 0;
    color: #9BA2B8;
    font-size: 17px;
}
QPushButton[topIcon="true"]:hover { background: #1A1C25; color: #FFFFFF; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {
    min-height: 36px;
    padding: 0 10px;
    background: #0D101A;
    border: 1px solid #30364C;
    border-radius: 8px;
    selection-background-color: #7C3AED;
}
QTextEdit, QPlainTextEdit { padding: 8px; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus { border-color: #8B5CF6; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView {
    background: #171B29;
    border: 1px solid #30364C;
    selection-background-color: #6D28D9;
    padding: 4px;
}
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 18px; height: 18px; }
QCheckBox::indicator:unchecked { background: #0D101A; border: 1px solid #424962; border-radius: 5px; }
QCheckBox::indicator:checked { background: #8B5CF6; border: 1px solid #A78BFA; border-radius: 5px; }
QTableWidget, QTreeWidget, QListWidget {
    background: #0E111B;
    alternate-background-color: #121625;
    border: 1px solid #252A3C;
    border-radius: 10px;
    gridline-color: #252A3C;
    selection-background-color: #37266A;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background: #171B29;
    color: #AEB4C9;
    padding: 8px;
    border: 0;
    border-bottom: 1px solid #30364C;
    font-weight: 650;
}
QTableCornerButton::section { background: #171B29; border: 0; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 3px; }
QScrollBar::handle:vertical { min-height: 28px; background: #343B54; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; margin: 3px; }
QScrollBar::handle:horizontal { min-width: 28px; background: #343B54; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSlider::groove:horizontal { height: 5px; background: #292F45; border-radius: 2px; }
QSlider::handle:horizontal { width: 17px; margin: -6px 0; background: #A78BFA; border-radius: 8px; }
QTabWidget::pane { border: 1px solid #252A3C; border-radius: 10px; top: -1px; }
QTabBar::tab { padding: 10px 16px; color: #9299B2; }
QTabBar::tab:selected { color: #C4B5FD; border-bottom: 2px solid #8B5CF6; }
QToolTip { background: #1A1F30; color: white; border: 1px solid #3A425C; padding: 7px; }
QMenu { background: #171B29; border: 1px solid #30364C; padding: 5px; }
QMenu::item { padding: 8px 24px; border-radius: 5px; }
QMenu::item:selected { background: #6D28D9; }
QProgressBar { background: #1B2031; border: 0; border-radius: 5px; height: 9px; text-align: center; }
QProgressBar::chunk { background: #8B5CF6; border-radius: 5px; }
QGraphicsView { background: #0C0F18; border: 1px solid #252A3C; border-radius: 10px; }
"""
