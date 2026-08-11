import flet as ft
from db.storage import store_csv_in_sqlite, fetch_preview, COLUMNS

INK = "#14161C"
SURFACE = "#1E212B"
SURFACE_ALT = "#242836"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"
EMERALD = "#3FA787"
CLAY = "#E2685C"

COL_WIDTH = 110
TABLE_WIDTH = COL_WIDTH * len(COLUMNS)


def build_upload_view(page: ft.Page):
    status_icon = ft.Icon(ft.Icons.DIAMOND_OUTLINED, size=34, color=BRASS)
    status_title = ft.Text(
        "Upload stock CSV", size=16, weight=ft.FontWeight.W_600, color=IVORY,
        style=ft.TextStyle(font_family="Playfair"),
    )
    status_sub = ft.Text("Select a CSV to add it to the ledger", size=12, color=SLATE)

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def set_status(icon, color, title, sub):
        status_icon.name = icon
        status_icon.color = color
        status_title.value = title
        status_sub.value = sub

    # --- preview table (shown after a successful upload) ---
    def header_cell(label):
        return ft.Text(
            label.replace("_", " ").upper(), size=10, weight=ft.FontWeight.W_600,
            color=BRASS, style=ft.TextStyle(letter_spacing=1),
        )

    def data_cell(value):
        return ft.Text(str(value), size=12, color=IVORY)

    table_header = ft.Container(
        content=ft.Row([ft.Container(header_cell(c), width=COL_WIDTH) for c in COLUMNS], spacing=0),
        padding=ft.Padding(14, 10, 14, 10),
        bgcolor=SURFACE_ALT,
        width=TABLE_WIDTH,
    )

    preview_rows = ft.Column(spacing=0, width=TABLE_WIDTH)

    table_scroll = ft.Row(
        controls=[ft.Column([table_header, preview_rows], spacing=0, width=TABLE_WIDTH)],
        scroll=ft.ScrollMode.ALWAYS,
    )

    preview_label = ft.Text(
        "UPLOADED · THIS FILE", size=11, weight=ft.FontWeight.W_600,
        color=SLATE, style=ft.TextStyle(letter_spacing=1),
    )

    preview_section = ft.Container(
        content=ft.Column(
            [
                preview_label,
                ft.Container(height=10),
                ft.Container(
                    content=table_scroll,
                    bgcolor=SURFACE,
                    border=ft.Border.all(1, BRASS_DIM),
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    width=340,
                ),
            ],
            spacing=0,
        ),
        visible=False,
    )

    def show_uploaded_preview(row_count):
        rows = fetch_preview(limit=row_count)
        preview_rows.controls = [
            ft.Container(
                content=ft.Row([ft.Container(data_cell(v), width=COL_WIDTH) for v in row], spacing=0),
                padding=ft.Padding(14, 10, 14, 10),
                bgcolor=SURFACE if i % 2 == 0 else SURFACE_ALT,
            )
            for i, row in enumerate(rows)
        ]
        preview_section.visible = True

    async def on_upload_click(e):
        files = await file_picker.pick_files(allow_multiple=False, allowed_extensions=["csv"])
        if not files:
            return

        picked = files[0]
        set_status(ft.Icons.HOURGLASS_TOP, BRASS, f"Reading {picked.name}", "Please wait")
        preview_section.visible = False
        page.update()

        try:
            with open(picked.path, "r", encoding="utf-8-sig", newline="") as f:
                csv_text = f.read()

            columns, row_count = store_csv_in_sqlite(csv_text)
            set_status(
                ft.Icons.CHECK_CIRCLE_OUTLINE, EMERALD,
                f"{row_count} rows added", f"Saved · {', '.join(columns)}",
            )
            show_uploaded_preview(row_count)
            page.update()

        except Exception as ex:
            set_status(ft.Icons.ERROR_OUTLINE, CLAY, "Upload failed", str(ex))
            page.update()

    info_card = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, color=BRASS, size=16),
                ft.Text(
                    f"Required columns: {', '.join(COLUMNS)}",
                    size=11.5, color=SLATE, expand=True,
                ),
            ],
            spacing=10,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        padding=14,
        border_radius=8,
    )

    status_card = ft.Container(
        content=ft.Column(
            [status_icon, status_title, status_sub],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=10,
        padding=36,
        alignment=ft.Alignment.CENTER,
    )

    # --- properly centered button content (icon + label as one aligned unit) ---
    upload_btn = ft.ElevatedButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED, size=18, color=INK),
                ft.Text(
                    "UPLOAD CSV",
                    weight=ft.FontWeight.W_600,
                    size=13,
                    color=INK,
                    style=ft.TextStyle(letter_spacing=1),
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        on_click=on_upload_click,
        style=ft.ButtonStyle(
            bgcolor=BRASS,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(0, 18, 0, 18),
        ),
        height=50,
        width=float("inf"),
    )

    return ft.Container(
        content=ft.Column(
            [
                info_card,
                status_card,
                upload_btn,
                ft.Container(height=6),
                preview_section,
            ],
            spacing=18,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=20,
        bgcolor=INK,
        expand=True,
    )