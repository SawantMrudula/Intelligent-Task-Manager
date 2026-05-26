import flet as ft

def main(page: ft.Page):
    page.add(ft.Text("Hello, packaged app!"))

ft.app(target=main)