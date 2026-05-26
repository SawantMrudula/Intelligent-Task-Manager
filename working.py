import flet as ft
import os
import sys
from flet import Icons, BlurTileMode, Colors, BoxShadow, ShadowBlurStyle, Offset, Blur, Stack, ImageFit, ImageRepeat
from proc_chain import create_process_chains_layout, start_proc_chain_updates
from network_monitor import create_network_monitoring_layout
from proc_mon import create_process_monitoring_layout
from Scheduled_processes import create_system_distribution_layout, start_realtime_updates
from logs_analytics import create_logs_analytics_layout
from device_manager import DeviceManagerUI

# Path helper function for PyInstaller
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DesktopApp:
    def __init__(self):
        # Initialize common properties
        self.window_width = 1280
        self.window_height = 720
        self.min_width = 800
        self.min_height = 450
        self.dark_bg = "#1a1b26"
        self.dark_card = "#20212e"
        self.accent_color = "#00ffff"
        self.text_color = "#ffffff"
        self.selected_tab_index = 0
        self.sidebar_expanded = False
        self.sidebar_width = 50
        self.sidebar_expanded_width = 150
        
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
        
        # Path setup - use get_resource_path for PyInstaller compatibility
        self.base_path = get_resource_path("assets")
        self.bg_image_path = os.path.join(self.base_path, "Background.png")
        
        self.svg_icons = {
            "process_monitor": os.path.join(self.base_path, "Process.svg"),
            "network": os.path.join(self.base_path, "Network.svg"),
            "scheduled": os.path.join(self.base_path, "scheduled.svg"),
            "process_chains": os.path.join(self.base_path, "Chaining.svg"),
            "device_manager": os.path.join(self.base_path, "device_manager.svg"),
            "system_logs": os.path.join(self.base_path, "systemlog.svg"),
        }

    def get_tab_content(self):
        """Return the appropriate content based on the selected tab"""
        if self.selected_tab_index == 1:  # Network Connections tab
            layout, init_network = create_network_monitoring_layout(
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow
            )
            init_network(self.page)
            return layout
        elif self.selected_tab_index == 4:  # Device Manager tab
            # Use DeviceManagerUI from the external module
            device_manager_ui = DeviceManagerUI(
                base_path=self.base_path,
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow,
                accent_color=self.accent_color,
                background_color=self.dark_bg,
                text_color=self.text_color
            )
            device_manager_container = device_manager_ui.build()  # Fixed assignment operator
            return device_manager_container

        elif self.selected_tab_index == 3:  # Process Chains tab
            layout, dashboard = create_process_chains_layout(
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow
            )
            start_proc_chain_updates(self.page, dashboard)
            return layout
        elif self.selected_tab_index == 0:  # Process Monitor tab
            layout, init_proc = create_process_monitoring_layout(
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow
            )
            init_proc(self.page)
            return layout
        elif self.selected_tab_index == 2:  # Scheduled Processes tab
            layout, dashboard = create_system_distribution_layout(
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow
            )
            start_realtime_updates(self.page, dashboard)
            return layout  
        elif self.selected_tab_index == 5:  # System Logs tab
            layout, init_logs = create_logs_analytics_layout(
                base_path=self.base_path,
                glass_bgcolor=self.glass_bgcolor,
                container_blur=self.container_blur,
                container_shadow=self.container_shadow,
                accent_color=self.accent_color,
                background_color=self.dark_bg,
                card_color=self.dark_card,
                text_color="#FFFFFF"
            )
            init_logs(self.page)
            return layout
        else:
            return ft.Container(
                content=ft.Text("Coming Soon...", size=20, color="white"),
                alignment=ft.alignment.center,
                expand=True
            )

    # Rest of your code remains the same
    def create_tab_item(self, icon_path, label, index):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Image(
                        src=icon_path,
                        width=24,
                        height=24,
                        color="white" if index != self.selected_tab_index else self.accent_color,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    tooltip=ft.Tooltip(
                        message=label,
                        bgcolor="#08CDFF",
                        text_style=ft.TextStyle(color="white"),
                        padding=10,
                    ) if not self.sidebar_expanded else None,
                    margin=ft.margin.only(left=0),
                    width=24,
                    height=24,
                    alignment=ft.alignment.center,
                ),
                ft.Container(
                    content=ft.Text(
                        label,
                        size=10,
                        color="white" if index != self.selected_tab_index else self.accent_color,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.CLIP,
                        max_lines=2,
                    ),
                    visible=self.sidebar_expanded,
                    padding=ft.padding.only(left=-5),
                )
            ],
            alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=self.glass_bgcolor if index == self.selected_tab_index else None,
            blur=self.container_blur if index == self.selected_tab_index else None,
            shadow=self.container_shadow if index == self.selected_tab_index else None,
            border_radius=0,
            border=ft.border.all(1, self.accent_color) if index == self.selected_tab_index else None,
            width=self.sidebar_expanded_width if self.sidebar_expanded else self.sidebar_width,
            height=50,
            on_click=lambda e, idx=index: self.change_tab(e, idx),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
        )

    def toggle_sidebar(self, e):
        self.sidebar_expanded = not self.sidebar_expanded
        self.sidebar_tabs.controls = [
            self.create_tab_item(icon_path, label, i) 
            for i, (icon_path, label) in enumerate(self.tabs_data)
        ]
        self.left_sidebar.width = self.sidebar_expanded_width if self.sidebar_expanded else self.sidebar_width
        e.page.update()

    def change_tab(self, e, index):
        """Modified change_tab method to handle content switching"""
        self.selected_tab_index = index
        
        # Update tab styling
        for i, tab in enumerate(self.sidebar_tabs.controls):
            if i == index:
                tab.bgcolor = self.glass_bgcolor
                tab.blur = self.container_blur
                tab.shadow = self.container_shadow
                tab.content.controls[0].content.color = self.accent_color
                if len(tab.content.controls) > 1:
                    tab.content.controls[1].content.color = self.accent_color
                tab.border = ft.border.all(1, self.accent_color)
            else:
                tab.bgcolor = None
                tab.blur = None
                tab.shadow = None
                tab.content.controls[0].content.color = "white"
                if len(tab.content.controls) > 1:
                    tab.content.controls[1].content.color = "white"
                tab.border = None
        
        # Update main content
        if hasattr(self, 'main_content_container'):
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
        
        # Create background image container
        background = ft.Container(
            expand=True,
            image_src=self.bg_image_path,
            image_fit=ft.ImageFit.COVER,
            image_repeat=ft.ImageRepeat.NO_REPEAT,
        )
        
        # Initialize tabs
        self.tabs_data = [
            (self.svg_icons["process_monitor"], "Process Monitor"),
            (self.svg_icons["network"], "Network Connections"),
            (self.svg_icons["scheduled"], "Scheduled Processes"),
            (self.svg_icons["process_chains"], "Process Chains"),
            (self.svg_icons["device_manager"], "Device Manager"),
            (self.svg_icons["system_logs"], "System Logs"),
        ]

        # Create sidebar tabs
        self.sidebar_tabs = ft.Column(
            controls=[
                self.create_tab_item(icon_path, label, i) 
                for i, (icon_path, label) in enumerate(self.tabs_data)
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.START,
        )

        # Toggle button for sidebar
        toggle_button = ft.IconButton(
            icon=Icons.MENU,
            icon_color="white",
            icon_size=20,
            on_click=self.toggle_sidebar,
        )

        # Left sidebar container
        self.left_sidebar = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=toggle_button,
                        padding=ft.padding.only(left=2, top=5, bottom=5),
                        alignment=ft.alignment.center_left,
                    ),
                    self.sidebar_tabs,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=self.sidebar_width,
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=ft.border_radius.only(top_right=15),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
        )

        # Top bar with logo, search, notifications, and profile
        top_bar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Image(
                        src=os.path.join(self.base_path, "logo.png"),
                        width=75,
                        height=75,
                        fit=ft.ImageFit.CONTAIN,
                    ),
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
                                    content_padding=ft.padding.only(left=10, right=10),
                                )
                            ],
                            spacing=10,
                        ),
                        bgcolor=self.glass_bgcolor,
                        blur=self.container_blur,
                        border_radius=20,
                        padding=ft.padding.only(left=15, right=15),
                        expand=True,
                    ),
                    ft.Stack([
                        ft.IconButton(
                            icon=Icons.NOTIFICATIONS_OUTLINED,
                            icon_color='white',
                            icon_size=24,
                            tooltip="Notifications",
                        ),
                    ]),
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text("MP"),
                            bgcolor="#00008B",
                            radius=16,
                        ),
                        ft.Text("Mann Pandya", color="white", size=14),
                        ft.Icon(Icons.ARROW_DROP_DOWN, color="white"),
                    ], spacing=5),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=15,
            ),
            padding=ft.padding.only(left=5, right=20, top=0),
            margin=ft.margin.only(top=-10)
        )

        # Create main content container that will be updated with tab changes
        self.main_content_container = ft.Container(
            content=self.get_tab_content(),
            expand=True,
        )

        # Assemble main layout
        main_content = ft.Row(
            controls=[
                self.left_sidebar,
                self.main_content_container,
            ],
            spacing=0,
            expand=True,
        )

        content = ft.Container(
            expand=True,
            content=ft.Column(
                controls=[
                    top_bar,
                    main_content,
                ],
                spacing=0,
                expand=True,
            ),
        )

        # Final page assembly with background and content in a Stack
        page.add(
            ft.Stack(
                controls=[
                    background,
                    content,
                ],
                expand=True,
            )
        )
        
        page.update()

def main(page: ft.Page):
    app = DesktopApp()
    app.main(page)

if __name__ == '__main__':
    ft.app(target=main)