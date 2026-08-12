import flet as ft
from db.storage import store_customer, update_customer, delete_customer, fetch_customers
from ui.theme import (
    INK, SURFACE, SURFACE_ALT, BRASS, BRASS_DIM, IVORY, SLATE, CLAY,
    SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, SPACE_XXL, RADIUS_LG, RADIUS_MD,
    ROW_H_PAD, PAGE_H_PAD,
    eyebrow_text, heading_text, subheading_text, header_cell_text, data_cell_text,
    primary_button, danger_button, icon_action_button, app_text_field,
    table_shell, table_header_row, table_data_row, empty_state, snack,
)

CUST_COLUMNS = ["customer_code", "customer_name", "customer_number"]
COL_WIDTH = 140
ACTION_COL_WIDTH = 100
TABLE_WIDTH = COL_WIDTH * len(CUST_COLUMNS) + ACTION_COL_WIDTH


def build_customers_view(page: ft.Page):
    # ---------- table header ----------
    table_header = table_header_row(
        [ft.Container(header_cell_text(c), width=COL_WIDTH) for c in CUST_COLUMNS]
        + [ft.Container(width=ACTION_COL_WIDTH)],
    )
    table_header.width = TABLE_WIDTH

    customer_rows = ft.Column(spacing=0, width=TABLE_WIDTH)
    customers_table_container = table_shell(table_header, customer_rows, TABLE_WIDTH)
    customers_table_container.visible = False

    empty_container = empty_state("No customers yet — tap 'Add Customer' to create one.")

    # ---------- shared form fields (used by both Add and Edit dialogs) ----------
    code_field = app_text_field("Customer Code", "Enter customer code")
    name_field = app_text_field("Customer Name", "Enter customer name")
    number_field = app_text_field("Customer Number", "Enter phone number", keyboard=ft.KeyboardType.PHONE)
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
            snack(page, "Customer updated" if was_editing else "Customer added")
            page.update()
        except Exception as ex:
            error_text.value = str(ex)
            error_text.visible = True
            page.update()

    dialog_title = heading_text("Add Customer", size=20)
    dialog_subtitle = subheading_text("Enter customer details below")

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=RADIUS_LG),
        title=ft.Column([dialog_title, dialog_subtitle], spacing=4, tight=True),
        content=ft.Container(
            content=ft.Column(
                [code_field, name_field, number_field, error_text],
                spacing=SPACE_LG,
                tight=True,
            ),
            width=320,
            padding=ft.Padding(0, SPACE_MD, 0, 0),
        ),
        actions=[
            ft.TextButton(
                content=ft.Text("Cancel", color=SLATE, size=13, weight=ft.FontWeight.W_600),
                on_click=close_dialog,
            ),
            primary_button("Save Customer", on_click=save_customer),
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
            snack(page, f"Deleted '{name}'", accent=CLAY)
            page.update()

    delete_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=RADIUS_LG),
        title=heading_text("Delete Customer", size=18),
        content=delete_confirm_text,
        actions=[
            ft.TextButton(
                content=ft.Text("Cancel", color=SLATE, size=13, weight=ft.FontWeight.W_600),
                on_click=close_delete_dialog,
            ),
            danger_button("Delete", on_click=confirm_delete),
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
            empty_container.visible = True
            return

        row_controls = []
        for i, row in enumerate(rows):
            customer_id, code, name, number = row
            row_controls.append(
                table_data_row(
                    [ft.Container(data_cell_text(v), width=COL_WIDTH) for v in (code, name, number)]
                    + [
                        ft.Container(
                            content=ft.Row(
                                [
                                    icon_action_button(
                                        ft.Icons.EDIT_OUTLINED, BRASS, "Edit",
                                        lambda e, cid=customer_id, c=code, n=name, num=number:
                                            open_edit_dialog(cid, c, n, num),
                                    ),
                                    icon_action_button(
                                        ft.Icons.DELETE_OUTLINE, CLAY, "Delete",
                                        lambda e, cid=customer_id, n=name: open_delete_dialog(cid, n),
                                    ),
                                ],
                                spacing=4,
                                alignment=ft.MainAxisAlignment.CENTER,
                                tight=True,
                            ),
                            width=ACTION_COL_WIDTH,
                            alignment=ft.Alignment.CENTER,
                        )
                    ],
                    index=i,
                )
            )

        customer_rows.controls = row_controls
        customers_table_container.visible = True
        empty_container.visible = False

    add_btn = primary_button("Add Customer", on_click=open_add_dialog, icon=ft.Icons.PERSON_ADD_ALT_1, expand=True)

    refresh_customers()  # load existing customers immediately

    return ft.Container(
        content=ft.Column(
            [
                add_btn,
                ft.Container(height=SPACE_SM),
                eyebrow_text("Customers · All Records"),
                ft.Container(height=SPACE_SM),
                customers_table_container,
                empty_container,
            ],
            spacing=SPACE_SM,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=PAGE_H_PAD,
        bgcolor=INK,
        expand=True,
    )