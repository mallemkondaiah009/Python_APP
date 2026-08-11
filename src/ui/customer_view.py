import flet as ft
from db.storage import store_customer, update_customer, delete_customer, fetch_customers

INK = "#14161C"
SURFACE = "#1E212B"
SURFACE_ALT = "#242836"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"
CLAY = "#E2685C"

CUST_COLUMNS = ["customer_code", "customer_name", "customer_number"]
COL_WIDTH = 140
ACTION_COL_WIDTH = 90
TABLE_WIDTH = COL_WIDTH * len(CUST_COLUMNS) + ACTION_COL_WIDTH


def build_customers_view(page: ft.Page):
    customer_rows = ft.Column(spacing=0, width=TABLE_WIDTH)

    def header_cell(label):
        return ft.Text(
            label.replace("_", " ").upper(), size=10, weight=ft.FontWeight.W_600,
            color=BRASS, style=ft.TextStyle(letter_spacing=1),
        )

    def data_cell(value):
        return ft.Text(str(value) if value else "—", size=12, color=IVORY)

    table_header = ft.Container(
        content=ft.Row(
            [ft.Container(header_cell(c), width=COL_WIDTH) for c in CUST_COLUMNS]
            + [ft.Container(header_cell(""), width=ACTION_COL_WIDTH)],
            spacing=0,
        ),
        padding=ft.Padding(14, 10, 14, 10),
        bgcolor=SURFACE_ALT,
        width=TABLE_WIDTH,
    )

    table_scroll = ft.Row(
        controls=[ft.Column([table_header, customer_rows], spacing=0, width=TABLE_WIDTH)],
        scroll=ft.ScrollMode.ALWAYS,
    )

    customers_table_container = ft.Container(
        content=table_scroll,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BRASS_DIM),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        width=340,
        visible=False,
    )

    empty_msg = ft.Text("No customers yet — tap 'Add Customer' to create one.", size=12, color=SLATE)

    # ---------- snackbar helper ----------
    def show_snack(message, color=BRASS):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=IVORY),
                bgcolor=SURFACE_ALT,
            )
        )

    # ---------- shared form fields (used by both Add and Edit dialogs) ----------
    def field(label, hint, keyboard=None):
        return ft.TextField(
            label=label, hint_text=hint, keyboard_type=keyboard,
            border_color=BRASS_DIM, focused_border_color=BRASS,
            label_style=ft.TextStyle(color=SLATE, size=12),
            text_style=ft.TextStyle(color=IVORY),
            cursor_color=BRASS, bgcolor=SURFACE, border_radius=8,
        )

    code_field = field("Customer Code", "Enter Customer Code")
    name_field = field("Customer Name", "Enter Customer Name")
    number_field = field("Customer Number", "Enter Customer Number", ft.KeyboardType.PHONE)
    error_text = ft.Text("", size=12, color=CLAY, visible=False)

    # tracks which customer id is currently being edited; None = Add mode
    editing_id = {"value": None}

    def reset_fields():
        code_field.value = ""
        name_field.value = ""
        number_field.value = ""
        error_text.visible = False
        editing_id["value"] = None

    def close_dialog(e=None):
        page.pop_dialog()

    def save_customer(e):
        code = (code_field.value or "").strip()
        name = (name_field.value or "").strip()
        number = (number_field.value or "").strip()

        if not code or not name:
            error_text.value = "Customer Code and Name are required."
            error_text.visible = True
            page.update()
            return

        try:
            was_editing = editing_id["value"] is not None
            if was_editing:
                update_customer(editing_id["value"], code, name, number)
            else:
                store_customer(code, name, number)
            reset_fields()
            page.pop_dialog()
            page.update()
            refresh_customers()
            show_snack("Customer updated" if was_editing else "Customer added")
            page.update()
        except Exception as ex:
            error_text.value = str(ex)
            error_text.visible = True
            page.update()

    dialog_title = ft.Text(
        "Add Customer", size=20, color=IVORY, weight=ft.FontWeight.W_600,
        style=ft.TextStyle(font_family="Playfair"),
    )
    dialog_subtitle = ft.Text("Enter customer details below", size=12, color=SLATE)

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        title=ft.Column([dialog_title, dialog_subtitle], spacing=4, tight=True),
        content=ft.Container(
            content=ft.Column([code_field, name_field, number_field, error_text], spacing=16, tight=True),
            width=320,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog, style=ft.ButtonStyle(color=SLATE)),
            ft.ElevatedButton(
                "Save Customer", on_click=save_customer,
                style=ft.ButtonStyle(
                    bgcolor=BRASS, color=INK,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_add_dialog(e):
        reset_fields()
        dialog_title.value = "Add Customer"
        dialog_subtitle.value = "Enter customer details below"
        page.show_dialog(dialog)

    def open_edit_dialog(customer_id, code, name, number):
        editing_id["value"] = customer_id
        code_field.value = code
        name_field.value = name
        number_field.value = number
        error_text.visible = False
        dialog_title.value = "Edit Customer"
        dialog_subtitle.value = "Update customer details below"
        page.show_dialog(dialog)

    # ---------- delete confirmation ----------
    delete_target = {"id": None, "name": None}
    delete_confirm_text = ft.Text("", size=13, color=IVORY)

    def close_delete_dialog(e=None):
        page.pop_dialog()

    def confirm_delete(e):
        if delete_target["id"] is not None:
            name = delete_target["name"]
            delete_customer(delete_target["id"])
            page.pop_dialog()
            page.update()
            refresh_customers()
            show_snack(f"Deleted '{name}'", color=CLAY)
            page.update()

    delete_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        title=ft.Text("Delete Customer", size=18, color=IVORY, weight=ft.FontWeight.W_600),
        content=delete_confirm_text,
        actions=[
            ft.TextButton("Cancel", on_click=close_delete_dialog, style=ft.ButtonStyle(color=SLATE)),
            ft.ElevatedButton(
                "Delete", on_click=confirm_delete,
                style=ft.ButtonStyle(
                    bgcolor=CLAY, color=IVORY,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_delete_dialog(customer_id, name):
        delete_target["id"] = customer_id
        delete_target["name"] = name
        delete_confirm_text.value = f"Delete '{name}'? This can't be undone."
        page.show_dialog(delete_dialog)

    # ---------- table rendering ----------
    def refresh_customers():
        rows = fetch_customers(limit=100)
        if not rows:
            customers_table_container.visible = False
            empty_msg.visible = True
            return

        row_controls = []
        for i, row in enumerate(rows):
            customer_id, code, name, number = row
            row_controls.append(
                ft.Container(
                    content=ft.Row(
                        [ft.Container(data_cell(v), width=COL_WIDTH) for v in (code, name, number)]
                        + [
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            icon_color=BRASS,
                                            icon_size=16,
                                            tooltip="Edit",
                                            on_click=lambda e, cid=customer_id, c=code, n=name, num=number: open_edit_dialog(cid, c, n, num),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color=CLAY,
                                            icon_size=16,
                                            tooltip="Delete",
                                            on_click=lambda e, cid=customer_id, n=name: open_delete_dialog(cid, n),
                                        ),
                                    ],
                                    spacing=0,
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

        customer_rows.controls = row_controls
        customers_table_container.visible = True
        empty_msg.visible = False

    add_btn = ft.ElevatedButton(
        "ADD CUSTOMER",
        icon=ft.Icons.PERSON_ADD_ALT_1,
        on_click=open_add_dialog,
        style=ft.ButtonStyle(
            bgcolor=BRASS, color=INK, padding=18,
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_600, letter_spacing=1, size=13),
        ),
        expand=True,
    )

    header_row = ft.Text(
        "CUSTOMERS · ALL RECORDS", size=11, weight=ft.FontWeight.W_600,
        color=SLATE, style=ft.TextStyle(letter_spacing=1),
    )

    refresh_customers()  # load existing customers immediately

    return ft.Container(
        content=ft.Column(
            [add_btn, ft.Container(height=6), header_row, ft.Container(height=10),
             customers_table_container, empty_msg],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=20,
        bgcolor=INK,
        expand=True,
    )