import flet as ft
from db.storage import (
    fetch_preview,
    search_stock,
    COLUMNS,
    fetch_customers,
    get_linked_customers,
    link_customer_to_item,
    unlink_customer_from_item,
)

INK = "#14161C"
SURFACE = "#1E212B"
SURFACE_ALT = "#242836"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"

COL_WIDTH = 110
CUSTOMERS_COL_WIDTH = 130
ACTION_COL_WIDTH = 50
TABLE_WIDTH = COL_WIDTH * len(COLUMNS) + CUSTOMERS_COL_WIDTH + ACTION_COL_WIDTH


def build_ledger_view(page: ft.Page):
    def header_cell(label):
        return ft.Text(
            label.replace("_", " ").upper(), size=10, weight=ft.FontWeight.W_600,
            color=BRASS, style=ft.TextStyle(letter_spacing=1),
        )

    def data_cell(value):
        return ft.Text(str(value), size=12, color=IVORY)

    table_header = ft.Container(
        content=ft.Row(
            [ft.Container(header_cell(c), width=COL_WIDTH) for c in COLUMNS]
            + [ft.Container(header_cell("Customers"), width=CUSTOMERS_COL_WIDTH)]
            + [ft.Container(header_cell(""), width=ACTION_COL_WIDTH)],
            spacing=0,
        ),
        padding=ft.Padding(14, 10, 14, 10),
        bgcolor=SURFACE_ALT,
        width=TABLE_WIDTH,
    )

    ledger_rows = ft.Column(spacing=0, width=TABLE_WIDTH)

    table_scroll = ft.Row(
        controls=[ft.Column([table_header, ledger_rows], spacing=0, width=TABLE_WIDTH)],
        scroll=ft.ScrollMode.ALWAYS,
    )

    table_container = ft.Container(
        content=table_scroll,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        width=340,
        visible=False,
    )

    empty_msg = ft.Text("No stock rows found.", size=12, color=SLATE, visible=False)

    def show_snack(message):
        page.show_dialog(
            ft.SnackBar(content=ft.Text(message, color=IVORY), bgcolor=SURFACE_ALT)
        )

    # ---------- link customers dialog ----------
    link_item_code = {"value": None}
    link_checkboxes_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=260)
    link_dialog_title = ft.Text(
        "Link Customers", size=18, color=IVORY, weight=ft.FontWeight.W_600,
        style=ft.TextStyle(font_family="Playfair"),
    )
    link_dialog_sub = ft.Text("", size=12, color=SLATE)

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
        show_snack(f"Updated links for {item_code}")
        page.update()

    link_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        title=ft.Column([link_dialog_title, link_dialog_sub], spacing=4, tight=True),
        content=ft.Container(content=link_checkboxes_column, width=320),
        actions=[
            ft.TextButton("Cancel", on_click=close_link_dialog, style=ft.ButtonStyle(color=SLATE)),
            ft.ElevatedButton(
                "Save", on_click=save_links,
                style=ft.ButtonStyle(
                    bgcolor=BRASS, color=INK,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
                ),
            ),
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
                )
                for cid, code, name, number in all_customers
            ]
        page.show_dialog(link_dialog)

    # ---------- table rendering ----------
    def render_rows(rows):
        if not rows:
            table_container.visible = False
            empty_msg.visible = True
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
                        [ft.Container(data_cell(v), width=COL_WIDTH) for v in row]
                        + [ft.Container(data_cell(linked_display), width=CUSTOMERS_COL_WIDTH)]
                        + [
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.LINK,
                                    icon_color=BRASS,
                                    icon_size=16,
                                    tooltip="Link customers",
                                    on_click=lambda e, ic=item_code: open_link_dialog(ic),
                                ),
                                width=ACTION_COL_WIDTH,
                            )
                        ],
                        spacing=0,
                    ),
                    padding=ft.Padding(14, 6, 14, 6),
                    bgcolor=SURFACE if i % 2 == 0 else SURFACE_ALT,
                )
            )
        ledger_rows.controls = row_controls
        table_container.visible = True
        empty_msg.visible = False
        page.update()

    def load_all():
        render_rows(fetch_preview(limit=100))

    def on_search_change(e):
        query = (search_field.value or "").strip()
        if not query:
            load_all()
            return
        render_rows(search_stock(query, limit=100))

    search_field = ft.TextField(
        hint_text="Search by item_code or item_tag",
        prefix_icon=ft.Icons.SEARCH,
        border_color=BRASS_DIM,
        focused_border_color=BRASS,
        text_style=ft.TextStyle(color=IVORY),
        hint_style=ft.TextStyle(color=SLATE),
        cursor_color=BRASS,
        bgcolor=SURFACE,
        border_radius=8,
        on_change=on_search_change,
    )

    header_row = ft.Text(
        "LEDGER · ALL RECORDS", size=11, weight=ft.FontWeight.W_600,
        color=SLATE, style=ft.TextStyle(letter_spacing=1),
    )

    load_all()  # show existing stock data immediately

    return ft.Container(
        content=ft.Column(
            [search_field, ft.Container(height=6), header_row, ft.Container(height=6),
             table_container, empty_msg],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=20,
        bgcolor=INK,
        expand=True,
    )