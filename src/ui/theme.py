import flet as ft

# ---------- Color tokens ----------
INK = "#14161C"            # app background
SURFACE = "#1E212B"        # card / row background
SURFACE_ALT = "#242836"    # alternating row / header background
SURFACE_RAISED = "#2A2F3F" # hover / pressed surfaces
BRASS = "#C6A15B"          # primary accent
BRASS_DIM = "#3A3626"      # borders, dividers on dark surfaces
BRASS_MUTED = "#8A744A"    # secondary/disabled brass text
IVORY = "#F5F1E8"          # primary text on dark
SLATE = "#8B90A0"          # secondary/muted text
CLAY = "#E2685C"           # destructive / error accent
EMERALD = "#3FA787"        # success accent

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
RADIUS_MD = 8
RADIUS_LG = 12


# ---------- Typography helpers ----------
def eyebrow_text(label: str) -> ft.Text:
    """Small uppercase section label, e.g. 'LEDGER · ALL RECORDS'."""
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
        weight=ft.FontWeight.W_600,
        color=BRASS,
        style=ft.TextStyle(letter_spacing=1),
    )


def data_cell_text(value, muted: bool = False) -> ft.Text:
    return ft.Text(
        str(value) if value not in (None, "") else "—",
        size=12,
        color=SLATE if muted else IVORY,
    )


# ---------- Buttons ----------
def primary_button(label: str, on_click=None, icon=None, expand=False) -> ft.Button:
    return ft.Button(
        content=ft.Row(
            [c for c in [
                ft.Icon(icon, size=16, color=INK) if icon else None,
                ft.Text(
                    label.upper(), size=13, weight=ft.FontWeight.W_600,
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
            padding=ft.Padding(20, 16, 20, 16),
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
        content=ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=SLATE),
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
        text_style=ft.TextStyle(color=IVORY),
        cursor_color=BRASS,
        bgcolor=SURFACE,
        border_radius=RADIUS_MD,
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
    scroll = ft.Row(
        controls=[ft.Column([header, rows_column], spacing=0, width=width)],
        scroll=ft.ScrollMode.ALWAYS,
    )
    return ft.Container(
        content=scroll,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=RADIUS_LG,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        width=340,
    )


def row_bg(index: int) -> str:
    return SURFACE if index % 2 == 0 else SURFACE_ALT


def empty_state(message: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.INBOX_OUTLINED, color=BRASS_DIM, size=28),
                ft.Text(message, size=12, color=SLATE, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_SM,
        ),
        padding=SPACE_XXXL,
        alignment=ft.Alignment.CENTER,
    )


def snack(page: ft.Page, message: str, accent: str = BRASS):
    page.show_dialog(
        ft.SnackBar(
            content=ft.Row(
                [
                    ft.Container(width=4, height=18, bgcolor=accent, border_radius=2),
                    ft.Text(message, color=IVORY, size=13),
                ],
                spacing=10,
            ),
            bgcolor=SURFACE_ALT,
        )
    )