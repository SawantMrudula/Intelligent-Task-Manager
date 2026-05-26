import flet as ft
from flet import BlurTileMode, Colors, BoxShadow, ShadowBlurStyle, Offset, Blur
import plotly.graph_objects as go
import psutil
import asyncio
import threading
import os
import platform
import math
import datetime
import subprocess
from typing import List, Dict, Any

# Ensure Windows-only execution
if platform.system() != "Windows":
    raise SystemExit("This application is designed to run on Windows only.")

#####################################
# 1) Periodic Task Management
#####################################
async def periodic_update(page: ft.Page, app):
    """Runs in a background thread, fetching data and updating the UI every 5 seconds."""
    while True:
        try:
            tasks = fetch_realtime_tasks()
            app.update_task_table(tasks)
            app.update_statistics_chart(tasks)
            page.update()
        except Exception as e:
            print(f"Error in periodic update: {e}")
        finally:
            await asyncio.sleep(5)

def start_realtime_updates(page: ft.Page, app):
    """
    Starts the periodic update in a separate event loop so it doesn't block the main thread.
    """
    try:
        new_loop = asyncio.new_event_loop()
        new_loop.create_task(periodic_update(page, app))
        t = threading.Thread(target=_run_loop, args=(new_loop,), daemon=True)
        t.start()
        print("Realtime updates started for Scheduled Processes (Windows)")
        return True
    except Exception as e:
        print(f"Error starting realtime updates: {e}")
        return False

def _run_loop(loop):
    try:
        asyncio.set_event_loop(loop)
        loop.run_forever()
    except Exception as e:
        print(f"Error in run loop: {e}")

def get_scheduled_tasks() -> List[Dict[str, Any]]:
    """Fetches Windows scheduled tasks information."""
    scheduled_tasks = []
    try:
        # Use schtasks command to get scheduled tasks
        output = subprocess.check_output(
            "schtasks /query /fo LIST /v", 
            shell=True, 
            encoding='utf-8', 
            errors='ignore'
        )
        
        # Parse the output
        current_task = {}
        for line in output.splitlines():
            line = line.strip()
            if not line:
                if current_task and "TaskName" in current_task:
                    scheduled_tasks.append(current_task)
                current_task = {}
                continue
                
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if key == "TaskName":
                    current_task["TaskName"] = value
                elif key == "Next Run Time":
                    current_task["NextRunTime"] = value
                elif key == "Status":
                    current_task["Status"] = value
                elif key == "Last Run Time":
                    current_task["LastRunTime"] = value
                elif key == "Last Result":
                    current_task["LastResult"] = value
        
        # Add the last task if it exists
        if current_task and "TaskName" in current_task:
            scheduled_tasks.append(current_task)
            
    except Exception as e:
        print(f"Error fetching scheduled tasks: {e}")
    
    return scheduled_tasks

def match_process_to_scheduled_task(process_name: str, scheduled_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Try to match a process name to a scheduled task.
    Returns task info if found, otherwise an empty dict.
    """
    for task in scheduled_tasks:
        task_name = task.get("TaskName", "").split("\\")[-1] if task.get("TaskName") else ""
        if process_name.lower() in task_name.lower():
            return task
    return {}

def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration string."""
    if seconds < 60:
        return f"{seconds:.1f} sec"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} min"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f} hrs"
    else:
        days = seconds / 86400
        return f"{days:.1f} days"

