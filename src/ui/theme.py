import flet as ft

# ---------- Color tokens ----------
INK = "#14161C"
SURFACE = "#1E212B"
SURFACE_ALT = "#242836"
SURFACE_RAISED = "#2A2F3F"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
BRASS_MUTED = "#8A744A"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"
CLAY = "#E2685C"
EMERALD = "#3FA787"

FONT_DISPLAY = "Playfair"
FONT_BODY = "Manrope"

# ---------- Spacing scale (4px base grid) ----------
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
SPACE_XXL = 24
SPACE_XXXL = 32

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

# Consistent horizontal padding used for page-level and row-level alignment
PAGE_H_PAD = SPACE_XL
ROW_H_PAD = SPACE_LG


# ---------- Typography helpers ----------
def eyebrow_text(label: str) -> ft.Text:
    return ft.Text(
        label.upper(),
        size=11,
        weight=ft.FontWeight.W_600,
        color=SLATE,
        style=ft.TextStyle(letter_spacing=1.2),
    )


def heading_text(label: str, size: int = 18) -> ft.Text:
    return ft.Text(
        label,
        size=size,
        weight=ft.FontWeight.W_600,
        color=IVORY,
        style=ft.TextStyle(font_family=FONT_DISPLAY),
    )


def subheading_text(label: str) -> ft.Text:
    return ft.Text(label, size=12, color=SLATE)


def header_cell_text(label: str) -> ft.Text:
    return ft.Text(
        label.replace("_", " ").upper(),
        size=10,
        weight=ft.FontWeight.W_700,
        color=BRASS,
        style=ft.TextStyle(letter_spacing=1),
    )


def data_cell_text(value, muted: bool = False) -> ft.Text:
    return ft.Text(
        str(value) if value not in (None, "") else "—",
        size=12.5,
        color=SLATE if muted else IVORY,
    )


# ---------- Buttons ----------
def primary_button(label: str, on_click=None, icon=None, expand=False) -> ft.Button:
    return ft.Button(
        content=ft.Row(
            [c for c in [
                ft.Icon(icon, size=16, color=INK) if icon else None,
                ft.Text(
                    label.upper(), size=12.5, weight=ft.FontWeight.W_700,
                    color=INK, style=ft.TextStyle(letter_spacing=0.8),
                ),
            ] if c is not None],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=BRASS,
            shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
            padding=ft.Padding(20, 14, 20, 14),
            elevation=0,
        ),
        height=48,
        expand=expand,
    )


def danger_button(label: str, on_click=None) -> ft.Button:
    return ft.Button(
        content=ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=IVORY),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=CLAY,
            shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
            padding=ft.Padding(18, 14, 18, 14),
            elevation=0,
        ),
    )


def ghost_button(label: str, on_click=None) -> ft.TextButton:
    return ft.TextButton(
        content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=SLATE),
        on_click=on_click,
    )


def icon_action_button(icon, color, tooltip, on_click, size=32) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        icon_color=color,
        icon_size=15,
        tooltip=tooltip,
        on_click=on_click,
        width=size,
        height=size,
        mouse_cursor=ft.MouseCursor.CLICK,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            padding=ft.Padding(0, 0, 0, 0),
            overlay_color=ft.Colors.with_opacity(0.08, IVORY),
        ),
    )


def submit_arrow_button(on_click, tooltip="Assign") -> ft.IconButton:
    return ft.IconButton(
        icon=ft.Icons.ARROW_FORWARD_ROUNDED,
        icon_color=INK,
        icon_size=20,
        tooltip=tooltip,
        on_click=on_click,
        width=44,
        height=44,
        mouse_cursor=ft.MouseCursor.CLICK,
        style=ft.ButtonStyle(
            bgcolor=BRASS,
            shape=ft.CircleBorder(),
            padding=ft.Padding(0, 0, 0, 0),
            overlay_color=ft.Colors.with_opacity(0.15, INK),
        ),
    )


# ---------- Inputs ----------
def app_text_field(label, hint, keyboard=None, on_change=None, prefix_icon=None) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        keyboard_type=keyboard,
        prefix_icon=prefix_icon,
        on_change=on_change,
        border_color=BRASS_DIM,
        focused_border_color=BRASS,
        label_style=ft.TextStyle(color=SLATE, size=12),
        hint_style=ft.TextStyle(color=SLATE),
        text_style=ft.TextStyle(color=IVORY, size=13),
        cursor_color=BRASS,
        bgcolor=SURFACE,
        border_radius=RADIUS_MD,
        content_padding=ft.Padding(ROW_H_PAD, 14, ROW_H_PAD, 14),
    )


# ---------- Layout primitives ----------
def app_card(content, padding=SPACE_XXL) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=RADIUS_LG,
        padding=padding,
    )


def table_shell(header: ft.Container, rows_column: ft.Column, width: int) -> ft.Container:
    """Scrollable table wrapper. Uses full available width, scrolls horizontally
    only when needed (content wider than viewport)."""
    scroll = ft.Row(
        controls=[ft.Column([header, rows_column], spacing=0, width=width)],
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    return ft.Container(
        content=scroll,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=RADIUS_LG,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def table_header_row(cells, pad_left=ROW_H_PAD, pad_right=ROW_H_PAD):
    """Standardised table header with symmetric padding."""
    return ft.Container(
        content=ft.Row(cells, spacing=0),
        padding=ft.Padding(pad_left, SPACE_MD, pad_right, SPACE_MD),
        bgcolor=SURFACE_ALT,
    )


def table_data_row(cells, index, pad_left=ROW_H_PAD, pad_right=ROW_H_PAD):
    """Standardised data row with symmetric padding and zebra striping."""
    return ft.Container(
        content=ft.Row(
            cells,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(pad_left, SPACE_SM, pad_right, SPACE_SM),
        bgcolor=row_bg(index),
    )


def row_bg(index: int) -> str:
    return SURFACE if index % 2 == 0 else SURFACE_ALT


def empty_state(message: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.INBOX_OUTLINED, color=BRASS_MUTED, size=32),
                ft.Text(message, size=12.5, color=SLATE, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_MD,
        ),
        padding=ft.Padding(SPACE_XL, SPACE_XXXL, SPACE_XL, SPACE_XXXL),
        alignment=ft.Alignment.CENTER,
    )


def section_divider() -> ft.Container:
    """Subtle horizontal rule for separating content sections."""
    return ft.Container(
        height=1,
        bgcolor=BRASS_DIM,
        margin=ft.Margin(0, SPACE_SM, 0, SPACE_SM),
    )


def snack(page: ft.Page, message: str, accent: str = BRASS):
    page.show_dialog(
        ft.SnackBar(
            content=ft.Row(
                [
                    ft.Container(width=3, height=18, bgcolor=accent, border_radius=2),
                    ft.Text(message, color=IVORY, size=13, weight=ft.FontWeight.W_500),
                ],
                spacing=SPACE_MD,
            ),
            bgcolor=SURFACE_RAISED,
        )
    )