import csv
import datetime
import io
import flet as ft

from db.storage import (
    fetch_report_assignments,
    fetch_customers,
    fetch_report_purities,
)
from ui.theme import (
    INK, SURFACE, SURFACE_ALT, BRASS, BRASS_DIM, IVORY, SLATE, CLAY, EMERALD,
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL,
    RADIUS_MD, RADIUS_LG,
    ROW_H_PAD, PAGE_H_PAD,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, ghost_button, app_text_field, app_card,
    table_shell, table_header_row, table_data_row, empty_state, snack,
)

# Table column definitions & widths (matching ledger style)
REPORT_COLUMNS = [
    ("Customer", 130),
    ("Code", 85),
    ("Item No", 95),
    ("Tag", 95),
    ("Purity", 85),
    ("Net Wt (g)", 95),
    ("Gross Wt (g)", 95),
    ("Assigned Date", 140),
]
TABLE_WIDTH = sum(w for _, w in REPORT_COLUMNS)


def build_reports_view(page: ft.Page):
    # ──────────── state & controls ────────────
    customer_dropdown = ft.Dropdown(
        hint_text="Customer",
        options=[ft.DropdownOption(key="ALL", text="All Customers")],
        value="ALL",
        border_color=BRASS_DIM,
        focused_border_color=BRASS,
        color=IVORY,
        bgcolor=SURFACE,
        border_radius=RADIUS_MD,
        text_size=13,
        content_padding=ft.Padding(ROW_H_PAD, 12, ROW_H_PAD, 12),
        expand=True,
    )

    date_preset_dropdown = ft.Dropdown(
        hint_text="Date Range",
        options=[
            ft.DropdownOption(key="ALL", text="All Time"),
            ft.DropdownOption(key="TODAY", text="Today"),
            ft.DropdownOption(key="YESTERDAY", text="Yesterday"),
            ft.DropdownOption(key="7DAYS", text="Last 7 Days"),
            ft.DropdownOption(key="30DAYS", text="Last 30 Days"),
            ft.DropdownOption(key="CUSTOM", text="Custom Date Range"),
        ],
        value="ALL",
        border_color=BRASS_DIM,
        focused_border_color=BRASS,
        color=IVORY,
        bgcolor=SURFACE,
        border_radius=RADIUS_MD,
        text_size=13,
        content_padding=ft.Padding(ROW_H_PAD, 12, ROW_H_PAD, 12),
        expand=True,
    )

    purity_dropdown = ft.Dropdown(
        hint_text="Purity",
        options=[ft.DropdownOption(key="ALL", text="All Purities")],
        value="ALL",
        border_color=BRASS_DIM,
        focused_border_color=BRASS,
        color=IVORY,
        bgcolor=SURFACE,
        border_radius=RADIUS_MD,
        text_size=13,
        content_padding=ft.Padding(ROW_H_PAD, 12, ROW_H_PAD, 12),
        expand=True,
    )

    from_date_field = app_text_field("From Date", "YYYY-MM-DD")
    from_date_field.expand = True
    from_date_field.visible = False
    from_date_field.read_only = True

    to_date_field = app_text_field("To Date", "YYYY-MM-DD")
    to_date_field.expand = True
    to_date_field.visible = False
    to_date_field.read_only = True

    # Date pickers for custom date range
    def on_from_date_picked(e):
        if from_date_picker.value:
            picked = from_date_picker.value.strftime("%Y-%m-%d")
            from_date_field.value = picked
            apply_filters(update_page=True)

    def on_to_date_picked(e):
        if to_date_picker.value:
            picked = to_date_picker.value.strftime("%Y-%m-%d")
            to_date_field.value = picked
            apply_filters(update_page=True)

    from_date_picker = ft.DatePicker(on_change=on_from_date_picked)
    to_date_picker = ft.DatePicker(on_change=on_to_date_picked)
    page.overlay.append(from_date_picker)
    page.overlay.append(to_date_picker)

    def open_from_picker(e):
        from_date_picker.open = True
        page.update()

    def open_to_picker(e):
        to_date_picker.open = True
        page.update()

    from_date_field.suffix = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        icon_color=BRASS,
        icon_size=20,
        on_click=open_from_picker,
    )
    to_date_field.suffix = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        icon_color=BRASS,
        icon_size=20,
        on_click=open_to_picker,
    )

    search_field = app_text_field(
        label=None,
        hint="Search Item No, Tag, Customer...",
        prefix_icon=ft.Icons.SEARCH,
    )
    search_field.expand = True

    # Table structure (scrollable table like ledger view)
    table_header = table_header_row(
        [ft.Container(header_cell_text(title), width=width) for title, width in REPORT_COLUMNS]
    )
    table_header.width = TABLE_WIDTH

    report_rows_column = ft.Column(spacing=0, width=TABLE_WIDTH)
    table_container = table_shell(table_header, report_rows_column, TABLE_WIDTH)
    table_container.visible = False

    empty_container = empty_state("No customer assigned stock records match the selected filters.")
    empty_container.visible = True

    table_section_label = eyebrow_text("Report Records")

    filtered_records_store = {"data": []}

    # ──────────── helper functions ────────────

    def populate_dropdown_options():
        """Refresh Customer and Purity dropdown lists from DB."""
        # Customers
        cust_options = [ft.DropdownOption(key="ALL", text="All Customers")]
        for _, ccode, cname, _ in fetch_customers(limit=200):
            label = f"{cname} ({ccode})" if ccode else cname
            cust_options.append(ft.DropdownOption(key=cname, text=label))
        customer_dropdown.options = cust_options
        valid_cust_keys = {opt.key for opt in cust_options}
        if customer_dropdown.value not in valid_cust_keys:
            customer_dropdown.value = "ALL"

        # Purities
        purity_options = [ft.DropdownOption(key="ALL", text="All Purities")]
        for p in fetch_report_purities():
            purity_options.append(ft.DropdownOption(key=p, text=p))
        purity_dropdown.options = purity_options
        valid_purity_keys = {opt.key for opt in purity_options}
        if purity_dropdown.value not in valid_purity_keys:
            purity_dropdown.value = "ALL"

    def resolve_date_range():
        """Compute start_date and end_date strings based on preset or custom input."""
        preset = date_preset_dropdown.value
        today = datetime.date.today()

        if preset == "TODAY":
            s = today.strftime("%Y-%m-%d")
            return s, s
        elif preset == "YESTERDAY":
            y = today - datetime.timedelta(days=1)
            s = y.strftime("%Y-%m-%d")
            return s, s
        elif preset == "7DAYS":
            start = today - datetime.timedelta(days=6)
            return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        elif preset == "30DAYS":
            start = today - datetime.timedelta(days=29)
            return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        elif preset == "CUSTOM":
            f_val = (from_date_field.value or "").strip()
            t_val = (to_date_field.value or "").strip()
            return f_val if f_val else None, t_val if t_val else None
        else:  # ALL
            return None, None

    def apply_filters(e=None, update_page=True):
        start_d, end_d = resolve_date_range()
        records = fetch_report_assignments(
            customer_name=customer_dropdown.value,
            start_date=start_d,
            end_date=end_d,
            purity=purity_dropdown.value,
            search_query=search_field.value,
        )
        filtered_records_store["data"] = records
        render_report(records, update_page=update_page)

    def on_date_preset_change(e):
        preset = date_preset_dropdown.value
        is_custom = (preset == "CUSTOM")
        from_date_field.visible = is_custom
        to_date_field.visible = is_custom
        apply_filters(update_page=True)

    def reset_all_filters(e=None):
        customer_dropdown.value = "ALL"
        date_preset_dropdown.value = "ALL"
        purity_dropdown.value = "ALL"
        search_field.value = ""
        from_date_field.value = ""
        to_date_field.value = ""
        from_date_field.visible = False
        to_date_field.visible = False
        apply_filters(update_page=True)

    # Wire handlers
    customer_dropdown.on_select = lambda e: apply_filters(e, update_page=True)
    date_preset_dropdown.on_select = on_date_preset_change
    purity_dropdown.on_select = lambda e: apply_filters(e, update_page=True)
    search_field.on_change = lambda e: apply_filters(e, update_page=True)

    # ──────────── table rendering ────────────

    def render_report(records, update_page=True):
        if not records:
            table_container.visible = False
            empty_container.visible = True
            table_section_label.value = "REPORT RECORDS · 0 ITEMS"
            export_csv_btn.disabled = True
            export_pdf_btn.disabled = True
            if update_page:
                page.update()
            return

        table_section_label.value = f"REPORT RECORDS · {len(records)} ITEMS"

        # Render rows
        row_controls = []
        for index, r in enumerate(records):
            row_cells = [
                ft.Container(data_cell_text(r["customer_name"]), width=REPORT_COLUMNS[0][1]),
                ft.Container(data_cell_text(r["customer_code"], muted=True), width=REPORT_COLUMNS[1][1]),
                ft.Container(data_cell_text(r["item_no"]), width=REPORT_COLUMNS[2][1]),
                ft.Container(data_cell_text(r["tag"]), width=REPORT_COLUMNS[3][1]),
                ft.Container(data_cell_text(r["purity"]), width=REPORT_COLUMNS[4][1]),
                ft.Container(data_cell_text(f"{r['net_weight']:.3f}"), width=REPORT_COLUMNS[5][1]),
                ft.Container(data_cell_text(f"{r['gross_weight']:.3f}"), width=REPORT_COLUMNS[6][1]),
                ft.Container(data_cell_text(r["assigned_at"], muted=True), width=REPORT_COLUMNS[7][1]),
            ]
            row_controls.append(table_data_row(row_cells, index=index))

        report_rows_column.controls = row_controls
        table_container.visible = True
        empty_container.visible = False
        export_csv_btn.disabled = False
        export_pdf_btn.disabled = False
        if update_page:
            page.update()

    # ──────────── exports (CSV & PDF) ────────────
    export_picker = ft.FilePicker()
    page.services.append(export_picker)

    def build_report_csv(records):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Customer", "Customer Code", "Item No", "Tag", "Purity", "Net Wt (g)", "Gross Wt (g)", "Assigned Date"])
        for r in records:
            writer.writerow([
                r["customer_name"],
                r["customer_code"],
                r["item_no"],
                r["tag"],
                r["purity"],
                r["net_weight"],
                r["gross_weight"],
                r["assigned_at"],
            ])
        return output.getvalue()

    def build_report_pdf(records):
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
            textColor=colors.HexColor("#C6A15B"),
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "DocMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#8B90A0"),
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
        story.append(Paragraph("CUSTOMER ASSIGNED STOCK REPORT", title_style))
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tot_net = sum(r["net_weight"] for r in records)
        tot_gross = sum(r["gross_weight"] for r in records)

        meta_text = (
            f"Generated: {now_str}  ·  Total Items: {len(records)}  ·  "
            f"Net Wt: {tot_net:.3f} g  ·  Gross Wt: {tot_gross:.3f} g"
        )
        story.append(Paragraph(meta_text, meta_style))

        table_data = [[
            Paragraph("Customer", header_cell_style),
            Paragraph("Code", header_cell_style),
            Paragraph("Item No", header_cell_style),
            Paragraph("Tag", header_cell_style),
            Paragraph("Purity", header_cell_style),
            Paragraph("Net Wt", header_cell_style),
            Paragraph("Gross Wt", header_cell_style),
            Paragraph("Assigned Date", header_cell_style),
        ]]

        for r in records:
            table_data.append([
                Paragraph(r["customer_name"], data_cell_style),
                Paragraph(r["customer_code"], data_cell_style),
                Paragraph(r["item_no"], data_cell_style),
                Paragraph(r["tag"], data_cell_style),
                Paragraph(r["purity"], data_cell_style),
                Paragraph(f"{r['net_weight']:.3f}", data_cell_style),
                Paragraph(f"{r['gross_weight']:.3f}", data_cell_style),
                Paragraph(r["assigned_at"], data_cell_style),
            ])

        col_widths = [110, 65, 80, 80, 65, 75, 75, 120]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E212B")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D0D0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5F7")]),
        ]))

        story.append(t)
        doc.build(story)
        return buffer.getvalue()

    async def on_export_csv_click(e):
        recs = filtered_records_store["data"]
        if not recs:
            return
        csv_text = build_report_csv(recs)
        try:
            res = await export_picker.save_file(
                dialog_title="Export Customer Assigned Report (CSV)",
                file_name="customer_assigned_report.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=csv_text.encode("utf-8"),
            )
            if res:
                snack(page, "Exported customer_assigned_report.csv")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    async def on_export_pdf_click(e):
        recs = filtered_records_store["data"]
        if not recs:
            return
        pdf_bytes = build_report_pdf(recs)
        try:
            res = await export_picker.save_file(
                dialog_title="Export Customer Assigned Report (PDF)",
                file_name="customer_assigned_report.pdf",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pdf"],
                src_bytes=pdf_bytes,
            )
            if res:
                snack(page, "Exported customer_assigned_report.pdf")
        except Exception as ex:
            snack(page, f"Export failed: {ex}", accent=CLAY)
        page.update()

    export_csv_btn = primary_button("Export CSV", on_click=on_export_csv_click, icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, expand=True)
    export_pdf_btn = primary_button("Export PDF", on_click=on_export_pdf_click, icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, expand=True)

    # ──────────── Filter panel ────────────
    filters_header = ft.Row(
        [
            eyebrow_text("Filter Reports"),
            ghost_button("Reset Filters", on_click=reset_all_filters),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    date_custom_row = ft.Row(
        [from_date_field, to_date_field],
        spacing=SPACE_SM,
    )

    dropdowns_row = ft.Column(
        [
            customer_dropdown,
            ft.Row(
                [date_preset_dropdown, purity_dropdown],
                spacing=SPACE_SM,
            ),
        ],
        spacing=SPACE_SM,
    )

    filters_panel = app_card(
        content=ft.Column(
            [
                filters_header,
                ft.Container(height=SPACE_XS),
                dropdowns_row,
                date_custom_row,
                ft.Row([search_field], spacing=SPACE_SM),
            ],
            spacing=SPACE_SM,
        ),
        padding=SPACE_MD,
    )

    # Initial data load
    populate_dropdown_options()
    apply_filters(update_page=False)

    # ──────────── Main view ────────────
    view = ft.Container(
        content=ft.Column(
            [
                eyebrow_text("Stock & Customer Reports"),
                ft.Container(height=SPACE_XS),
                filters_panel,
                ft.Container(height=SPACE_MD),
                table_section_label,
                ft.Container(height=SPACE_XS),
                table_container,
                empty_container,
                ft.Container(height=SPACE_LG),
                ft.Row([export_csv_btn, export_pdf_btn], spacing=SPACE_SM),
                ft.Container(height=SPACE_LG),
            ],
            spacing=SPACE_SM,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=PAGE_H_PAD,
        bgcolor=INK,
        expand=True,
    )

    def refresh_report_view():
        populate_dropdown_options()
        apply_filters(update_page=True)

    view.refresh_report = refresh_report_view
    return view
