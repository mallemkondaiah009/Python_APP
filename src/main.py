import flet as ft
from ui.ledger_view import build_ledger_view
from ui.upload_view import build_upload_view
from ui.customer_view import build_customers_view
from db.storage import init_customer_table, init_link_table 

INK = "#14161C"
SURFACE = "#1E212B"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"


def main(page: ft.Page):
    init_customer_table()   
    init_link_table()       

    page.title = "Stock Uploader"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = INK
    page.padding = 0

    page.fonts = {
        "Playfair": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        "Manrope": "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf",
    }
    page.theme = ft.Theme(font_family="Manrope")

    content_area = ft.Container(expand=True)

    def show_ledger():
        content_area.content = build_ledger_view(page)
        page.update()

    def show_upload():
        content_area.content = build_upload_view(page)
        page.update()

    def show_customers():
        content_area.content = build_customers_view(page)
        page.update()

    async def go_ledger(e):
        await page.close_drawer()
        show_ledger()

    async def go_upload(e):
        await page.close_drawer()
        show_upload()

    async def go_customers(e):
        await page.close_drawer()
        show_customers()

    def menu_item(icon, label, on_click):
        return ft.ListTile(
            leading=ft.Icon(icon, color=BRASS),
            title=ft.Text(label, color=IVORY, size=14),
            on_click=on_click,
        )

    drawer = ft.NavigationDrawer(
        bgcolor=SURFACE,
        controls=[
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DIAMOND_OUTLINED, color=BRASS, size=20),
                        ft.Text(
                            "STOCK UPLOADER", size=16, weight=ft.FontWeight.W_600, color=BRASS,
                            style=ft.TextStyle(font_family="Playfair", letter_spacing=1),
                        ),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            ft.Divider(color=BRASS_DIM, height=1),
            menu_item(ft.Icons.HOME_OUTLINED, "Stock Ledger", go_ledger),
            menu_item(ft.Icons.UPLOAD_FILE_OUTLINED, "Upload Data", go_upload),
            menu_item(ft.Icons.PEOPLE_OUTLINE, "Customers", go_customers),
        ],
    )

    page.drawer = drawer

    async def open_drawer(e):
        await page.show_drawer()

    page.appbar = ft.AppBar(
        leading=ft.IconButton(icon=ft.Icons.MENU, icon_color=BRASS, on_click=open_drawer),
        title=ft.Text(
            "STOCK UPLOADER", size=18, weight=ft.FontWeight.W_600, color=BRASS,
            style=ft.TextStyle(font_family="Playfair", letter_spacing=1),
        ),
        center_title=False,
        bgcolor=INK,
        elevation=0,
    )

    page.add(content_area)
    show_ledger()  # default landing view


if __name__ == "__main__":
    ft.run(main)