import flet as ft
from db.storage import (
    fetch_preview,
    search_stock,
    COLUMNS,
    fetch_customers,
    get_linked_customers,
    link_customer_to_item,
    unlink_customer_from_item,
    export_ledger_csv,
)
from ui.theme import (
    INK, SURFACE, SURFACE_ALT, BRASS, BRASS_DIM, IVORY, SLATE, CLAY,
    SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, RADIUS_MD, RADIUS_LG,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, icon_action_button, app_text_field,
    table_shell, row_bg, empty_state, snack,
)

COL_WIDTH = 110
CUSTOMERS_COL_WIDTH = 130
ACTION_COL_WIDTH = 56
ROW_END_SPACER = 12
TABLE_WIDTH = COL_WIDTH * len(COLUMNS) + CUSTOMERS_COL_WIDTH + ACTION_COL_WIDTH + ROW_END_SPACER


def build_ledger_view(page: ft.Page):
    table_header = ft.Container(
        content=ft.Row(
            [ft.Container(header_cell_text(c), width=COL_WIDTH) for c in COLUMNS]
            + [ft.Container(header_cell_text("Customers"), width=CUSTOMERS_COL_WIDTH)]
            + [ft.Container(width=ACTION_COL_WIDTH)]
            + [ft.Container(width=ROW_END_SPACER)],
            spacing=0,
        ),
        padding=ft.Padding(SPACE_LG, SPACE_MD, 0, SPACE_MD),
        bgcolor=SURFACE_ALT,
        width=TABLE_WIDTH,
    )

    ledger_rows = ft.Column(spacing=0, width=TABLE_WIDTH)
    table_container = table_shell(table_header, ledger_rows, TABLE_WIDTH)
    table_container.visible = False

    empty_container = empty_state("No stock rows found. Upload a CSV to get started.")
    empty_container.visible = False

    # ---------- export ----------
    export_picker = ft.FilePicker()
    page.services.append(export_picker)

    async def on_export_click(e):
        csv_text = export_ledger_csv()
        try:
            result = await export_picker.save_file(
                dialog_title="Export stock ledger",
                file_name="stock_ledger_export.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=csv_text.encode("utf-8"),
            )
            if not result:
                return  # user cancelled
            snack(page, "Exported stock_ledger_export.csv")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    # ---------- link customers dialog ----------
    link_item_code = {"value": None}
    link_checkboxes_column = ft.Column(spacing=SPACE_SM, scroll=ft.ScrollMode.AUTO, height=260)
    link_dialog_title = heading_text("Link Customers", size=18)
    link_dialog_sub = subheading_text("")

    def close_link_dialog(e=None):
        page.pop_dialog()

    def refresh_current_view():
        query = (search_field.value or "").strip()
        if query:
            render_rows(search_stock(query, limit=100))
        else:
            render_rows(fetch_preview(limit=100))

    def save_links(e):
        item_code = link_item_code["value"]
        if not item_code:
            page.pop_dialog()
            return

        selected_ids = {
            cb.data for cb in link_checkboxes_column.controls
            if isinstance(cb, ft.Checkbox) and cb.value
        }
        currently_linked = {cid for cid, _, _ in get_linked_customers(item_code)}

        for cid in selected_ids - currently_linked:
            link_customer_to_item(item_code, cid)
        for cid in currently_linked - selected_ids:
            unlink_customer_from_item(item_code, cid)

        page.pop_dialog()
        page.update()
        refresh_current_view()
        snack(page, f"Updated links for {item_code}")
        page.update()

    link_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=RADIUS_LG),
        title=ft.Column([link_dialog_title, link_dialog_sub], spacing=4, tight=True),
        content=ft.Container(content=link_checkboxes_column, width=320, padding=ft.Padding(0, SPACE_SM, 0, 0)),
        actions=[
            ft.TextButton(
                content=ft.Text("Cancel", color=SLATE, size=13, weight=ft.FontWeight.W_600),
                on_click=close_link_dialog,
            ),
            primary_button("Save", on_click=save_links),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_link_dialog(item_code):
        link_item_code["value"] = item_code
        link_dialog_sub.value = f"Item: {item_code}"

        all_customers = fetch_customers(limit=200)
        linked_ids = {cid for cid, _, _ in get_linked_customers(item_code)}

        if not all_customers:
            link_checkboxes_column.controls = [
                ft.Text("No customers yet — add one in the Customers tab first.", size=12, color=SLATE)
            ]
        else:
            link_checkboxes_column.controls = [
                ft.Checkbox(
                    label=f"{name}  ({code})",
                    value=(cid in linked_ids),
                    data=cid,
                    label_style=ft.TextStyle(color=IVORY, size=13),
                    active_color=BRASS,
                )
                for cid, code, name, number in all_customers
            ]
        page.show_dialog(link_dialog)

    # ---------- table rendering ----------
    def render_rows(rows):
        if not rows:
            table_container.visible = False
            empty_container.visible = True
            page.update()
            return

        row_controls = []
        for i, row in enumerate(rows):
            item_code = row[0]
            linked = get_linked_customers(item_code)
            if not linked:
                linked_display = "—"
            elif len(linked) == 1:
                linked_display = linked[0][2]
            else:
                linked_display = f"{linked[0][2]} +{len(linked) - 1}"

            row_controls.append(
                ft.Container(
                    content=ft.Row(
                        [ft.Container(data_cell_text(v), width=COL_WIDTH) for v in row]
                        + [ft.Container(
                            data_cell_text(linked_display, muted=(linked_display == "—")),
                            width=CUSTOMERS_COL_WIDTH,
                        )]
                        + [
                            ft.Container(
                                content=icon_action_button(
                                    ft.Icons.LINK, BRASS, "Link customers",
                                    lambda e, ic=item_code: open_link_dialog(ic),
                                ),
                                width=ACTION_COL_WIDTH,
                                alignment=ft.Alignment.CENTER,
                            )
                        ]
                        + [ft.Container(width=ROW_END_SPACER)],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(SPACE_LG, SPACE_SM, 0, SPACE_SM),
                    bgcolor=row_bg(i),
                )
            )
        ledger_rows.controls = row_controls
        table_container.visible = True
        empty_container.visible = False
        page.update()

    def load_all():
        render_rows(fetch_preview(limit=100))

    def on_search_change(e):
        query = (search_field.value or "").strip()
        if not query:
            load_all()
            return
        render_rows(search_stock(query, limit=100))

    search_field = app_text_field(
        label=None, hint="Search by item code or tag",
        on_change=on_search_change, prefix_icon=ft.Icons.SEARCH,
    )

    export_btn = primary_button(
        "Export CSV", on_click=on_export_click, icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, expand=True,
    )

    load_all()  # show existing stock data immediately

    return ft.Container(
        content=ft.Column(
            [
                search_field,
                ft.Container(height=SPACE_SM),
                eyebrow_text("Ledger · All Records"),
                ft.Container(height=SPACE_SM),
                table_container,
                empty_container,
                ft.Container(height=SPACE_SM),
                export_btn,
            ],
            spacing=SPACE_LG,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=SPACE_XL,
        bgcolor=INK,
        expand=True,
    )