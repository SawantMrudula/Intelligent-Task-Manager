import flet as ft
import os
import threading
from flet import (
    Icons, BlurTileMode, Colors, BoxShadow, ShadowBlurStyle, Offset, Blur, Stack,
    ImageFit, ImageRepeat
)
from proc_chain import create_process_chains_layout, start_proc_chain_updates
from network_monitor import create_network_monitoring_layout
from proc_mon import create_process_monitoring_layout
#from Scheduled_processes import create_system_distribution_layout, start_realtime_updates
from logs_analytics import create_logs_analytics_layout as create_logs_tab
from device_manager import DeviceManagerUI
from Scheduled_processes import create_system_distribution_layout, start_realtime_updates

class DesktopApp:
    def __init__(self):
        # Window and theme properties
        self.window_width = 1280
        self.window_height = 720
        self.min_width = 800
        self.min_height = 450
        self.dark_bg = "#1a1b26"
        self.dark_card = "#20212e"
        self.accent_color = "#00ffff"
        self.text_color = "#ffffff"
        
        # Sidebar state
        self.selected_tab_index = 0
        self.sidebar_expanded = False
        self.sidebar_width = 50
        self.sidebar_expanded_width = 150
        
        # Cache for tab content
        self.tab_cache = {}
        
        # Glass effect properties
        self.glass_bgcolor = "#20f4f4f4"
        self.container_blur = Blur(10, 10, BlurTileMode.REPEATED)
        self.container_shadow = BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=Colors.BLACK54,
            offset=Offset(2, 2),
            blur_style=ShadowBlurStyle.OUTER
        )
        
        # Platform-agnostic asset paths
        self.base_path = os.path.join(os.path.dirname(__file__), "assets")
        self.bg_image_path = os.path.join(self.base_path, "Background.png")
        self.svg_icons = {
            "process_monitor": os.path.join(self.base_path, "Process.svg"),
            "network": os.path.join(self.base_path, "Network.svg"),
            "scheduled": os.path.join(self.base_path, "scheduled.svg"),
            "process_chains": os.path.join(self.base_path, "Chaining.svg"),
            "device_manager": os.path.join(self.base_path, "device_manager.svg"),
            "system_logs": os.path.join(self.base_path, "systemlog.svg"),
        }
        
        # Preload images to reduce initial lag
        for key in self.svg_icons:
            ft.Image(src=self.svg_icons[key])  # Trigger loading
        ft.Image(src=self.bg_image_path)

    def get_tab_content(self):
        """Return cached or newly created tab content"""
        if self.selected_tab_index not in self.tab_cache:
            if self.selected_tab_index == 0:  # Process Monitor
                layout, init_proc = create_process_monitoring_layout(
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow
                )
                init_proc(self.page)
                self.tab_cache[0] = layout
            elif self.selected_tab_index == 1:  # Network Connections
                layout, init_network = create_network_monitoring_layout(
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow
                )
                init_network(self.page)
                self.tab_cache[1] = layout

            elif self.selected_tab_index == 3:  # Process Chains
                layout, dashboard = create_process_chains_layout(
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow
                )
                threading.Thread(target=start_proc_chain_updates, args=(self.page, dashboard), daemon=True).start()
                self.tab_cache[3] = layout
            elif self.selected_tab_index == 4:  # Device Manager
                device_manager_ui = DeviceManagerUI(
                    base_path=self.base_path,
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow,
                    accent_color=self.accent_color,
                    background_color=self.dark_bg,  # Added missing parameter
                    text_color=self.text_color      # Added missing parameter
                )
                self.tab_cache[4] = device_manager_ui.build()
            elif self.selected_tab_index == 2:  # Scheduled Processes
                layout, dashboard = create_system_distribution_layout(
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow
                )
                threading.Thread(target=start_realtime_updates, args=(self.page, dashboard), daemon=True).start()
                self.tab_cache[2]=layout
            elif self.selected_tab_index == 5:  # System Logs
                layout, init_logs_tab = create_logs_tab(
                    base_path=self.base_path,
                    glass_bgcolor=self.glass_bgcolor,
                    container_blur=self.container_blur,
                    container_shadow=self.container_shadow,
                    accent_color=self.accent_color,
                    background_color=self.dark_bg,
                    card_color=self.dark_card,
                    text_color=self.text_color
                )
                init_logs_tab(self.page)
                self.tab_cache[5] = layout
            else:
                self.tab_cache[self.selected_tab_index] = ft.Container(
                    content=ft.Text("Coming Soon...", size=20, color="white"),
                    alignment=ft.alignment.center,
                    expand=True
                )
        return self.tab_cache[self.selected_tab_index]

    def create_tab_item(self, icon_path, label, index):
        """Create a reusable tab item with stored references"""
        icon = ft.Image(
            src=icon_path,
            width=24,
            height=24,
            color="white" if index != self.selected_tab_index else self.accent_color,
            fit=ImageFit.CONTAIN
        )
        text = ft.Text(
            label,
            size=10,
            color="white" if index != self.selected_tab_index else self.accent_color,
            weight=ft.FontWeight.W_500,
            overflow=ft.TextOverflow.CLIP,
            max_lines=2,
            visible=self.sidebar_expanded
        )
        container = ft.Container(
            content=ft.Row([
                ft.Container(content=icon, width=24, height=24, alignment=ft.alignment.center),
                ft.Container(content=text, padding=ft.padding.only(left=-5))
            ], alignment=ft.MainAxisAlignment.START),
            bgcolor=self.glass_bgcolor if index == self.selected_tab_index else None,
            blur=self.container_blur if index == self.selected_tab_index else None,
            shadow=self.container_shadow if index == self.selected_tab_index else None,
            border=ft.border.all(1, self.accent_color) if index == self.selected_tab_index else None,
            width=self.sidebar_width,
            height=50,
            on_click=lambda e, idx=index: self.change_tab(e, idx),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
            padding=ft.padding.symmetric(horizontal=10, vertical=5)
        )
        container.icon = icon  # Store references for updates
        container.text = text
        return container

    def toggle_sidebar(self, e):
        """Toggle sidebar width and visibility without recreating items"""
        self.sidebar_expanded = not self.sidebar_expanded
        new_width = self.sidebar_expanded_width if self.sidebar_expanded else self.sidebar_width
        for tab in self.sidebar_tabs.controls:
            tab.width = new_width
            tab.text.visible = self.sidebar_expanded
            tab.content.controls[0].tooltip = (
                ft.Tooltip(
                    message=tab.text.value,
                    bgcolor="#08CDFF",
                    text_style=ft.TextStyle(color="white"),
                    padding=10
                ) if not self.sidebar_expanded else None
            )
        self.left_sidebar.width = new_width
        e.page.update()

    def change_tab(self, e, index):
        """Update only the affected tabs and content"""
        old_index = self.selected_tab_index
        self.selected_tab_index = index
        
        for i, tab in enumerate(self.sidebar_tabs.controls):
            if i in (old_index, index):
                is_selected = (i == index)
                tab.bgcolor = self.glass_bgcolor if is_selected else None
                tab.blur = self.container_blur if is_selected else None
                tab.shadow = self.container_shadow if is_selected else None
                tab.border = ft.border.all(1, self.accent_color) if is_selected else None
                tab.icon.color = self.accent_color if is_selected else "white"
                tab.text.color = self.accent_color if is_selected else "white"
        
        self.main_content_container.content = self.get_tab_content()
        e.page.update()

    def main(self, page: ft.Page):
        self.page = page
        page.window_width = self.window_width
        page.window_height = self.window_height
        page.window_min_width = self.min_width
        page.window_min_height = self.min_height
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK

        # Background
        background = ft.Container(
            expand=True,
            image_src=self.bg_image_path,
            image_fit=ImageFit.COVER,
            image_repeat=ImageRepeat.NO_REPEAT
        )

        # Sidebar tabs
        self.tabs_data = [
            (self.svg_icons["process_monitor"], "Process Monitor"),
            (self.svg_icons["network"], "Network Connections"),
            (self.svg_icons["scheduled"], "Scheduled Processes"),
            (self.svg_icons["process_chains"], "Process Chains"),
            (self.svg_icons["device_manager"], "Device Manager"),
            (self.svg_icons["system_logs"], "System Logs"),
        ]
        self.sidebar_tabs = ft.Column(
            controls=[self.create_tab_item(icon_path, label, i) for i, (icon_path, label) in enumerate(self.tabs_data)],
            spacing=5,
            alignment=ft.MainAxisAlignment.START
        )

        # Sidebar with toggle button
        toggle_button = ft.IconButton(
            icon=Icons.MENU,
            icon_color="white",
            icon_size=20,
            on_click=self.toggle_sidebar
        )
        self.left_sidebar = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=toggle_button, padding=ft.padding.only(left=2, top=5, bottom=5)),
                    self.sidebar_tabs
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=self.sidebar_width,
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=ft.border_radius.only(top_right=15),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
        )

        # Top bar
        top_bar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Image(src=os.path.join(self.base_path, "logo.png"), width=75, height=75, fit=ImageFit.CONTAIN),
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(Icons.SEARCH, color='#6c757d', size=20),
                                ft.TextField(
                                    border=ft.InputBorder.NONE,
                                    height=40,
                                    text_size=14,
                                    bgcolor='transparent',
                                    color='white',
                                    hint_text="Search...",
                                    hint_style=ft.TextStyle(color='#6c757d'),
                                    expand=True,
                                    content_padding=ft.padding.only(left=10, right=10)
                                )
                            ],
                            spacing=10
                        ),
                        bgcolor=self.glass_bgcolor,
                        blur=self.container_blur,
                        border_radius=20,
                        padding=ft.padding.only(left=15, right=15),
                        expand=True
                    ),
                    ft.Stack([
                        ft.IconButton(
                            icon=Icons.NOTIFICATIONS_OUTLINED,
                            icon_color='white',
                            icon_size=24,
                            tooltip="Notifications"
                        )
                    ]),
                    ft.Row([
                        ft.CircleAvatar(content=ft.Text("MP"), bgcolor="#00008B", radius=16),
                        ft.Text("Mann Pandya", color="white", size=14),
                        ft.Icon(Icons.ARROW_DROP_DOWN, color="white")
                    ], spacing=5)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=15
            ),
            padding=ft.padding.only(left=5, right=20, top=0),
            margin=ft.margin.only(top=-10)
        )

        # Main content area
        self.main_content_container = ft.Container(content=self.get_tab_content(), expand=True)
        main_content = ft.Row(controls=[self.left_sidebar, self.main_content_container], spacing=0, expand=True)

        # Assemble page
        content = ft.Container(
            expand=True,
            content=ft.Column(controls=[top_bar, main_content], spacing=0, expand=True)
        )
        page.add(ft.Stack(controls=[background, content], expand=True))
        page.update()

def main(page: ft.Page):
    app = DesktopApp()
    app.main(page)

if __name__ == '__main__':
    ft.app(target=main)