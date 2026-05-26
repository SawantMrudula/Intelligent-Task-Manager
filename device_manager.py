import flet as ft
import os
import subprocess
import threading
import time
import re

# For microphone functionality
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class DeviceManagerUI:
    def __init__(
        self,
        base_path: str,
        glass_bgcolor: str,
        container_blur: ft.Blur,
        container_shadow: ft.BoxShadow,
        accent_color: str,
        background_color: str,
        text_color: str
    ):
        """
        Construct a DeviceManagerUI that can be integrated into your main Flet app.

        :param base_path:        Path to assets (icons, images).
        :param glass_bgcolor:    Semi-transparent background for the "glass" effect.
        :param container_blur:   Flet Blur object for containers.
        :param container_shadow: Flet BoxShadow for containers.
        :param accent_color:     Color used for highlights (e.g. #00ffff).
        :param background_color: Overall background color (e.g. #1a1b26).
        :param text_color:       Primary text color (e.g. #ffffff).
        """

        # Store parameters
        self.base_path = base_path
        self.glass_bgcolor = glass_bgcolor  # This should be semi-transparent
        self.container_blur = container_blur
        self.container_shadow = container_shadow
        self.accent_color = accent_color
        self.background_color = background_color
        self.text_color = text_color

        # For logging
        self.log_column = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )
        # Store messages until the UI is built
        self.log_messages = []

        # PowerShell path (for Windows-based operations)
        self.POWERSHELL_PATH = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"

    # ----------------------
    # LOGGING & UTILITY
    # ----------------------
    def add_to_log(self, text: str, color: str = "white"):
        """Add a message to the log section."""
        # If UI is built, append immediately
        if self.log_column and hasattr(self.log_column, 'page') and self.log_column.page:
            self.log_column.controls.append(ft.Text(text, color=color))
            self.log_column.update()
        else:
            # Otherwise, store for later
            self.log_messages.append((text, color))

    def display_stored_log_messages(self):
        """Display any messages stored before UI was built."""
        if self.log_column and hasattr(self.log_column, 'page') and self.log_column.page:
            for text, color in self.log_messages:
                self.log_column.controls.append(ft.Text(text, color=color))
            self.log_messages.clear()
            self.log_column.update()

    def clear_logs(self):
        """Clear all log messages."""
        if self.log_column:
            self.log_column.controls.clear()
            self.add_to_log("🧹 Logs cleared", self.text_color)

    def run_powershell_command(self, command: str) -> str:
        """Run a PowerShell command and return its output (Windows only)."""
        if not os.path.exists(self.POWERSHELL_PATH):
            return "❌ PowerShell is not available."

        try:
            output = subprocess.check_output(
                [self.POWERSHELL_PATH, "-Command", command],
                encoding="utf-8",
                stderr=subprocess.STDOUT
            )
            return output.strip()
        except subprocess.CalledProcessError as e:
            return f"❌ Error: {e.output.strip()}"

    def is_admin(self) -> bool:
        """Check if script is running with administrator privileges (Windows)."""
        command = '[bool](([System.Security.Principal.WindowsIdentity]::GetCurrent()).Groups -match "S-1-5-32-544")'
        output = self.run_powershell_command(command)
        return "True" in output

    # ----------------------
    # USB FUNCTIONALITY
    # ----------------------
    def get_usb_ports(self):
        """Get all USB devices (Windows)."""
        command = 'pnputil /enum-devices /class "USB"'
        try:
            output = subprocess.check_output(command, shell=True, encoding='utf-8')
            usb_devices = []
            for line in output.splitlines():
                if "USB\\" in line:
                    device_id = line.split(":")[-1].strip()
                    usb_devices.append(device_id)
            return usb_devices
        except subprocess.CalledProcessError:
            return []

    def toggle_usb(self, action: str, device_id: str = None):
        """Enable or disable USB devices."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control USB devices.", "red")
            return

        command_action = "/disable-device" if action == "disable" else "/enable-device"
        if device_id:
            command = f'pnputil {command_action} "{device_id}" /force'
            subprocess.run(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.add_to_log(f"✅ USB Device {action}d successfully.", "green")
        else:
            device_ids = self.get_usb_ports()
            if not device_ids:
                self.add_to_log("⚠️ No USB devices found.", "red")
                return
            for dev_id in device_ids:
                self.add_to_log(f"USB Device Detected: {dev_id}", "blue")
                command = f'pnputil {command_action} "{dev_id}" /force'
                subprocess.run(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.add_to_log(f"✅ All USB Devices {action}d successfully.", "green")

        self.add_to_log("🔄 Please restart your system for complete changes.", "orange")

    def create_usb_section(self) -> ft.Container:
        """USB control UI."""
        usb_devices = self.get_usb_ports()
        usb_dropdown = ft.Dropdown(
            label="Select USB Device",
            options=[ft.dropdown.Option(device) for device in usb_devices],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def disable_specific_usb(e):
            if usb_dropdown.value:
                self.toggle_usb("disable", usb_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a USB device.", "red")

        def enable_specific_usb(e):
            if usb_dropdown.value:
                self.toggle_usb("enable", usb_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a USB device.", "red")

        def disable_all_usb(e):
            self.toggle_usb("disable")

        def enable_all_usb(e):
            self.toggle_usb("enable")

        return ft.Container(
            content=ft.Column([
                ft.Text("USB Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Row([usb_dropdown]),
                ft.Row([
                    ft.ElevatedButton("Disable Selected", on_click=disable_specific_usb, bgcolor="red", color="white"),
                    ft.ElevatedButton("Enable Selected", on_click=enable_specific_usb, bgcolor="green", color="white"),
                ]),
                ft.Row([
                    ft.ElevatedButton("Disable All USB", on_click=disable_all_usb, bgcolor="red", color="white"),
                    ft.ElevatedButton("Enable All USB", on_click=enable_all_usb, bgcolor="green", color="white"),
                ]),
            ]),
            bgcolor=self.glass_bgcolor,  # Semi-transparent background
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # CAMERA FUNCTIONALITY
    # ----------------------
    def enable_camera(self, e):
        """Enable the integrated camera."""
        command = 'Get-PnpDevice -Class Camera | Enable-PnpDevice -Confirm:$false'
        try:
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
            if result.returncode == 0:
                self.add_to_log("✅ Enabled Integrated Camera", "green")
            else:
                error_message = result.stderr.strip() if result.stderr else "No error message available"
                self.add_to_log(f"❌ Error Enabling Camera: {error_message}", "red")
        except Exception as e:
            self.add_to_log(f"❌ Unexpected Error: {str(e)}", "red")

    def disable_camera(self, e):
        """Disable the integrated camera."""
        command = 'Get-PnpDevice -Class Camera | Disable-PnpDevice -Confirm:$false'
        try:
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
            if result.returncode == 0:
                self.add_to_log("❌ Disabled Integrated Camera", "red")
            else:
                error_message = result.stderr.strip() if result.stderr else "No error message available"
                self.add_to_log(f"❌ Error Disabling Camera: {error_message}", "red")
        except Exception as e:
            self.add_to_log(f"❌ Unexpected Error: {str(e)}", "red")

    def create_camera_section(self) -> ft.Container:
        """Camera control UI."""
        return ft.Container(
            content=ft.Column([
                ft.Text("Camera Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Row([
                    ft.ElevatedButton(
                        text="Enable Integrated Camera",
                        on_click=self.enable_camera,
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                    ),
                    ft.ElevatedButton(
                        text="Disable Integrated Camera",
                        on_click=self.disable_camera,
                        bgcolor=ft.Colors.RED,
                        color=ft.Colors.WHITE,
                    ),
                ]),
            ]),
            bgcolor=self.glass_bgcolor,  # Semi-transparent background
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # MICROPHONE FUNCTIONALITY
    # ----------------------
    def get_microphone_device(self):
        """Get the microphone device (Windows with PyCaw)."""
        try:
            devices = AudioUtilities.GetSpeakers()  # PyCaw doesn't have a direct 'GetMicrophone' function
            return devices
        except Exception as e:
            self.add_to_log(f"❌ Error accessing microphone: {str(e)}", "red")
            return None

    def set_microphone_mute(self, mute: bool):
        """Mute or unmute the microphone."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control microphone.", "red")
            return False

        action = "Disable" if mute else "Enable"
        cmd = f'Get-PnpDevice -Class AudioEndpoint | Where-Object {{ $_.FriendlyName -like "*Microphone*" }} | {action}-PnpDevice -Confirm:$false'
        self.run_powershell_command(cmd)
        status = "disabled" if mute else "enabled"
        self.add_to_log(f"✅ Microphone {status} successfully.", "green")
        return True

    def is_microphone_muted(self) -> bool:
        """Check if the microphone is muted."""
        return False  # Placeholder implementation

    def create_microphone_section(self) -> ft.Container:
        """Microphone control UI."""
        mic_state = self.is_microphone_muted()  # False = not muted

        mic_toggle = ft.Switch(
            value=not mic_state,  # True means mic is 'on'
            active_color=self.accent_color,
            scale=1.2,
        )

        def toggle_microphone(e):
            new_mute_state = not e.control.value  # True means we want to mute
            success = self.set_microphone_mute(new_mute_state)
            if not success:
                # Revert if operation failed
                e.control.value = not e.control.value
            e.control.update()

        mic_toggle.on_change = toggle_microphone

        mic_status_text = ft.Text(
            "Enabled" if not mic_state else "Disabled",
            color="green" if not mic_state else "red",
            size=14,
            weight=ft.FontWeight.W_500
        )

        return ft.Container(
            content=ft.Column([
                ft.Text("Microphone Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=10),
                ft.Row([
                    ft.Icon(ft.icons.MIC, color=self.text_color, size=24),
                    ft.Text("Microphone Status:", color=self.text_color, size=14),
                    mic_status_text,
                ]),
                ft.Container(height=10),
                ft.Row([
                    ft.Text("Microphone: ", color=self.text_color),
                    mic_toggle,
                    ft.Text("ON" if not mic_state else "OFF", color="green" if not mic_state else "red"),
                ]),
            ]),
            bgcolor=self.glass_bgcolor,  # Semi-transparent background
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
            width=350,
        )

    # ----------------------
    # BLUETOOTH FUNCTIONALITY
    # ----------------------
    def get_bluetooth_devices(self):
        """Retrieve Bluetooth devices (Windows)."""
        command = 'Get-WmiObject Win32_PnPEntity | Where-Object { $_.PNPClass -eq "Bluetooth" } | Select-Object Caption'
        output = self.run_powershell_command(command)
        if "❌" in output:
            return []
        bt_devices = [line.strip() for line in output.splitlines() if line.strip() and "Caption" not in line]
        return bt_devices

    def identify_device_type(self, device_name: str) -> str:
        """Classify device into categories (rough heuristic)."""
        command = f'Get-WmiObject Win32_PnPEntity | Where-Object {{ $_.Caption -eq "{device_name}" }} | Select-Object PNPClass, Description, DeviceID'
        output = self.run_powershell_command(command).lower()

        if "headphone" in output or "headset" in output or "earbuds" in device_name.lower():
            return "Headphones"
        elif "speaker" in output or "a2dp" in output:
            return "Speakers"
        elif "mouse" in output or "hid" in output:
            return "Mouse"
        elif "keyboard" in output:
            return "Keyboard"
        elif "game" in output or "controller" in output:
            return "Game Controller"
        elif "printer" in output:
            return "Printer"
        elif "phone" in output or "rfcomm" in output:
            return "Mobile Device"
        elif "network" in output or "adapter" in output:
            return "Network Device"
        elif "storage" in output or "usb" in output:
            return "Storage Device"
        return "Unknown"

    def enable_bluetooth(self, device_name=None):
        """Enable Bluetooth devices."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control Bluetooth.", "red")
            return

        if device_name:
            cmd = f'Get-PnpDevice | Where-Object {{ $_.FriendlyName -eq "{device_name}" }} | Enable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd)
            self.add_to_log(f"✅ Bluetooth device {device_name} enabled.", "green")
        else:
            cmd = 'Start-Service bthserv; Get-PnpDevice | Where-Object { $_.Class -eq "Bluetooth" } | Enable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd)
            self.add_to_log("✅ All Bluetooth devices enabled.", "green")

    def disable_bluetooth(self, device_name=None):
        """Disable Bluetooth devices."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control Bluetooth.", "red")
            return

        if device_name:
            cmd = f'Get-PnpDevice | Where-Object {{ $_.FriendlyName -eq "{device_name}" }} | Disable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd)
            self.add_to_log(f"🚫 Bluetooth device {device_name} disabled.", "blue")
        else:
            cmd = 'Get-PnpDevice | Where-Object { $_.Class -eq "Bluetooth" } | Disable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd)
            self.add_to_log("🚫 All Bluetooth devices disabled.", "blue")

    def create_bluetooth_section(self) -> ft.Container:
        """Bluetooth control UI."""
        bt_devices = self.get_bluetooth_devices()
        bt_dropdown = ft.Dropdown(
            label="Select Bluetooth Device",
            options=[ft.dropdown.Option(bt) for bt in bt_devices] if bt_devices else [ft.dropdown.Option("⚠️ No Bluetooth Devices Found")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        device_types = []
        if bt_devices:
            for device in bt_devices:
                dt = self.identify_device_type(device)
                if dt not in device_types:
                    device_types.append(dt)

        type_dropdown = ft.Dropdown(
            label="Select Device Type",
            options=[ft.dropdown.Option(dt) for dt in device_types] if device_types else [ft.dropdown.Option("⚠️ No Device Types Found")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def disable_selected_bt(e):
            if bt_dropdown.value and "⚠️" not in bt_dropdown.value:
                self.disable_bluetooth(bt_dropdown.value)
            else:
                self.add_to_log("⚠️ Select a valid Bluetooth device.", "red")

        def enable_selected_bt(e):
            if bt_dropdown.value and "⚠️" not in bt_dropdown.value:
                self.enable_bluetooth(bt_dropdown.value)
            else:
                self.add_to_log("⚠️ Select a valid Bluetooth device.", "red")

        def disable_all_bt(e):
            self.disable_bluetooth()

        def enable_all_bt(e):
            self.enable_bluetooth()

        def disable_by_type(e):
            if type_dropdown.value and "⚠️" not in type_dropdown.value:
                for device in bt_devices:
                    if self.identify_device_type(device) == type_dropdown.value:
                        self.disable_bluetooth(device)
            else:
                self.add_to_log("⚠️ Select a valid device type.", "red")

        def enable_by_type(e):
            if type_dropdown.value and "⚠️" not in type_dropdown.value:
                for device in bt_devices:
                    if self.identify_device_type(device) == type_dropdown.value:
                        self.enable_bluetooth(device)
            else:
                self.add_to_log("⚠️ Select a valid device type.", "red")

        return ft.Container(
            content=ft.Column([
                ft.Text("Bluetooth Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=10),
                ft.Row([bt_dropdown]),
                ft.Row([
                    ft.ElevatedButton("Disable Selected", on_click=disable_selected_bt, bgcolor="red", color="white"),
                    ft.ElevatedButton("Enable Selected", on_click=enable_selected_bt, bgcolor="green", color="white"),
                ]),
                ft.Container(height=5),
                ft.Row([
                    ft.ElevatedButton("Disable All Bluetooth", on_click=disable_all_bt, bgcolor="red", color="white"),
                    ft.ElevatedButton("Enable All Bluetooth", on_click=enable_all_bt, bgcolor="green", color="white"),
                ]),
                ft.Container(height=20),
                ft.Text("Control by Device Type", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=5),
                ft.Row([type_dropdown]),
                ft.Row([
                    ft.ElevatedButton("Disable by Type", on_click=disable_by_type, bgcolor="blue", color="white"),
                    ft.ElevatedButton("Enable by Type", on_click=enable_by_type, bgcolor="purple", color="white"),
                ]),
            ]),
            bgcolor=self.glass_bgcolor,  # Semi-transparent background
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # WIFI FUNCTIONALITY
    # ----------------------
    def get_available_wifi_networks(self):
        """List available Wi-Fi networks (Windows)."""
        try:
            command = 'netsh wlan show networks mode=bssid'
            output = subprocess.check_output(command, shell=True, encoding='utf-8')
            ssid_list = []
            for line in output.splitlines():
                if "SSID" in line and ":" in line:
                    ssid = line.split(":")[1].strip()
                    if ssid and ssid not in ssid_list:
                        ssid_list.append(ssid)
            return ssid_list
        except subprocess.CalledProcessError:
            self.add_to_log("❌ Error retrieving Wi-Fi networks.", "red")
            return []

    def enable_wifi(self):
        """Enable Wi-Fi."""
        try:
            command = 'netsh interface set interface "Wi-Fi" admin=enable'
            subprocess.run(command, shell=True)
            self.add_to_log("✅ Wi-Fi enabled successfully.", "green")
        except Exception as e:
            self.add_to_log(f"❌ Error enabling Wi-Fi: {str(e)}", "red")

    def disable_wifi(self):
        """Disable Wi-Fi."""
        try:
            command = 'netsh interface set interface "Wi-Fi" admin=disable'
            subprocess.run(command, shell=True)
            self.add_to_log("✅ Wi-Fi disabled successfully.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error disabling Wi-Fi: {str(e)}", "red")

    def block_wifi_network(self, ssid):
        """Block a specific Wi-Fi network."""
        try:
            command = f'netsh wlan add filter permission=block ssid="{ssid}" networktype=infrastructure'
            subprocess.run(command, shell=True)
            self.add_to_log(f"🚫 Blocked Wi-Fi network: {ssid}", "blue")
        except Exception as e:
            self.add_to_log(f"❌ Error blocking Wi-Fi network: {str(e)}", "red")

    def unblock_wifi_network(self, ssid):
        """Unblock a specific Wi-Fi network."""
        try:
            command = f'netsh wlan delete filter permission=block ssid="{ssid}" networktype=infrastructure'
            subprocess.run(command, shell=True)
            self.add_to_log(f"✅ Unblocked Wi-Fi network: {ssid}", "green")
        except Exception as e:
            self.add_to_log(f"❌ Error unblocking Wi-Fi network: {str(e)}", "red")

    def get_wifi_status(self):
        """Get current Wi-Fi status."""
        try:
            command = 'netsh interface show interface name="Wi-Fi"'
            output = subprocess.check_output(command, shell=True, encoding='utf-8')
            if "Enabled" in output:
                return "Enabled"
            elif "Disabled" in output:
                return "Disabled"
            else:
                return "Unknown"
        except Exception:
            return "Unknown"

    def get_connected_wifi(self):
        """Get currently connected Wi-Fi network."""
        try:
            command = 'netsh wlan show interfaces'
            output = subprocess.check_output(command, shell=True, encoding='utf-8')
            for line in output.splitlines():
                if "SSID" in line and ":" in line and "BSSID" not in line:
                    ssid = line.split(":")[1].strip()
                    if ssid:
                        return ssid
            return None
        except Exception:
            return None

    def disconnect_wifi(self):
        """Disconnect from current Wi-Fi network."""
        try:
            command = 'netsh wlan disconnect'
            subprocess.run(command, shell=True)
            self.add_to_log("✅ Disconnected from Wi-Fi network.", "blue")
        except Exception as e:
            self.add_to_log(f"❌ Error disconnecting from Wi-Fi: {str(e)}", "red")

    def connect_wifi(self, ssid):
        """Connect to a specific Wi-Fi network."""
        try:
            command = f'netsh wlan connect name="{ssid}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if "Connection request was completed successfully" in result.stdout:
                self.add_to_log(f"✅ Connected to {ssid} successfully.", "green")
            else:
                self.add_to_log(f"⚠️ Could not connect to {ssid}. {result.stdout}", "orange")
        except Exception as e:
            self.add_to_log(f"❌ Error connecting to Wi-Fi: {str(e)}", "red")

    def create_wifi_section(self) -> ft.Container:
        """Wi-Fi control UI."""
        wifi_networks = self.get_available_wifi_networks()
        wifi_status = self.get_wifi_status()
        current_network = self.get_connected_wifi() or "Not connected"

        status_text = ft.Text(
            f"Status: {wifi_status}",
            color="green" if wifi_status == "Enabled" else "red",
            weight=ft.FontWeight.BOLD
        )
        connected_text = ft.Text(f"Connected to: {current_network}", color=self.text_color)

        ssid_dropdown = ft.Dropdown(
            label="Select Wi-Fi Network",
            options=[ft.dropdown.Option(ssid) for ssid in wifi_networks] if wifi_networks else [ft.dropdown.Option("⚠️ No Wi-Fi Networks Found")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def refresh_networks(e):
            new_networks = self.get_available_wifi_networks()
            ssid_dropdown.options = [ft.dropdown.Option(nw) for nw in new_networks] if new_networks else [ft.dropdown.Option("⚠️ No Wi-Fi Networks Found")]
            new_status = self.get_wifi_status()
            new_current_network = self.get_connected_wifi() or "Not connected"
            status_text.value = f"Status: {new_status}"
            status_text.color = "green" if new_status == "Enabled" else "red"
            connected_text.value = f"Connected to: {new_current_network}"
            self.add_to_log("🔄 Refreshed Wi-Fi networks list.", "blue")
            e.page.update()

        def disable_wifi_click(e):
            self.disable_wifi()
            status_text.value = "Status: Disabled"
            status_text.color = "red"
            e.page.update()

        def enable_wifi_click(e):
            self.enable_wifi()
            status_text.value = "Status: Enabled"
            status_text.color = "green"
            e.page.update()

        def connect_wifi_click(e):
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value:
                self.connect_wifi(ssid_dropdown.value)
                time.sleep(2)
                new_current = self.get_connected_wifi() or "Not connected"
                connected_text.value = f"Connected to: {new_current}"
                e.page.update()
            else:
                self.add_to_log("⚠️ Please select a valid Wi-Fi network.", "red")

        def disconnect_wifi_click(e):
            self.disconnect_wifi()
            connected_text.value = "Connected to: Not connected"
            e.page.update()

        def block_ssid_click(e):
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value:
                self.block_wifi_network(ssid_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a valid Wi-Fi network.", "red")

        def unblock_ssid_click(e):
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value:
                self.unblock_wifi_network(ssid_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a valid Wi-Fi network.", "red")

        refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color=self.text_color,
            tooltip="Refresh Networks",
            on_click=refresh_networks
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Wi-Fi Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    refresh_button,
                ]),
                ft.Divider(color="#333333"),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Network Status", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                        status_text,
                        connected_text,
                    ]),
                    padding=10,
                    border=ft.border.all(1, "#333333"),
                    border_radius=5,
                    margin=ft.margin.only(bottom=15)
                ),
                ft.Text("Wi-Fi Power Controls", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Row([
                    ft.ElevatedButton("Turn Off Wi-Fi", on_click=disable_wifi_click, bgcolor="red", color="white"),
                    ft.ElevatedButton("Turn On Wi-Fi", on_click=enable_wifi_click, bgcolor="green", color="white"),
                ]),
                ft.Divider(color="#333333"),
                ft.Text("Network Management", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=10),
                ft.Row([ssid_dropdown]),
                ft.Row([
                    ft.ElevatedButton("Connect", on_click=connect_wifi_click, bgcolor="green", color="white"),
                    ft.ElevatedButton("Disconnect", on_click=disconnect_wifi_click, bgcolor="blue", color="white"),
                ]),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton("Block Network", on_click=block_ssid_click, bgcolor="orange", color="white"),
                    ft.ElevatedButton("Unblock Network", on_click=unblock_ssid_click, bgcolor="purple", color="white"),
                ]),
            ]),
            bgcolor=self.glass_bgcolor,  # Semi-transparent background
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # BUILD DEVICE MANAGER UI
    # ----------------------
    def create_device_panel(self) -> ft.Column:
        """
        Return a Column with all device controls:
        Camera, Microphone, Wi-Fi, USB, Bluetooth
        """
        return ft.Column(
            controls=[
                # Camera + Microphone
                ft.Row(
                    controls=[
                        self.create_camera_section(),
                        self.create_microphone_section(),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                # Wi-Fi
                self.create_wifi_section(),
                # USB
                self.create_usb_section(),
                # Bluetooth
                self.create_bluetooth_section(),
            ],
            scroll=ft.ScrollMode.AUTO,
        )

    def build(self) -> ft.Container:
        """
        Build and return the main container for the device manager UI,
        including a right-side log panel.
        """
        # Device manager panel - with more transparent background
        device_panel = ft.Container(
            expand=2,
            bgcolor=self.glass_bgcolor,  # Using the semi-transparent glass color
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=15,
            margin=ft.margin.only(left=10, right=10, top=2, bottom=10),
            padding=20,
            content=self.create_device_panel()
        )

        # Log panel - with more transparent background
        log_panel = ft.Container(
            expand=1,
            bgcolor=self.glass_bgcolor,  # Using the semi-transparent glass color
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=15,
            margin=ft.margin.only(right=10, top=2, bottom=10),
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Device Action Log",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=self.text_color
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.icons.DELETE_SWEEP,
                                icon_color=self.text_color,
                                tooltip="Clear Logs",
                                on_click=lambda e: self.clear_logs(),
                            ),
                        ],
                    ),
                    ft.Container(
                        content=self.log_column,
                        expand=True,
                        border=ft.border.all(1, "#333333"),
                        border_radius=5,
                        padding=10,
                        margin=ft.margin.only(top=10),
                    )
                ],
            ),
        )

        # The final layout is a Row with device_panel + log_panel
        final_layout = ft.Row(
            controls=[device_panel, log_panel],
            spacing=0,
            expand=True
        )

        # Return the layout wrapped in a transparent container
        container = ft.Container(
            content=final_layout,
            expand=True,
            bgcolor="transparent"  # Using transparent background to match other tabs
        )

        # After building, display any stored log messages
        self.display_stored_log_messages()

        # Return the container to be placed in integrated code
        return container