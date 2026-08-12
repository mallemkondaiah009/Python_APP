from db.storage import (
    fetch_by_item_codes, COLUMNS, fetch_customers,
    save_customer_assignments, update_item_assignments, fetch_assignments, clear_assignments,
)
from ui.theme import (
    INK, SURFACE, BRASS, BRASS_DIM, IVORY, SLATE, CLAY,
    SPACE_SM, SPACE_LG, RADIUS_MD, RADIUS_LG,
    ROW_H_PAD, PAGE_H_PAD,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, icon_action_button, submit_arrow_button, ghost_button, app_text_field,
    table_shell, table_header_row, table_data_row, empty_state, snack,
)

import flet as ft

COL_WIDTH = 110
CUSTOMERS_COL_WIDTH = 130
ACTION_COL_WIDTH = 56
TABLE_WIDTH = COL_WIDTH * len(COLUMNS) + CUSTOMERS_COL_WIDTH + ACTION_COL_WIDTH


def build_ledger_view(page: ft.Page):
    # ---------- database-backed assignment state ----------
    session_links = fetch_assignments()  # item_code -> set(customer_id) loaded from DB

    customer_lookup = {}
    dropdown_container = ft.Container(expand=1)

    def refresh_customer_list():
        """Reload customers from DB and update dropdown + lookup."""
        customer_lookup.clear()
        options = []
        for cid, code, name, number in fetch_customers(limit=200):
            customer_lookup[cid] = (code, name)
            options.append(ft.DropdownOption(key=str(cid), text=name))

        dropdown_container.content = ft.Dropdown(
            hint_text="Customer",
            options=options,
            border_color=BRASS_DIM,
            focused_border_color=BRASS,
            color=IVORY,
            bgcolor=SURFACE,
            border_radius=RADIUS_MD,
            text_size=13,
            content_padding=ft.Padding(ROW_H_PAD, 14, ROW_H_PAD, 14),
            expand=True,
        )

    refresh_customer_list()  # initial load

    # ---------- table ----------
    table_header = table_header_row(
        [ft.Container(header_cell_text(c), width=COL_WIDTH) for c in COLUMNS]
        + [ft.Container(header_cell_text("Customers"), width=CUSTOMERS_COL_WIDTH)]
        + [ft.Container(width=ACTION_COL_WIDTH)],
    )
    table_header.width = TABLE_WIDTH

    ledger_rows = ft.Column(spacing=0, width=TABLE_WIDTH)
    table_container = table_shell(table_header, ledger_rows, TABLE_WIDTH)
    table_container.visible = False

    empty_container = empty_state("Assign stock to a customer below to see it here.")
    empty_container.visible = True

    current_item_codes = {"value": list(session_links.keys())}  # loaded from DB

    section_label = eyebrow_text("Assigned Items")
    clear_btn = ghost_button("Clear", on_click=lambda e: clear_assigned())
    clear_btn.visible = bool(current_item_codes["value"])

    section_header_row = ft.Row(
        [section_label, ft.Container(expand=True), clear_btn],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def clear_assigned():
        clear_assignments()
        session_links.clear()
        current_item_codes["value"] = []
        section_label.value = "ASSIGNED ITEMS"
        clear_btn.visible = False
        export_btn.disabled = True
        render_rows([])
        page.update()

    # ---------- assign by item code ----------
    codes_field = app_text_field(label=None, hint="item code(s), e.g. AB123, AB124")
    codes_field.expand = 2

    def render_assigned(new_item_codes):
        combined = current_item_codes["value"] + [
            c for c in new_item_codes if c not in current_item_codes["value"]
        ]
        current_item_codes["value"] = combined
        clear_btn.visible = True
        render_rows(fetch_by_item_codes(combined))

    def on_assign_click(e):
        dropdown_ctrl = dropdown_container.content
        customer_key = dropdown_ctrl.value if dropdown_ctrl else None
        codes_text = (codes_field.value or "").strip()

        if not customer_key:
            snack(page, "Select a customer first", accent=CLAY)
            page.update()
            return
        if not codes_text:
            snack(page, "Enter at least one item code", accent=CLAY)
            page.update()
            return

        customer_id = int(customer_key)
        raw_codes = [c.strip() for c in codes_text.replace("\n", ",").split(",") if c.strip()]

        matched_rows = fetch_by_item_codes(raw_codes)
        matched_codes = [row[0] for row in matched_rows]
        not_found = [c for c in raw_codes if c not in matched_codes]

        already_added = [c for c in matched_codes if customer_id in session_links.get(c, set())]
        new_codes = [c for c in matched_codes if customer_id not in session_links.get(c, set())]

        if not new_codes and already_added:
            snack(page, "Item already added", accent=CLAY)
            page.update()
            return

        for code in new_codes:
            session_links.setdefault(code, set()).add(customer_id)

        if new_codes:
            save_customer_assignments(customer_id, new_codes)
            render_assigned(new_codes)
            section_label.value = f"ASSIGNED ITEMS · {len(current_item_codes['value'])} total"
            export_btn.disabled = False
            codes_field.value = ""

        if new_codes and not not_found and not already_added:
            snack(page, f"Assigned {len(new_codes)} item(s)")
        elif new_codes and already_added:
            snack(page, f"Assigned {len(new_codes)} item(s); Item already added", accent=CLAY)
        elif new_codes and not_found:
            snack(page, f"Assigned {len(new_codes)}; not found: {', '.join(not_found)}", accent=CLAY)
        elif not_found:
            snack(page, f"No matching item codes found: {', '.join(not_found)}", accent=CLAY)
        page.update()

    assign_row = ft.Row(
        [
            dropdown_container,
            codes_field,
            submit_arrow_button(on_click=on_assign_click, tooltip="Assign to customer"),
        ],
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ---------- export (built entirely from session_links, no DB join) ----------
    export_picker = ft.FilePicker()
    page.services.append(export_picker)

    def build_export_csv():
        import csv
        import io

        rows = fetch_by_item_codes(current_item_codes["value"])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(COLUMNS + ["linked_customers"])
        for row in rows:
            item_code = row[0]
            ids = session_links.get(item_code, set())
            names = [customer_lookup[cid][1] for cid in ids if cid in customer_lookup]
            writer.writerow(list(row) + [", ".join(names)])
        return output.getvalue()

    async def on_export_click(e):
        if not current_item_codes["value"]:
            return

        csv_text = build_export_csv()
        try:
            result = await export_picker.save_file(
                dialog_title="Export assigned stock",
                file_name="assigned_stock_export.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=csv_text.encode("utf-8"),
            )
            if not result:
                return
            snack(page, "Exported assigned_stock_export.csv")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    export_btn = primary_button("Export CSV", on_click=on_export_click, icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, expand=True)
    export_btn.disabled = not bool(current_item_codes["value"])

    # ---------- per-row link dialog ----------
    link_item_code = {"value": None}
    link_checkboxes_column = ft.Column(spacing=SPACE_SM, scroll=ft.ScrollMode.AUTO, height=260)
    link_dialog_title = heading_text("Link Customers", size=18)
    link_dialog_sub = subheading_text("")

    def close_link_dialog(e=None):
        page.pop_dialog()

    def save_links(e):
        item_code = link_item_code["value"]
        if not item_code:
            page.pop_dialog()
            return

        selected_ids = {
            cb.data for cb in link_checkboxes_column.controls
            if isinstance(cb, ft.Checkbox) and cb.value
        }
        if selected_ids:
            session_links[item_code] = selected_ids
        elif item_code in session_links:
            del session_links[item_code]

        update_item_assignments(item_code, selected_ids)

        page.pop_dialog()
        page.update()
        render_rows(fetch_by_item_codes(current_item_codes["value"]))
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

        linked_ids = session_links.get(item_code, set())

        if not customer_lookup:
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
                for cid, (code, name) in customer_lookup.items()
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
            linked_ids = session_links.get(item_code, set())
            names = [customer_lookup[cid][1] for cid in linked_ids if cid in customer_lookup]
            if not names:
                linked_display = "—"
            elif len(names) == 1:
                linked_display = names[0]
            else:
                linked_display = f"{names[0]} +{len(names) - 1}"

            row_controls.append(
                table_data_row(
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
                    ],
                    index=i,
                )
            )
        ledger_rows.controls = row_controls
        table_container.visible = True
        empty_container.visible = False
        page.update()

    view = ft.Container(
        content=ft.Column(
            [
                eyebrow_text("Assign Stock To Customer"),
                ft.Container(height=SPACE_SM),
                assign_row,
                ft.Container(height=SPACE_LG),
                section_header_row,
                ft.Container(height=SPACE_SM),
                table_container,
                empty_container,
                ft.Container(height=SPACE_SM),
                export_btn,
            ],
            spacing=SPACE_SM,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=PAGE_H_PAD,
        bgcolor=INK,
        expand=True,
    )

    # Initial load of stored assignments from DB
    if current_item_codes["value"]:
        section_label.value = f"ASSIGNED ITEMS · {len(current_item_codes['value'])} total"
        render_rows(fetch_by_item_codes(current_item_codes["value"]))

    def refresh_and_render():
        refresh_customer_list()
        if current_item_codes["value"]:
            render_rows(fetch_by_item_codes(current_item_codes["value"]))

    # Attach refresh hook so main.py can call it on tab switch
    view.refresh_customers = refresh_and_render
    return view