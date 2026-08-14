import flet as ft
from db.storage import store_csv_in_sqlite, fetch_preview, COLUMNS
from ui.theme import (
    INK, SURFACE, SURFACE_ALT, BRASS, BRASS_DIM, IVORY, SLATE, CLAY, EMERALD,
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, SPACE_XXL,
    PAGE_H_PAD, RADIUS_SM, RADIUS_MD, RADIUS_LG,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, ghost_button, app_card, table_shell, table_header_row, table_data_row,
)

COL_WIDTH = 110
TABLE_WIDTH = COL_WIDTH * len(COLUMNS)


def _format_file_size(size_bytes: int) -> str:
    if not size_bytes or size_bytes < 1024:
        return f"{size_bytes or 0} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def build_upload_view(page: ft.Page):
    # Selected file state ref
    selected_file_ref = {"file": None}

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # ────────────── Step Indicator Controls ──────────────
    step1_num_container = ft.Container(
        content=ft.Text("1", size=11, weight=ft.FontWeight.W_700, color=INK),
        bgcolor=BRASS,
        border_radius=10,
        width=20,
        height=20,
        alignment=ft.Alignment.CENTER,
    )
    step1_label = ft.Text("Select File", size=12, weight=ft.FontWeight.W_600, color=IVORY)

    step1_indicator = ft.Container(
        content=ft.Row([step1_num_container, step1_label], spacing=SPACE_XS, tight=True),
    )

    step2_num_container = ft.Container(
        content=ft.Text("2", size=11, weight=ft.FontWeight.W_700, color=SLATE),
        bgcolor=SURFACE_ALT,
        border_radius=10,
        width=20,
        height=20,
        alignment=ft.Alignment.CENTER,
    )
    step2_label = ft.Text("Confirm & Upload", size=12, weight=ft.FontWeight.W_500, color=SLATE)

    step2_indicator = ft.Container(
        content=ft.Row([step2_num_container, step2_label], spacing=SPACE_XS, tight=True),
    )

    step_divider = ft.Text("→", size=13, color=SLATE)

    step_bar = ft.Container(
        content=ft.Row(
            [step1_indicator, step_divider, step2_indicator],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=SPACE_MD,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=RADIUS_MD,
        padding=ft.Padding(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM),
    )

    def update_step(step_num: int):
        if step_num == 1:
            step1_num_container.bgcolor = BRASS
            step1_num_container.content = ft.Text("1", size=11, weight=ft.FontWeight.W_700, color=INK)
            step1_label.color = IVORY
            step1_label.weight = ft.FontWeight.W_600

            step2_num_container.bgcolor = SURFACE_ALT
            step2_num_container.content = ft.Text("2", size=11, weight=ft.FontWeight.W_700, color=SLATE)
            step2_label.color = SLATE
            step2_label.weight = ft.FontWeight.W_500
        else:
            step1_num_container.bgcolor = EMERALD
            step1_num_container.content = ft.Icon(ft.Icons.CHECK, size=12, color=INK)
            step1_label.color = SLATE
            step1_label.weight = ft.FontWeight.W_500

            step2_num_container.bgcolor = BRASS
            step2_num_container.content = ft.Text("2", size=11, weight=ft.FontWeight.W_700, color=INK)
            step2_label.color = IVORY
            step2_label.weight = ft.FontWeight.W_600

    # ────────────── Confirmation & Preview Components ──────────────
    file_name_text = ft.Text("", size=14, weight=ft.FontWeight.W_700, color=IVORY)
    file_size_text = ft.Text("", size=12, color=SLATE)

    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=24, color=EMERALD)
    status_title = ft.Text("", size=14, weight=ft.FontWeight.W_700, color=IVORY)
    status_sub = ft.Text("", size=12, color=SLATE)

    status_banner = ft.Container(
        content=ft.Row(
            [
                status_icon,
                ft.Column(
                    [status_title, status_sub],
                    spacing=2,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_MD,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1, EMERALD),
        border_radius=RADIUS_MD,
        padding=SPACE_MD,
        visible=False,
    )

    table_header = table_header_row(
        [ft.Container(header_cell_text(c), width=COL_WIDTH) for c in COLUMNS],
    )
    table_header.width = TABLE_WIDTH

    preview_rows = ft.Column(spacing=0, width=TABLE_WIDTH)
    preview_table = table_shell(table_header, preview_rows, TABLE_WIDTH)
    preview_section_label = eyebrow_text("Uploaded Stock Preview")

    # ────────────── Event Handlers ──────────────
    async def on_select_file_click(e):
        files = await file_picker.pick_files(
            dialog_title="Select Stock CSV File",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return

        picked = files[0]
        selected_file_ref["file"] = picked

        # Update file details in confirmation card
        file_name_text.value = picked.name
        file_size_text.value = f"Size: {_format_file_size(picked.size)} · Ready to import"

        # Switch to Confirmation Step
        update_step(2)
        browse_dropzone.visible = False
        confirmation_card.visible = True
        status_banner.visible = False
        preview_section.visible = False
        page.update()

    def on_cancel_selected(e=None):
        selected_file_ref["file"] = None
        update_step(1)
        browse_dropzone.visible = True
        confirmation_card.visible = False
        status_banner.visible = False
        preview_section.visible = False
        page.update()

    async def on_confirm_upload_click(e):
        picked = selected_file_ref["file"]
        if not picked:
            return

        confirm_btn.disabled = True
        status_icon.name = ft.Icons.HOURGLASS_TOP
        status_icon.color = BRASS
        status_title.value = f"Importing {picked.name}..."
        status_sub.value = "Reading data and saving into SQLite database..."
        status_banner.border = ft.Border.all(1, BRASS)
        status_banner.visible = True
        page.update()

        try:
            csv_text = None
            if picked.bytes is not None and len(picked.bytes) > 0:
                try:
                    csv_text = picked.bytes.decode("utf-8-sig")
                except UnicodeDecodeError:
                    csv_text = picked.bytes.decode("latin-1", errors="replace")
            elif picked.path:
                try:
                    with open(picked.path, "r", encoding="utf-8-sig", newline="") as f:
                        csv_text = f.read()
                except UnicodeDecodeError:
                    with open(picked.path, "r", encoding="latin-1", newline="", errors="replace") as f:
                        csv_text = f.read()

            if not csv_text:
                raise ValueError("Could not read file content or file is empty.")

            columns, row_count = store_csv_in_sqlite(csv_text)

            status_icon.name = ft.Icons.CHECK_CIRCLE_OUTLINE
            status_icon.color = EMERALD
            status_title.value = f"Successfully Imported {row_count} Items"
            status_sub.value = f"Saved to database · Columns matched: {', '.join(columns)}"
            status_banner.border = ft.Border.all(1, EMERALD)
            status_banner.visible = True

            confirmation_card.visible = False
            browse_dropzone.visible = False
            show_uploaded_preview(row_count)
            confirm_btn.disabled = False
            page.update()

        except Exception as ex:
            confirm_btn.disabled = False
            status_icon.name = ft.Icons.ERROR_OUTLINE
            status_icon.color = CLAY
            status_title.value = "Import Failed"
            status_sub.value = str(ex)
            status_banner.border = ft.Border.all(1, CLAY)
            status_banner.visible = True
            page.update()

    def show_uploaded_preview(row_count):
        preview_limit = min(row_count, 100)
        rows = fetch_preview(limit=preview_limit)
        preview_rows.controls = [
            table_data_row(
                [ft.Container(data_cell_text(v), width=COL_WIDTH) for v in row],
                index=i,
            )
            for i, row in enumerate(rows)
        ]
        preview_section_label.value = (
            f"UPLOADED STOCK PREVIEW · {row_count} TOTAL ITEMS"
            if row_count <= 100
            else f"UPLOADED STOCK PREVIEW · SHOWING FIRST 100 OF {row_count} ITEMS"
        )
        preview_section.visible = True

    # ────────────── Main Interactive UI Blocks ──────────────
    browse_dropzone = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=38, color=BRASS),
                    bgcolor=BRASS_DIM,
                    border_radius=30,
                    width=60,
                    height=60,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=4),
                heading_text("Choose Stock CSV File", size=16),
                subheading_text("Tap below to browse and select your CSV file"),
                ft.Container(height=8),
                primary_button(
                    "Browse CSV File",
                    on_click=on_select_file_click,
                    icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_SM,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1.5, BRASS_DIM),
        border_radius=RADIUS_LG,
        padding=SPACE_XXL,
        alignment=ft.Alignment.CENTER,
    )

    confirm_btn = primary_button(
        "Confirm & Import Data",
        on_click=on_confirm_upload_click,
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        expand=True,
    )

    confirmation_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=BRASS),
                            ft.Text(
                                "CONFIRMATION REQUIRED",
                                size=11,
                                weight=ft.FontWeight.W_700,
                                color=BRASS,
                                style=ft.TextStyle(letter_spacing=1.2),
                            ),
                        ],
                        spacing=SPACE_SM,
                        tight=True,
                    ),
                    bgcolor=BRASS_DIM,
                    border_radius=RADIUS_SM,
                    padding=ft.Padding(10, 6, 10, 6),
                ),
                ft.Container(height=4),
                heading_text("Ready to upload this file?", size=16),
                subheading_text("Please verify the file details below before importing into SQLite:"),
                ft.Container(height=SPACE_SM),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=24, color=BRASS),
                                bgcolor=BRASS_DIM,
                                border_radius=RADIUS_SM,
                                padding=SPACE_SM,
                            ),
                            ft.Column(
                                [
                                    file_name_text,
                                    file_size_text,
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(".CSV", size=10, weight=ft.FontWeight.W_700, color=BRASS),
                                bgcolor=BRASS_DIM,
                                border_radius=RADIUS_SM,
                                padding=ft.Padding(6, 3, 6, 3),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=SPACE_MD,
                    ),
                    bgcolor=SURFACE_ALT,
                    border=ft.Border.all(1, BRASS_DIM),
                    border_radius=RADIUS_MD,
                    padding=SPACE_MD,
                ),
                ft.Container(height=SPACE_SM),
                confirm_btn,
                ft.Row(
                    [
                        ghost_button("Choose Different File", on_click=on_select_file_click),
                        ghost_button("Cancel", on_click=on_cancel_selected),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=SPACE_MD,
                ),
            ],
            spacing=SPACE_SM,
        ),
        bgcolor=SURFACE,
        border=ft.Border.all(1.5, BRASS),
        border_radius=RADIUS_LG,
        padding=SPACE_XL,
        visible=False,
    )

    upload_another_btn = primary_button(
        "Upload Another CSV",
        on_click=on_cancel_selected,
        icon=ft.Icons.UPLOAD_FILE_OUTLINED,
        expand=True,
    )

    preview_section = ft.Container(
        content=ft.Column(
            [
                preview_section_label,
                ft.Container(height=SPACE_XS),
                preview_table,
                ft.Container(height=SPACE_MD),
                upload_another_btn,
            ],
            spacing=0,
        ),
        visible=False,
    )

    info_card = app_card(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, color=BRASS, size=16),
                ft.Text(
                    f"Required columns: {', '.join(COLUMNS)} (Item No, Tag, Purity, Net Wt, Gross Wt)",
                    size=11.5,
                    color=SLATE,
                    expand=True,
                ),
            ],
            spacing=SPACE_MD,
        ),
        padding=SPACE_LG,
    )

    return ft.Container(
        content=ft.Column(
            [
                eyebrow_text("Inventory Management"),
                ft.Container(height=SPACE_XS),
                step_bar,
                ft.Container(height=SPACE_SM),
                info_card,
                ft.Container(height=SPACE_SM),
                browse_dropzone,
                confirmation_card,
                status_banner,
                ft.Container(height=SPACE_SM),
                preview_section,
                ft.Container(height=SPACE_LG),
            ],
            spacing=SPACE_SM,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=PAGE_H_PAD,
        bgcolor=INK,
        expand=True,
    )