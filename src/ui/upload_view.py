import flet as ft
from db.storage import store_csv_in_sqlite, fetch_preview, COLUMNS
from ui.theme import (
    INK, BRASS, SLATE, CLAY, EMERALD,
    SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XXL,
    PAGE_H_PAD,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, app_card, table_shell, table_header_row, table_data_row,
)

COL_WIDTH = 110
TABLE_WIDTH = COL_WIDTH * len(COLUMNS)


def build_upload_view(page: ft.Page):
    status_icon = ft.Icon(ft.Icons.DIAMOND_OUTLINED, size=32, color=BRASS)
    status_title = heading_text("Upload stock CSV", size=16)
    status_sub = subheading_text("Select a CSV to add it to the ledger")

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def set_status(icon, color, title, sub):
        status_icon.name = icon
        status_icon.color = color
        status_title.value = title
        status_sub.value = sub

    # --- preview table (shown after a successful upload) ---
    table_header = table_header_row(
        [ft.Container(header_cell_text(c), width=COL_WIDTH) for c in COLUMNS],
    )
    table_header.width = TABLE_WIDTH

    preview_rows = ft.Column(spacing=0, width=TABLE_WIDTH)
    preview_table = table_shell(table_header, preview_rows, TABLE_WIDTH)

    preview_section = ft.Container(
        content=ft.Column(
            [eyebrow_text("Uploaded · This File"), ft.Container(height=SPACE_SM), preview_table],
            spacing=0,
        ),
        visible=False,
    )

    def show_uploaded_preview(row_count):
        rows = fetch_preview(limit=row_count)
        preview_rows.controls = [
            table_data_row(
                [ft.Container(data_cell_text(v), width=COL_WIDTH) for v in row],
                index=i,
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

    info_card = app_card(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, color=BRASS, size=16),
                ft.Text(
                    f"Required columns: {', '.join(COLUMNS)}",
                    size=11.5, color=SLATE, expand=True,
                ),
            ],
            spacing=SPACE_MD,
        ),
        padding=SPACE_LG,
    )

    status_card = app_card(
        content=ft.Column(
            [status_icon, status_title, status_sub],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_SM,
        ),
        padding=SPACE_XXL,
    )
    status_card.alignment = ft.Alignment.CENTER

    upload_btn = primary_button(
        "Upload CSV", on_click=on_upload_click, icon=ft.Icons.UPLOAD_FILE_OUTLINED, expand=True,
    )

    return ft.Container(
        content=ft.Column(
            [
                info_card,
                status_card,
                upload_btn,
                ft.Container(height=SPACE_SM),
                preview_section,
            ],
            spacing=SPACE_LG,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=PAGE_H_PAD,
        bgcolor=INK,
        expand=True,
    )