def fetch_realtime_tasks():
    """Fetches real-time processes with enhanced timing information."""
    tasks = []
    try:
        # First, get scheduled tasks information
        scheduled_tasks = get_scheduled_tasks()
        
        # Now get running processes with creation time
        for proc in list(psutil.process_iter(['pid', 'name', 'username', 'create_time']))[:50]:
            try:
                info = proc.info
                user = info.get('username', None)
                if user is None or "SYSTEM" in user.upper():
                    status = "System"
                else:
                    status = "Non-System"
                
                # Get process creation time
                create_time = info.get('create_time', None)
                if create_time:
                    start_time = datetime.datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M")
                    duration_seconds = (datetime.datetime.now() - datetime.datetime.fromtimestamp(create_time)).total_seconds()
                    duration = format_duration(duration_seconds)
                else:
                    start_time = "N/A"
                    duration = "N/A"
                
                # Try to match with a scheduled task
                process_name = info['name'] or "Unknown"
                matched_task = match_process_to_scheduled_task(process_name, scheduled_tasks)
                
                # Get next run time from scheduled task if available
                next_run = matched_task.get("NextRunTime", "N/A")
                if next_run == "N/A" and status == "System":
                    # For system processes, can approximate as recurring
                    next_run = "System managed"
                
                tasks.append({
                    "name": process_name,
                    "next_run": next_run,
                    "status": status,
                    "start_time": start_time,
                    "duration": duration,
                    "first_scheduled": matched_task.get("LastRunTime", f"PID: {info['pid']}"),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"Error fetching tasks: {e}")
    return tasks

#####################################
# 2) SystemDistributionApp Class
#####################################
class SystemDistributionApp:
    def __init__(self, glass_bgcolor, container_blur, container_shadow, bg_image_path=None):
        self.glass_bgcolor = glass_bgcolor
        self.container_blur = container_blur
        self.container_shadow = container_shadow
        self.bg_image_path = bg_image_path or ""
        self.data_rows_container = None
        self.page = None
        self.stats_container = None
        self.system_count = 0
        self.non_system_count = 0
        self.system_label = None
        self.non_system_label = None
        self.system_segment = None
        self.non_system_segment = None
        
    def create_task_table(self):
        """Creates a table displaying tasks."""
        header_row = ft.Row(
            controls=[
                ft.Container(content=ft.Text("Task Name", color="white", weight=ft.FontWeight.BOLD, size=12), width=180),
                ft.Container(content=ft.Text("Next Run Time", color="white", weight=ft.FontWeight.BOLD, size=12), width=150),
                ft.Container(content=ft.Text("Status", color="white", weight=ft.FontWeight.BOLD, size=12), width=100),
                ft.Container(content=ft.Text("Start Time", color="white", weight=ft.FontWeight.BOLD, size=12), width=150),
                ft.Container(content=ft.Text("Duration", color="white", weight=ft.FontWeight.BOLD, size=12), width=100),
                ft.Container(content=ft.Text("First Scheduled", color="white", weight=ft.FontWeight.BOLD, size=12), width=150),
            ],
            spacing=10,
        )

        # Create the data rows container
        self.data_rows_container = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
        table_data = ft.Container(content=self.data_rows_container, expand=True)
        
        # Create the table container
        table_container = ft.Container(
            content=ft.Column(controls=[header_row, table_data], spacing=0, expand=True),
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            expand=True,
        )
        
        # Create the statistics section (right side)
        self.stats_container = ft.Container(
            content=ft.Column([
                ft.Text("Statistics", size=24, color="white", weight=ft.FontWeight.BOLD),
                ft.Container(height=40),  # Spacer
                self.create_pie_chart_ui()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=self.glass_bgcolor,
            blur=self.container_blur,
            shadow=self.container_shadow,
            border_radius=10,
            padding=15,
            width=400  # Reduced width to make left side take more space (was 500)
        )
        
        # Create layout with table on left and chart on right
        # Use a ratio of 7:3 to make the table larger relative to the chart
        layout = ft.Row(
            controls=[
                ft.Container(content=table_container, expand=7),  # Table gets 70% of space
                ft.Container(content=self.stats_container, expand=3)  # Chart gets 30% of space
            ],
            spacing=10,
            expand=True
        )
        
        return layout
    
    def create_pie_chart_ui(self):
        """Creates a donut chart visualization using standard Flet components."""
        self.chart_title = ft.Text("System vs. Non-System Processes", size=18, color="white", weight=ft.FontWeight.BOLD)
        
        # Initialize with dummy data - will be updated with real data
        self.system_percent = 50
        self.non_system_percent = 50
        
        # Chart colors
        system_color = "#4e68f9"  # Blue for System
        non_system_color = "#ff6054"  # Red for Non-System
        
        # Chart dimensions
        chart_size = 220
        
        # Increase donut width by adjusting stroke_width (was 0.2, now 0.3)
        donut_thickness = chart_size * 0.3
        
        # Create the system segment (blue portion) using a progress ring
        self.system_segment = ft.ProgressRing(
            value=self.system_percent / 100,
            width=chart_size,
            height=chart_size,
            stroke_width=donut_thickness,  # Increased thickness for wider donut
            color=system_color,
            bgcolor="transparent",
        )
        
        # Create the non-system segment (red portion)
        self.non_system_segment = ft.ProgressRing(
            value=self.non_system_percent / 100,
            width=chart_size,
            height=chart_size,
            stroke_width=donut_thickness,  # Increased thickness for wider donut
            color=non_system_color,
            bgcolor="transparent",
            rotate=math.pi * self.system_percent / 50,  # Rotate to start where system ends
        )
        
        # Create the percentage labels
        self.system_label = ft.Text(
            f"{self.system_percent}%", 
            size=16, 
            color="white", 
            weight=ft.FontWeight.BOLD
        )
        
        self.non_system_label = ft.Text(
            f"{self.non_system_percent}%", 
            size=16, 
            color="white", 
            weight=ft.FontWeight.BOLD
        )
        
        # Create a stack for the chart - without the black center circle
        self.chart_container = ft.Container(
            width=chart_size,
            height=chart_size,
            content=ft.Stack([
                # Non-system segment first (base layer)
                self.non_system_segment,
                # System segment on top
                self.system_segment,
                # System percentage label
                ft.Container(
                    content=self.system_label,
                    left=chart_size * 0.6,
                    top=chart_size * 0.3,
                ),
                # Non-System percentage label
                ft.Container(
                    content=self.non_system_label,
                    left=chart_size * 0.2,
                    top=chart_size * 0.6,
                ),
            ]),
            alignment=ft.alignment.center,
        )
        
        # Create the legend
        legend = ft.Row([
            # System legend item
            ft.Row([
                ft.Container(width=12, height=12, bgcolor=system_color, border_radius=6),
                ft.Text("System", color="white", size=14),
            ], spacing=5),
            # Spacer
            ft.Container(width=30),
            # Non-System legend item
            ft.Row([
                ft.Container(width=12, height=12, bgcolor=non_system_color, border_radius=6),
                ft.Text("Non-System", color="white", size=14),
            ], spacing=5),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        # Create the chart view
        return ft.Column([
            self.chart_title,
            ft.Container(height=40),  # Spacer
            self.chart_container,  
            ft.Container(height=20),  # Spacer
            legend
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def update_task_table(self, tasks):
        """Updates the task table with new data."""
        try:
            new_data_rows = [
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(content=ft.Text(t["name"], color="white", size=12), width=180),
                            ft.Container(content=ft.Text(t["next_run"], color="white", size=12), width=150),
                            ft.Container(content=ft.Text(t["status"], color="#90caf9" if t["status"] == "System" else "#a5d6a7", size=12), width=100),
                            ft.Container(content=ft.Text(t["start_time"], color="white", size=12), width=150),
                            ft.Container(content=ft.Text(t["duration"], color="white", size=12), width=100),
                            ft.Container(content=ft.Text(t["first_scheduled"], color="white", size=12), width=150),
                        ],
                        spacing=10,
                    ),
                    padding=10,
                    border_radius=5,
                    bgcolor=self.glass_bgcolor,
                    blur=self.container_blur,
                    shadow=self.container_shadow,
                ) for t in tasks
            ]
            if self.data_rows_container:
                self.data_rows_container.controls = new_data_rows
        except Exception as e:
            print(f"Error updating task table: {e}")

    def update_statistics_chart(self, tasks):
        """Updates the statistics chart with new data."""
        try:
            # Count system vs non-system processes
            self.system_count = sum(1 for t in tasks if t["status"] == "System")
            self.non_system_count = len(tasks) - self.system_count
            
            total = max(1, self.system_count + self.non_system_count)  # Avoid division by zero
            self.system_percent = int((self.system_count / total) * 100)
            self.non_system_percent = 100 - self.system_percent
            
            # Update the progress rings with new values
            if hasattr(self, 'system_segment') and self.system_segment:
                self.system_segment.value = self.system_percent / 100
                
            if hasattr(self, 'non_system_segment') and self.non_system_segment:
                self.non_system_segment.value = self.non_system_percent / 100
                # Adjust rotation based on system percentage
                self.non_system_segment.rotate = math.pi * self.system_percent / 50
            
            # Update the percentage labels
            if hasattr(self, 'system_label') and self.system_label:
                self.system_label.value = f"{self.system_percent}%"
                
            if hasattr(self, 'non_system_label') and self.non_system_label:
                self.non_system_label.value = f"{self.non_system_percent}%"
                
        except Exception as e:
            print(f"Error updating statistics chart: {e}")

#####################################
# 4) Create a function to return layout
#####################################
def create_system_distribution_layout(glass_bgcolor, container_blur, container_shadow, bg_image_path=None):
    app = SystemDistributionApp(glass_bgcolor, container_blur, container_shadow, bg_image_path)
    layout = app.create_task_table()
    return layout, app