import flet as ft
from ui.ledger_view import build_ledger_view
from ui.upload_view import build_upload_view
from ui.customer_view import build_customers_view
from ui.report_view import build_reports_view
from db.storage import init_customer_table, init_assignments_table

INK = "#14161C"
SURFACE = "#1E212B"
BRASS = "#C6A15B"
BRASS_DIM = "#3A3626"
IVORY = "#F5F1E8"
SLATE = "#8B90A0"


def main(page: ft.Page):
    init_customer_table()
    init_assignments_table()

    page.title = "ABS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = INK
    page.padding = 0

    page.fonts = {
        "Playfair": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        "Manrope": "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf",
    }
    page.theme = ft.Theme(font_family="Manrope")

    content_area = ft.Container(expand=True)

    # Build each view once so in-session state (e.g. assigned stock links)
    # survives tab navigation. Data resets only on app close or Clear.
    cached_views = {}

    def get_view(name, builder):
        if name not in cached_views:
            cached_views[name] = builder(page)
        return cached_views[name]

    def show_ledger():
        view = get_view("ledger", build_ledger_view)
        # Refresh customer dropdown to pick up newly added customers
        if hasattr(view, "refresh_customers"):
            view.refresh_customers()
        content_area.content = view
        page.update()

    def show_upload():
        content_area.content = get_view("upload", build_upload_view)
        page.update()

    def show_customers():
        content_area.content = get_view("customers", build_customers_view)
        page.update()

    def show_reports():
        view = get_view("reports", build_reports_view)
        if hasattr(view, "refresh_report"):
            view.refresh_report()
        content_area.content = view
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

    async def go_reports(e):
        await page.close_drawer()
        show_reports()

    def menu_item(icon, label, on_click):
        return ft.ListTile(
            leading=ft.Icon(icon, color=BRASS, size=20),
            title=ft.Text(label, color=IVORY, size=14, weight=ft.FontWeight.W_500),
            on_click=on_click,
            content_padding=ft.Padding(20, 0, 20, 0),
        )

    drawer = ft.NavigationDrawer(
        bgcolor=SURFACE,
        controls=[
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DIAMOND_OUTLINED, color=BRASS, size=20),
                        ft.Text(
                            "ABS", size=16, weight=ft.FontWeight.W_600, color=BRASS,
                            style=ft.TextStyle(font_family="Playfair", letter_spacing=1),
                        ),
                    ],
                    spacing=10,
                ),
                padding=ft.Padding(20, 24, 20, 20),
            ),
            ft.Divider(color=BRASS_DIM, height=1),
            ft.Container(height=4),
            menu_item(ft.Icons.HOME_OUTLINED, "Stock Ledger", go_ledger),
            menu_item(ft.Icons.UPLOAD_FILE_OUTLINED, "Upload Data", go_upload),
            menu_item(ft.Icons.PEOPLE_OUTLINE, "Customers", go_customers),
            menu_item(ft.Icons.ASSESSMENT_OUTLINED, "Reports", go_reports),
        ],
    )

    page.drawer = drawer

    async def open_drawer(e):
        await page.show_drawer()

    # AppBar with a subtle bottom accent line
    page.appbar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.Icons.MENU,
            icon_color=BRASS,
            icon_size=22,
            on_click=open_drawer,
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.with_opacity(0.06, IVORY),
            ),
        ),
        title=ft.Text(
            "ABS", size=17, weight=ft.FontWeight.W_600, color=BRASS,
            style=ft.TextStyle(font_family="Playfair", letter_spacing=1.5),
        ),
        center_title=False,
        bgcolor=INK,
        elevation=0,
    )

    page.add(content_area)
    show_ledger()  # default landing view


if __name__ == "__main__":
    ft.run(main)