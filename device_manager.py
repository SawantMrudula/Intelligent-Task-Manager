import flet as ft
import os
import subprocess
import threading
import time
import re
from functools import lru_cache

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
        
        # Cache for device lookups
        self.device_cache = {}
        self.cache_timestamp = 0
        self.CACHE_LIFETIME = 60  # Cache lifetime in seconds

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

    @lru_cache(maxsize=32)
    def run_powershell_command(self, command: str, use_cache=True) -> str:
        """Run a PowerShell command and return its output (Windows only)."""
        if not os.path.exists(self.POWERSHELL_PATH):
            return "❌ PowerShell is not available."

        cache_key = f"ps_{command}"
        current_time = time.time()
        
        # Check if we can use cache
        if use_cache and cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        try:
            output = subprocess.check_output(
                [self.POWERSHELL_PATH, "-Command", command],
                encoding="utf-8",
                stderr=subprocess.STDOUT,
                timeout=5  # Add timeout to prevent hanging
            )
            result = output.strip()
            
            # Cache result if needed
            if use_cache:
                self.device_cache[cache_key] = result
                self.cache_timestamp = current_time
                
            return result
        except subprocess.CalledProcessError as e:
            return f"❌ Error: {e.output.strip()}"
        except subprocess.TimeoutExpired:
            return "❌ Command timed out"

    def is_admin(self) -> bool:
        """Check if script is running with administrator privileges (Windows)."""
        if "is_admin" in self.device_cache and time.time() - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache["is_admin"]
            
        command = '[bool](([System.Security.Principal.WindowsIdentity]::GetCurrent()).Groups -match "S-1-5-32-544")'
        output = self.run_powershell_command(command)
        result = "True" in output
        
        self.device_cache["is_admin"] = result
        return result

    # ----------------------
    # USB FUNCTIONALITY - Optimized with caching
    # ----------------------
    def get_usb_ports(self):
        """Get all USB devices (Windows) with caching."""
        cache_key = "usb_ports"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        command = 'pnputil /enum-devices /class "USB" | findstr /i /C:"USB\\"'
        try:
            output = subprocess.check_output(command, shell=True, encoding='utf-8', timeout=5)
            usb_devices = []
            for line in output.splitlines():
                if "USB\\" in line:
                    device_id = line.split(":")[-1].strip()
                    usb_devices.append(device_id)
                    
            # Cache the result
            self.device_cache[cache_key] = usb_devices
            self.cache_timestamp = current_time
            return usb_devices
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
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
        
        # Clear cache since device state changed
        if "usb_ports" in self.device_cache:
            del self.device_cache["usb_ports"]

    def create_usb_section(self) -> ft.Container:
        """USB control UI - Lazy loaded."""
        # Create empty dropdown that will be populated on demand
        usb_dropdown = ft.Dropdown(
            label="Select USB Device",
            options=[ft.dropdown.Option("Click 'Refresh' to load devices")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def refresh_usb_devices(e):
            devices = self.get_usb_ports()
            if devices:
                usb_dropdown.options = [ft.dropdown.Option(device) for device in devices]
            else:
                usb_dropdown.options = [ft.dropdown.Option("No USB devices found")]
            usb_dropdown.update()
            self.add_to_log("USB device list refreshed", "blue")

        def disable_specific_usb(e):
            if usb_dropdown.value and "No USB" not in usb_dropdown.value and "Click" not in usb_dropdown.value:
                self.toggle_usb("disable", usb_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a USB device.", "red")

        def enable_specific_usb(e):
            if usb_dropdown.value and "No USB" not in usb_dropdown.value and "Click" not in usb_dropdown.value:
                self.toggle_usb("enable", usb_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a USB device.", "red")

        def disable_all_usb(e):
            self.toggle_usb("disable")

        def enable_all_usb(e):
            self.toggle_usb("enable")

        refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color=self.text_color,
            tooltip="Refresh USB Devices",
            on_click=refresh_usb_devices
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("USB Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    refresh_button
                ]),
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
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # CAMERA FUNCTIONALITY - Optimized
    # ----------------------
    def enable_camera(self, e):
        """Enable the integrated camera."""
        command = 'Get-PnpDevice -Class Camera | Enable-PnpDevice -Confirm:$false'
        try:
            result = subprocess.run(["powershell", "-Command", command], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.add_to_log("✅ Enabled Integrated Camera", "green")
                
                # Clear camera status cache
                if "camera_enabled" in self.device_cache:
                    del self.device_cache["camera_enabled"]
                    
                # Update UI if we can find the control
                if e and e.page:
                    for control in e.page.controls:
                        if hasattr(control, 'content') and isinstance(control.content, ft.Row):
                            # Try to find the camera status text
                            for row_control in control.content.controls:
                                if hasattr(row_control, 'content') and isinstance(row_control.content, ft.Column):
                                    for col_item in row_control.content.controls:
                                        if isinstance(col_item, ft.Row) and len(col_item.controls) > 2:
                                            if isinstance(col_item.controls[0], ft.Icon) and col_item.controls[0].icon == ft.icons.CAMERA_ALT:
                                                status_text = col_item.controls[2]
                                                status_text.value = "Enabled"
                                                status_text.color = "green"
                                                status_text.update()
            else:
                error_message = result.stderr.strip() if result.stderr else "No error message available"
                self.add_to_log(f"❌ Error Enabling Camera: {error_message}", "red")
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while enabling camera", "red")
        except Exception as e:
            self.add_to_log(f"❌ Unexpected Error: {str(e)}", "red")

    def disable_camera(self, e):
        """Disable the integrated camera."""
        command = 'Get-PnpDevice -Class Camera | Disable-PnpDevice -Confirm:$false'
        try:
            result = subprocess.run(["powershell", "-Command", command], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.add_to_log("❌ Disabled Integrated Camera", "red")
                
                # Clear camera status cache
                if "camera_enabled" in self.device_cache:
                    del self.device_cache["camera_enabled"]
                    
                # Update UI if we can find the control
                if e and e.page:
                    for control in e.page.controls:
                        if hasattr(control, 'content') and isinstance(control.content, ft.Row):
                            # Try to find the camera status text
                            for row_control in control.content.controls:
                                if hasattr(row_control, 'content') and isinstance(row_control.content, ft.Column):
                                    for col_item in row_control.content.controls:
                                        if isinstance(col_item, ft.Row) and len(col_item.controls) > 2:
                                            if isinstance(col_item.controls[0], ft.Icon) and col_item.controls[0].icon == ft.icons.CAMERA_ALT:
                                                status_text = col_item.controls[2]
                                                status_text.value = "Disabled"
                                                status_text.color = "red"
                                                status_text.update()
            else:
                error_message = result.stderr.strip() if result.stderr else "No error message available"
                self.add_to_log(f"❌ Error Disabling Camera: {error_message}", "red")
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while disabling camera", "red")
        except Exception as e:
            self.add_to_log(f"❌ Unexpected Error: {str(e)}", "red")

    def get_camera_status(self) -> bool:
        """Check if the camera is enabled or disabled."""
        cache_key = "camera_enabled"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        # Default to assuming camera is enabled
        camera_enabled = True
        
        try:
            # Simple check based on presence of disabled cameras
            cmd = 'Get-PnpDevice -Class Camera | Where-Object { $_.Status -eq "Disabled" } | Measure-Object | Select-Object -ExpandProperty Count'
            output = self.run_powershell_command(cmd)
            count = int(output.strip()) if output.strip().isdigit() else 0
            camera_enabled = count == 0
            
            self.device_cache[cache_key] = camera_enabled
            self.cache_timestamp = current_time
        except:
            pass
            
        return camera_enabled

    def create_camera_section(self) -> ft.Container:
        """Camera control UI with status icon."""
        camera_state = self.get_camera_status()  # True = enabled

        camera_status_text = ft.Text(
            "Enabled" if camera_state else "Disabled",
            color="green" if camera_state else "red",
            size=14,
            weight=ft.FontWeight.W_500
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Camera Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=10),
                ft.Row([
                    ft.Icon(ft.icons.CAMERA_ALT, color=self.text_color, size=24),
                    ft.Text("Camera Status:", color=self.text_color, size=14),
                    camera_status_text,
                ]),
                ft.Container(height=10),
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
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
            width=450,  # Increased width to better fit the buttons
        )

    # ----------------------
    # MICROPHONE FUNCTIONALITY - Optimized
    # ----------------------
    def get_microphone_device(self):
        """Get the microphone device (Windows with PyCaw)."""
        cache_key = "mic_device"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        try:
            devices = AudioUtilities.GetSpeakers()
            self.device_cache[cache_key] = devices
            self.cache_timestamp = current_time
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
        self.run_powershell_command(cmd, use_cache=False)
        status = "disabled" if mute else "enabled"
        self.add_to_log(f"✅ Microphone {status} successfully.", "green")
        
        # Clear mic device cache since state changed
        if "mic_device" in self.device_cache:
            del self.device_cache["mic_device"]
            
        return True

    def is_microphone_muted(self) -> bool:
        """Check if the microphone is muted."""
        cache_key = "mic_muted"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        # Default to assuming not muted
        muted = False
        
        # This is a placeholder implementation - proper implementation would need to
        # interact with the Windows audio API to determine actual mute state
        try:
            # Simple check based on presence of disabled microphones
            cmd = 'Get-PnpDevice -Class AudioEndpoint | Where-Object { $_.Status -eq "Disabled" -and $_.FriendlyName -like "*Microphone*" } | Measure-Object | Select-Object -ExpandProperty Count'
            output = self.run_powershell_command(cmd)
            count = int(output.strip()) if output.strip().isdigit() else 0
            muted = count > 0
            
            self.device_cache[cache_key] = muted
            self.cache_timestamp = current_time
        except:
            pass
            
        return muted

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
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
            width=350,
        )

    # ----------------------
    # BLUETOOTH FUNCTIONALITY - Optimized with caching
    # ----------------------
    def get_bluetooth_devices(self):
        """Retrieve Bluetooth devices (Windows) with caching."""
        cache_key = "bt_devices"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        command = 'Get-WmiObject Win32_PnPEntity | Where-Object { $_.PNPClass -eq "Bluetooth" } | Select-Object Caption'
        output = self.run_powershell_command(command, use_cache=False)
        if "❌" in output:
            return []
        
        bt_devices = [line.strip() for line in output.splitlines() if line.strip() and "Caption" not in line]
        
        # Cache the result
        self.device_cache[cache_key] = bt_devices
        self.cache_timestamp = current_time
        
        return bt_devices

    def identify_device_type(self, device_name: str) -> str:
        """Classify device into categories (rough heuristic) with caching."""
        cache_key = f"dev_type_{device_name}"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        # Use regex patterns for faster identification instead of another PowerShell call
        result = "Unknown"
        device_name_lower = device_name.lower()
        
        if "headphone" in device_name_lower or "headset" in device_name_lower or "earbuds" in device_name_lower:
            result = "Headphones"
        elif "speaker" in device_name_lower or "a2dp" in device_name_lower:
            result = "Speakers"
        elif "mouse" in device_name_lower:
            result = "Mouse"
        elif "keyboard" in device_name_lower:
            result = "Keyboard"
        elif "game" in device_name_lower or "controller" in device_name_lower:
            result = "Game Controller"
        elif "printer" in device_name_lower:
            result = "Printer"
        elif "phone" in device_name_lower:
            result = "Mobile Device"
        elif "network" in device_name_lower or "adapter" in device_name_lower:
            result = "Network Device"
        elif "storage" in device_name_lower:
            result = "Storage Device"
            
        # Cache the result
        self.device_cache[cache_key] = result
        self.cache_timestamp = current_time
        
        return result

    def enable_bluetooth(self, device_name=None):
        """Enable Bluetooth devices."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control Bluetooth.", "red")
            return

        if device_name:
            cmd = f'Get-PnpDevice | Where-Object {{ $_.FriendlyName -eq "{device_name}" }} | Enable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd, use_cache=False)
            self.add_to_log(f"✅ Bluetooth device {device_name} enabled.", "green")
        else:
            cmd = 'Start-Service bthserv; Get-PnpDevice | Where-Object { $_.Class -eq "Bluetooth" } | Enable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd, use_cache=False)
            self.add_to_log("✅ All Bluetooth devices enabled.", "green")
            
        # Clear BT cache since state changed
        if "bt_devices" in self.device_cache:
            del self.device_cache["bt_devices"]

    def disable_bluetooth(self, device_name=None):
        """Disable Bluetooth devices."""
        if not self.is_admin():
            self.add_to_log("❌ Run as Administrator to control Bluetooth.", "red")
            return

        if device_name:
            cmd = f'Get-PnpDevice | Where-Object {{ $_.FriendlyName -eq "{device_name}" }} | Disable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd, use_cache=False)
            self.add_to_log(f"🚫 Bluetooth device {device_name} disabled.", "blue")
        else:
            cmd = 'Get-PnpDevice | Where-Object { $_.Class -eq "Bluetooth" } | Disable-PnpDevice -Confirm:$false'
            self.run_powershell_command(cmd, use_cache=False)
            self.add_to_log("🚫 All Bluetooth devices disabled.", "blue")
            
        # Clear BT cache since state changed
        if "bt_devices" in self.device_cache:
            del self.device_cache["bt_devices"]

    def create_bluetooth_section(self) -> ft.Container:
        """Bluetooth control UI with lazy-loading."""
        # Create empty dropdowns that will be populated on demand
        bt_dropdown = ft.Dropdown(
            label="Select Bluetooth Device",
            options=[ft.dropdown.Option("Click 'Refresh' to load devices")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        type_dropdown = ft.Dropdown(
            label="Select Device Type",
            options=[ft.dropdown.Option("Device types will load after refresh")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def refresh_bt_devices(e):
            # Load bluetooth devices on demand
            bt_devices = self.get_bluetooth_devices()
            device_types = []
            
            if bt_devices:
                bt_dropdown.options = [ft.dropdown.Option(bt) for bt in bt_devices]
                
                # Identify device types
                for device in bt_devices:
                    dt = self.identify_device_type(device)
                    if dt not in device_types:
                        device_types.append(dt)
                
                if device_types:
                    type_dropdown.options = [ft.dropdown.Option(dt) for dt in device_types]
                else:
                    type_dropdown.options = [ft.dropdown.Option("No device types found")]
            else:
                bt_dropdown.options = [ft.dropdown.Option("No Bluetooth devices found")]
                type_dropdown.options = [ft.dropdown.Option("No device types available")]
                
            bt_dropdown.update()
            type_dropdown.update()
            self.add_to_log("🔄 Bluetooth device list refreshed", "blue")

        def disable_selected_bt(e):
            if bt_dropdown.value and "⚠️" not in bt_dropdown.value and "Click" not in bt_dropdown.value:
                self.disable_bluetooth(bt_dropdown.value)
            else:
                self.add_to_log("⚠️ Select a valid Bluetooth device.", "red")

        def enable_selected_bt(e):
            if bt_dropdown.value and "⚠️" not in bt_dropdown.value and "Click" not in bt_dropdown.value:
                self.enable_bluetooth(bt_dropdown.value)
            else:
                self.add_to_log("⚠️ Select a valid Bluetooth device.", "red")

        def disable_all_bt(e):
            self.disable_bluetooth()

        def enable_all_bt(e):
            self.enable_bluetooth()

        def disable_by_type(e):
            if type_dropdown.value and "⚠️" not in type_dropdown.value and "Device types" not in type_dropdown.value:
                bt_devices = self.get_bluetooth_devices()
                for device in bt_devices:
                    if self.identify_device_type(device) == type_dropdown.value:
                        self.disable_bluetooth(device)
            else:
                self.add_to_log("⚠️ Select a valid device type.", "red")

        def enable_by_type(e):
            if type_dropdown.value and "⚠️" not in type_dropdown.value and "Device types" not in type_dropdown.value:
                bt_devices = self.get_bluetooth_devices()
                for device in bt_devices:
                    if self.identify_device_type(device) == type_dropdown.value:
                        self.enable_bluetooth(device)
            else:
                self.add_to_log("⚠️ Select a valid device type.", "red")

        refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color=self.text_color,
            tooltip="Refresh Bluetooth Devices",
            on_click=refresh_bt_devices
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Bluetooth Control", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    refresh_button
                ]),
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
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=15),
        )

    # ----------------------
    # WIFI FUNCTIONALITY - Optimized
    # ----------------------
    def get_available_wifi_networks(self):
        """List available Wi-Fi networks (Windows) with caching."""
        cache_key = "wifi_networks"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        try:
            command = 'netsh wlan show networks mode=bssid'
            output = subprocess.check_output(command, shell=True, encoding='utf-8', timeout=5)
            ssid_list = []
            for line in output.splitlines():
                if "SSID" in line and ":" in line:
                    ssid = line.split(":")[1].strip()
                    if ssid and ssid not in ssid_list:
                        ssid_list.append(ssid)
            
            # Cache the result
            self.device_cache[cache_key] = ssid_list
            self.cache_timestamp = current_time
            
            return ssid_list
        except subprocess.CalledProcessError:
            self.add_to_log("❌ Error retrieving Wi-Fi networks.", "red")
            return []
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out retrieving Wi-Fi networks.", "red")
            return []
            
    def enable_wifi(self):
        """Enable Wi-Fi."""
        try:
            command = 'netsh interface set interface "Wi-Fi" admin=enable'
            subprocess.run(command, shell=True, timeout=5)
            self.add_to_log("✅ Wi-Fi enabled successfully.", "green")
            
            # Clear Wi-Fi cache
            if "wifi_networks" in self.device_cache:
                del self.device_cache["wifi_networks"]
            if "wifi_status" in self.device_cache:
                del self.device_cache["wifi_status"]
                
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while enabling Wi-Fi.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error enabling Wi-Fi: {str(e)}", "red")

    def disable_wifi(self):
        """Disable Wi-Fi."""
        try:
            command = 'netsh interface set interface "Wi-Fi" admin=disable'
            subprocess.run(command, shell=True, timeout=5)
            self.add_to_log("✅ Wi-Fi disabled successfully.", "red")
            
            # Clear Wi-Fi cache
            if "wifi_networks" in self.device_cache:
                del self.device_cache["wifi_networks"]
            if "wifi_status" in self.device_cache:
                del self.device_cache["wifi_status"]
                
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while disabling Wi-Fi.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error disabling Wi-Fi: {str(e)}", "red")

    def block_wifi_network(self, ssid):
        """Block a specific Wi-Fi network."""
        try:
            command = f'netsh wlan add filter permission=block ssid="{ssid}" networktype=infrastructure'
            subprocess.run(command, shell=True, timeout=5)
            self.add_to_log(f"🚫 Blocked Wi-Fi network: {ssid}", "blue")
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while blocking Wi-Fi network.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error blocking Wi-Fi network: {str(e)}", "red")

    def unblock_wifi_network(self, ssid):
        """Unblock a specific Wi-Fi network."""
        try:
            command = f'netsh wlan delete filter permission=block ssid="{ssid}" networktype=infrastructure'
            subprocess.run(command, shell=True, timeout=5)
            self.add_to_log(f"✅ Unblocked Wi-Fi network: {ssid}", "green")
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while unblocking Wi-Fi network.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error unblocking Wi-Fi network: {str(e)}", "red")
            
    def get_wifi_status(self):
        """Get current Wi-Fi status with caching."""
        cache_key = "wifi_status"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        try:
            command = 'netsh interface show interface name="Wi-Fi"'
            output = subprocess.check_output(command, shell=True, encoding='utf-8', timeout=3)
            status = "Unknown"
            
            if "Enabled" in output:
                status = "Enabled"
            elif "Disabled" in output:
                status = "Disabled"
                
            # Cache the result
            self.device_cache[cache_key] = status
            self.cache_timestamp = current_time
            
            return status
        except Exception:
            return "Unknown"

    def get_connected_wifi(self):
        """Get currently connected Wi-Fi network with caching."""
        cache_key = "connected_wifi"
        current_time = time.time()
        
        # Return cached result if available and fresh
        if cache_key in self.device_cache and current_time - self.cache_timestamp < self.CACHE_LIFETIME:
            return self.device_cache[cache_key]
            
        try:
            command = 'netsh wlan show interfaces'
            output = subprocess.check_output(command, shell=True, encoding='utf-8', timeout=3)
            ssid = None
            
            for line in output.splitlines():
                if "SSID" in line and ":" in line and "BSSID" not in line:
                    ssid = line.split(":")[1].strip()
                    if ssid:
                        break
                        
            # Cache the result
            self.device_cache[cache_key] = ssid
            self.cache_timestamp = current_time
            
            return ssid
        except Exception:
            return None

    def disconnect_wifi(self):
        """Disconnect from current Wi-Fi network."""
        try:
            command = 'netsh wlan disconnect'
            subprocess.run(command, shell=True, timeout=3)
            self.add_to_log("✅ Disconnected from Wi-Fi network.", "blue")
            
            # Clear connected wifi cache
            if "connected_wifi" in self.device_cache:
                del self.device_cache["connected_wifi"]
                
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while disconnecting Wi-Fi.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error disconnecting from Wi-Fi: {str(e)}", "red")

    def connect_wifi(self, ssid):
        """Connect to a specific Wi-Fi network."""
        try:
            command = f'netsh wlan connect name="{ssid}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            if "Connection request was completed successfully" in result.stdout:
                self.add_to_log(f"✅ Connected to {ssid} successfully.", "green")
            else:
                self.add_to_log(f"⚠️ Could not connect to {ssid}. {result.stdout}", "orange")
                
            # Clear connected wifi cache
            if "connected_wifi" in self.device_cache:
                del self.device_cache["connected_wifi"]
                
        except subprocess.TimeoutExpired:
            self.add_to_log("❌ Command timed out while connecting to Wi-Fi.", "red")
        except Exception as e:
            self.add_to_log(f"❌ Error connecting to Wi-Fi: {str(e)}", "red")
            
    def create_wifi_section(self) -> ft.Container:
        """Wi-Fi control UI with lazy loading."""
        # Create status displays with default values
        status_text = ft.Text(
            "Status: Loading...",
            color="gray",
            weight=ft.FontWeight.BOLD
        )
        connected_text = ft.Text("Connected to: Checking...", color=self.text_color)

        # Create empty dropdown that will be populated on demand
        ssid_dropdown = ft.Dropdown(
            label="Select Wi-Fi Network",
            options=[ft.dropdown.Option("Click 'Refresh' to scan networks")],
            width=300,
            color=self.text_color,
            border_color=self.accent_color,
            focused_border_color=self.accent_color,
            focused_color=self.text_color,
        )

        def refresh_networks(e):
            # Update status first (quick operation)
            new_status = self.get_wifi_status()
            status_text.value = f"Status: {new_status}"
            status_text.color = "green" if new_status == "Enabled" else "red"
            status_text.update()
            
            # Update connected network info (quick operation)
            new_current_network = self.get_connected_wifi() or "Not connected"
            connected_text.value = f"Connected to: {new_current_network}"
            connected_text.update()
            
            # Start loading message
            ssid_dropdown.label = "Scanning Wi-Fi Networks..."
            ssid_dropdown.update()
            
            # Start network scan in background thread to prevent UI freeze
            def scan_networks_thread():
                new_networks = self.get_available_wifi_networks()
                
                # Update dropdown on main thread
                if e.page:
                    def update_dropdown():
                        ssid_dropdown.label = "Select Wi-Fi Network"
                        ssid_dropdown.options = [ft.dropdown.Option(nw) for nw in new_networks] if new_networks else [ft.dropdown.Option("⚠️ No Wi-Fi Networks Found")]
                        ssid_dropdown.update()
                        self.add_to_log(f"🔄 Found {len(new_networks)} Wi-Fi networks.", "blue")
                    
                    e.page.run_async(update_dropdown)
            
            # Start background thread
            threading.Thread(target=scan_networks_thread, daemon=True).start()

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
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value and "Click" not in ssid_dropdown.value:
                self.connect_wifi(ssid_dropdown.value)
                time.sleep(1)  # Brief delay to allow connection
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
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value and "Click" not in ssid_dropdown.value:
                self.block_wifi_network(ssid_dropdown.value)
            else:
                self.add_to_log("⚠️ Please select a valid Wi-Fi network.", "red")

        def unblock_ssid_click(e):
            if ssid_dropdown.value and "⚠️" not in ssid_dropdown.value and "Click" not in ssid_dropdown.value:
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
            bgcolor=self.glass_bgcolor,
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