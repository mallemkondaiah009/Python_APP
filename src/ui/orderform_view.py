from db.storage import (
    fetch_by_item_codes, COLUMNS, fetch_customers,
    save_customer_assignments, update_item_assignments, fetch_assignments, clear_assignments,
    fetch_customer_totals_summary, fetch_customer_purity_breakdown,
)
from ui.theme import (
    INK, SURFACE, BRASS, BRASS_DIM, IVORY, SLATE, CLAY, EMERALD, SURFACE_ALT,
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, RADIUS_SM, RADIUS_MD, RADIUS_LG,
    ROW_H_PAD, PAGE_H_PAD,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, icon_action_button, submit_arrow_button, ghost_button, app_text_field,
    app_card, table_shell, table_header_row, table_data_row, empty_state, snack,
)

import flet as ft

COL_WIDTH = 110
CUSTOMERS_COL_WIDTH = 130
ACTION_COL_WIDTH = 56
TABLE_WIDTH = COL_WIDTH * len(COLUMNS) + CUSTOMERS_COL_WIDTH + ACTION_COL_WIDTH


def build_orderform_view(page: ft.Page):
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


    # ---------- assign by item code / bluetooth barcode scanner ----------
    codes_field = app_text_field(label=None, hint="Scan barcode or type item code (e.g. RG-101)")
    codes_field.expand = 2

    def render_assigned(new_item_keys):
        combined = current_item_codes["value"] + [
            k for k in new_item_keys if k not in current_item_codes["value"]
        ]
        current_item_codes["value"] = combined
        clear_btn.visible = True
        render_rows(fetch_by_item_codes(combined))

    async def on_assign_click(e):
        dropdown_ctrl = dropdown_container.content
        customer_key = dropdown_ctrl.value if dropdown_ctrl else None
        codes_text = (codes_field.value or "").strip()

        if not customer_key:
            snack(page, "Select a customer first", accent=CLAY)
            page.update()
            return
        if not codes_text:
            snack(page, "Enter at least one item (e.g. RG-101)", accent=CLAY)
            page.update()
            return

        customer_id = int(customer_key)
        raw_codes = [c.strip() for c in codes_text.replace("\n", ",").split(",") if c.strip()]

        matched_rows = fetch_by_item_codes(raw_codes)
        matched_keys = [f"{r[0]}-{r[1]}" for r in matched_rows]

        already_added = [r for r in matched_rows if customer_id in session_links.get(f"{r[0]}-{r[1]}", set())]
        new_rows = [r for r in matched_rows if customer_id not in session_links.get(f"{r[0]}-{r[1]}", set())]
        new_keys = [f"{r[0]}-{r[1]}" for r in new_rows]

        if not new_rows and already_added:
            snack(page, "Item already added", accent=CLAY)
            page.update()
            return

        for r in new_rows:
            key = f"{r[0]}-{r[1]}"
            session_links.setdefault(key, set()).add(customer_id)

        if new_rows:
            save_customer_assignments(customer_id, new_rows)
            render_assigned(new_keys)
            section_label.value = f"ASSIGNED ITEMS · {len(current_item_codes['value'])} total"
            export_csv_btn.disabled = False
            export_pdf_btn.disabled = False
            codes_field.value = ""

        if new_rows and not already_added:
            snack(page, f"Assigned {len(new_rows)} item(s)")
        elif new_rows and already_added:
            snack(page, f"Assigned {len(new_rows)} item(s); Item already added", accent=CLAY)
        elif not matched_rows:
            snack(page, f"No matching item found for: {', '.join(raw_codes)}", accent=CLAY)
        
        try:
            await codes_field.focus()
        except Exception:
            pass
        page.update()

    # Link Enter/Return key (sent by Bluetooth scanners) to trigger assignment automatically
    codes_field.on_submit = on_assign_click

    assign_row = ft.Column(
        [
            dropdown_container,
            ft.Row(
                [
                    codes_field,
                    submit_arrow_button(on_click=on_assign_click, tooltip="Assign to customer"),
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=SPACE_SM,
    )

    # ---------- export (CSV & PDF built from session_links) ----------
    export_picker = ft.FilePicker()
    page.services.append(export_picker)

    def build_export_csv():
        import csv
        import io

        rows = fetch_by_item_codes(current_item_codes["value"])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(COLUMNS + ["customer"])
        for row in rows:
            item_key = f"{row[0]}-{row[1]}"
            ids = session_links.get(item_key, set())
            names = [customer_lookup[cid][1] for cid in ids if cid in customer_lookup]
            if not names:
                writer.writerow(list(row) + ["—"])
            else:
                for cust_name in names:
                    writer.writerow(list(row) + [cust_name])
        return output.getvalue()

    def build_export_pdf():
        import io
        import datetime
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#9E7A36"),
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "DocMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#5A6B7C"),
            spaceAfter=12,
        )
        header_cell_style = ParagraphStyle(
            "HeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#FFFFFF"),
        )
        data_cell_style = ParagraphStyle(
            "DataCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1A1A1E"),
        )

        story = []
        story.append(Paragraph("ASSIGNED ORDER FORM REPORT", title_style))
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Generated: {now_str}  ·  Total Items: {len(current_item_codes['value'])}", meta_style))

        rows = fetch_by_item_codes(current_item_codes["value"])
        table_data = [[Paragraph(c, header_cell_style) for c in (COLUMNS + ["Customer"])]]

        for row in rows:
            item_key = f"{row[0]}-{row[1]}"
            ids = session_links.get(item_key, set())
            names = [customer_lookup[cid][1] for cid in ids if cid in customer_lookup]
            customer_list = names if names else ["—"]

            for cust_name in customer_list:
                row_cells = [Paragraph(str(v), data_cell_style) for v in row]
                row_cells.append(Paragraph(cust_name, data_cell_style))
                table_data.append(row_cells)

        col_widths = [75, 75, 140, 70, 75, 75, 170]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A1A1E")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D0D0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5F7")]),
        ]))

        story.append(t)
        doc.build(story)
        return buffer.getvalue()

    async def on_export_click(e):
        if not current_item_codes["value"]:
            return

        csv_text = build_export_csv()
        try:
            result = await export_picker.save_file(
                dialog_title="Export assigned order form (CSV)",
                file_name="order_form_export.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=csv_text.encode("utf-8"),
            )
            if not result:
                return
            snack(page, "Exported order_form_export.csv")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    async def on_export_pdf_click(e):
        if not current_item_codes["value"]:
            return

        pdf_bytes = build_export_pdf()
        try:
            result = await export_picker.save_file(
                dialog_title="Export assigned order form (PDF)",
                file_name="order_form_export.pdf",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pdf"],
                src_bytes=pdf_bytes,
            )
            if not result:
                return
            snack(page, "Exported order_form_export.pdf")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    export_csv_btn = primary_button("Export CSV", on_click=on_export_click, icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, expand=True)
    export_pdf_btn = primary_button("Export PDF", on_click=on_export_pdf_click, icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, expand=True)

    has_items = bool(current_item_codes["value"])
    export_csv_btn.disabled = not has_items
    export_pdf_btn.disabled = not has_items

    export_buttons_row = ft.Row(
        [export_csv_btn, export_pdf_btn],
        spacing=SPACE_SM,
    )

    # ---------- per-row link dialog ----------
    link_item_key = {"value": None}
    link_checkboxes_column = ft.Column(spacing=SPACE_SM, scroll=ft.ScrollMode.AUTO, height=260)
    link_dialog_title = heading_text("Link Customers", size=18)
    link_dialog_sub = subheading_text("")

    def close_link_dialog(e=None):
        page.pop_dialog()

    def save_links(e):
        item_key = link_item_key["value"]
        if not item_key:
            page.pop_dialog()
            return

        selected_ids = {
            cb.data for cb in link_checkboxes_column.controls
            if isinstance(cb, ft.Checkbox) and cb.value
        }
        if selected_ids:
            session_links[item_key] = selected_ids
        elif item_key in session_links:
            del session_links[item_key]

        parts = item_key.split("-", 1)
        item_no = parts[0]
        tag = parts[1] if len(parts) > 1 else ""
        update_item_assignments(item_no, tag, selected_ids)

        page.pop_dialog()
        page.update()
        render_rows(fetch_by_item_codes(current_item_codes["value"]))
        snack(page, f"Updated links for {item_key}")
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

    def open_link_dialog(item_key):
        link_item_key["value"] = item_key
        link_dialog_sub.value = f"Item: {item_key}"

        linked_ids = session_links.get(item_key, set())

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

    # ---------- totals summary ----------
    totals_cards_container = ft.Column(spacing=SPACE_SM)
    totals_section = ft.Container(
        content=ft.Column(
            [
                eyebrow_text("TOTALS SUMMARY"),
                ft.Container(height=SPACE_SM),
                totals_cards_container,
            ],
            spacing=0,
        ),
        visible=False,
    )

    def render_totals_summary():
        summary_rows = fetch_customer_totals_summary()

        if not summary_rows:
            totals_section.visible = False
            return

        grand_items = sum(r["item_count"] for r in summary_rows)
        grand_net = sum(r["total_net_weight"] for r in summary_rows)
        grand_gross = sum(r["total_gross_weight"] for r in summary_rows)

        grand_card = app_card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("GRAND TOTAL", color=BRASS, weight=ft.FontWeight.BOLD, size=13.5),
                            ft.Text(f"{grand_items} items total", color=SLATE, size=12),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [
                            ft.Text(f"Net Wt: {grand_net:.3f} g", color=IVORY, weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"Gross Wt: {grand_gross:.3f} g", color=IVORY, weight=ft.FontWeight.BOLD, size=13),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                    ),
                ],
                spacing=SPACE_SM,
            ),
            padding=SPACE_MD,
        )

        totals_cards_container.controls = [grand_card]
        totals_section.visible = True

    # ---------- table rendering ----------
    def render_rows(rows):
        if not rows:
            table_container.visible = False
            empty_container.visible = True
            render_totals_summary()
            page.update()
            return

        row_controls = []
        row_index = 0
        for row in rows:
            item_key = f"{row[0]}-{row[1]}"
            linked_ids = session_links.get(item_key, set())
            names = [customer_lookup[cid][1] for cid in linked_ids if cid in customer_lookup]
            customer_list = names if names else ["—"]

            for cust_name in customer_list:
                row_controls.append(
                    table_data_row(
                        [ft.Container(data_cell_text(v), width=COL_WIDTH) for v in row]
                        + [ft.Container(
                            data_cell_text(cust_name, muted=(cust_name == "—")),
                            width=CUSTOMERS_COL_WIDTH,
                        )]
                        + [
                            ft.Container(
                                content=icon_action_button(
                                    ft.Icons.LINK, BRASS, "Link customers",
                                    lambda e, ik=item_key: open_link_dialog(ik),
                                ),
                                width=ACTION_COL_WIDTH,
                                alignment=ft.Alignment.CENTER,
                            )
                        ],
                        index=row_index,
                    )
                )
                row_index += 1
        ledger_rows.controls = row_controls
        table_container.visible = True
        empty_container.visible = False
        render_totals_summary()
        page.update()

    def clear_assigned():
        clear_assignments()
        session_links.clear()
        current_item_codes["value"] = []
        section_label.value = "ASSIGNED ITEMS"
        clear_btn.visible = False
        export_csv_btn.disabled = True
        export_pdf_btn.disabled = True
        render_rows([])
        render_totals_summary()
        page.update()

    def save_links(e):
        item_key = link_item_key["value"]
        if not item_key:
            page.pop_dialog()
            return

        selected_ids = {
            cb.data for cb in link_checkboxes_column.controls
            if isinstance(cb, ft.Checkbox) and cb.value
        }
        if selected_ids:
            session_links[item_key] = selected_ids
        elif item_key in session_links:
            del session_links[item_key]

        parts = item_key.split("-", 1)
        item_no = parts[0]
        tag = parts[1] if len(parts) > 1 else ""
        update_item_assignments(item_no, tag, selected_ids)

        page.pop_dialog()
        page.update()
        render_rows(fetch_by_item_codes(current_item_codes["value"]))
        render_totals_summary()
        snack(page, f"Updated links for {item_key}")
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
                ft.Container(height=SPACE_LG),
                totals_section,
                ft.Container(height=SPACE_SM),
                export_buttons_row,
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
        render_totals_summary()

    def refresh_and_render():
        nonlocal session_links
        refresh_customer_list()
        session_links = fetch_assignments()
        current_item_codes["value"] = list(session_links.keys())
        if current_item_codes["value"]:
            clear_btn.visible = True
            export_csv_btn.disabled = False
            export_pdf_btn.disabled = False
            section_label.value = f"ASSIGNED ITEMS · {len(current_item_codes['value'])} total"
            render_rows(fetch_by_item_codes(current_item_codes["value"]))
        else:
            clear_btn.visible = False
            export_csv_btn.disabled = True
            export_pdf_btn.disabled = True
            section_label.value = "ASSIGNED ITEMS"
            render_rows([])
        render_totals_summary()

    # Attach refresh hook so main.py can call it on tab switch
    view.refresh_customers = refresh_and_render
    return view


# Backward-compatibility alias
build_ledger_view = build_orderform_view
