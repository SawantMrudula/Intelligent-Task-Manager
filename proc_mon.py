import flet as ft
from flet import Colors, BoxShadow, Offset
import psutil
import time
import threading
from datetime import datetime
import logging
import re

logging.basicConfig(filename='process_monitor.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

process_pattern = re.compile(r'(\w+|\d+)')
process_cache = {}

def create_process_monitoring_layout(glass_bgcolor, container_blur, container_shadow):
    running_processes_table_ref = ft.Ref[ft.Container]()
    critical_alerts_table_ref = ft.Ref[ft.Container]()
    process_logs_table_ref = ft.Ref[ft.Container]()
    status_text_ref = ft.Ref[ft.Text]()

    processes = {}
    process_logs = []
    critical_alerts = []

    def get_process_data():
        global process_cache
        try:
            current_processes = {}
            processes_data = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status'])
            current_time = datetime.now()
            current_pids = set()

            for proc in processes_data:
                pid = proc.info['pid']
                if pid in (0, 1):
                    continue
                current_pids.add(pid)
                process_name = proc.info['name'] or "Unknown"
                cpu_usage = proc.info['cpu_percent'] or 0.0
                memory_usage = proc.info['memory_percent'] or 0.0
                status = proc.info['status'] or "Running"

                if pid in process_cache and process_cache[pid]['name'] == process_name and process_cache[pid]['status'] == status:
                    current_processes[pid] = process_cache[pid]
                    current_processes[pid]['cpu_usage'] = cpu_usage
                    current_processes[pid]['memory_usage'] = memory_usage
                else:
                    current_processes[pid] = {
                        'pid': pid, 'name': process_name, 'cpu_usage': cpu_usage, 'memory_usage': memory_usage,
                        'status': status, 'started_at': current_time, 'security_check': "Safe"
                    }
                    if pid not in process_cache:
                        logger.info(f"New process detected: {process_name} (PID: {pid})")
                        # Include timestamp in process log
                        process_logs.append([process_name, str(pid), f"{cpu_usage:.2f}%", f"{memory_usage:.2f}%", status, current_time.strftime("%Y-%m-%d %H:%M:%S")])
                        if cpu_usage > 80 or memory_usage > 80:
                            critical_alerts.append([process_name, str(pid), f"High Usage: CPU {cpu_usage:.2f}%, Memory {memory_usage:.2f}%", current_time.strftime("%Y-%m-%d %H:%M:%S")])

            for pid in list(process_cache.keys()):
                if pid not in current_pids:
                    logger.info(f"Process terminated: {process_cache[pid]['name']} (PID: {pid})")
                    terminated_at = datetime.now()
                    process_logs.append([process_cache[pid]['name'], str(pid), f"{process_cache[pid]['cpu_usage']:.2f}%", f"{process_cache[pid]['memory_usage']:.2f}%", "Terminated", terminated_at.strftime("%Y-%m-%d %H:%M:%S")])
                    critical_alerts.append([process_cache[pid]['name'], str(pid), "Process Terminated", terminated_at.strftime("%Y-%m-%d %H:%M:%S")])
                    del process_cache[pid]

            process_cache.update(current_processes)
            process_logs[:] = process_logs[-50:]
            critical_alerts[:] = critical_alerts[-50:]

            running_processes = [[proc['name'], f"{proc['cpu_usage']:.2f}%", f"{proc['memory_usage']:.2f}%", proc['status'], proc['security_check']] for proc in current_processes.values()]
            status = f"Monitoring {len(running_processes)} active processes | {len(critical_alerts)} critical alerts"
            return running_processes, critical_alerts, status
        except Exception as e:
            logger.error(f"Error fetching process data: {str(e)}")
            return [], [], f"Error: {str(e)}"

    def update_process_data(page, last_update=[0], ui_update_interval=0.5):
        running_data, alerts_data, status = get_process_data()
        current_time = time.time()
        
        if status_text_ref.current and status_text_ref.current.value != status:
            status_text_ref.current.value = status
        
        if running_processes_table_ref.current and running_processes_table_ref.current.visible:
            # Navigate through the nested structure to get to the DataTable
            table = running_processes_table_ref.current.content.controls[0].controls[0]
            new_rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    str(cell), 
                                    color="white", 
                                    size=11, 
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                tooltip=ft.Tooltip(
                                    message=str(cell), 
                                    bgcolor="#08CDFF", 
                                    text_style=ft.TextStyle(color="white"), 
                                    padding=5
                                )
                            )
                        ) for cell in row
                    ]
                ) for row in running_data
            ]
            if table.rows != new_rows:
                table.rows = new_rows
        
        if critical_alerts_table_ref.current and critical_alerts_table_ref.current.visible:
            # Navigate through the nested structure to get to the DataTable
            table = critical_alerts_table_ref.current.content.controls[0].controls[0]
            new_rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    str(cell), 
                                    color="white", 
                                    size=11, 
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                tooltip=ft.Tooltip(
                                    message=str(cell), 
                                    bgcolor="#08CDFF", 
                                    text_style=ft.TextStyle(color="white"), 
                                    padding=5
                                )
                            )
                        ) for cell in row
                    ]
                ) for row in alerts_data
            ]
            if table.rows != new_rows:
                table.rows = new_rows
        
        if process_logs_table_ref.current:
            # Navigate through the nested structure to get to the DataTable
            table = process_logs_table_ref.current.content.controls[0].controls[0]
            new_rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    str(cell), 
                                    color="white", 
                                    size=11, 
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                tooltip=ft.Tooltip(
                                    message=str(cell), 
                                    bgcolor="#08CDFF", 
                                    text_style=ft.TextStyle(color="white"), 
                                    padding=5
                                )
                            )
                        ) for cell in row
                    ]
                ) for row in process_logs
            ]
            if table.rows != new_rows:
                table.rows = new_rows
        
        if current_time - last_update[0] >= ui_update_interval:
            page.update()
            last_update[0] = current_time

    def start_updates(page):
        def update_loop():
            while True:
                try:
                    update_process_data(page)
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Error in update loop: {str(e)}")
                    time.sleep(10)
        threading.Thread(target=update_loop, daemon=True).start()

    def create_process_table(columns, table_ref=None):
        # Create the data table
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text(col, color="white", size=11)
                ) 
                for col in columns
            ],
            rows=[], 
            border=ft.border.all(0, "transparent"), 
            horizontal_lines=ft.border.BorderSide(1, "#363636"),
            heading_row_color=Colors.with_opacity(0.1, "white"), 
            heading_row_height=45, 
            data_row_min_height=30, 
            data_row_max_height=40,
            column_spacing=8,
            width=len(columns) * 200,  # Set width based on number of columns
        )
        
        # First wrap the DataTable in a Row for horizontal scrolling
        horizontal_scroll_container = ft.Row(
            controls=[data_table],
            scroll="auto",
        )
        
        # Then wrap that in a Column for vertical scrolling
        vertical_scroll_container = ft.Column(
            controls=[horizontal_scroll_container],
            scroll="auto",
            expand=True,
        )
        
        # Finally wrap in a container with clip behavior
        table = ft.Container(
            content=vertical_scroll_container,
            ref=table_ref, 
            clip_behavior=ft.ClipBehavior.HARD_EDGE, 
            expand=True, 
            padding=5,
            height=300,  # Set a fixed height to ensure vertical scrollbar appears
        )
        
        return table

    def create_search_filter_bar(title, table_ref, log_type):
        last_filter_time = [0]
        
        def filter_table(e, debounce_interval=0.3):
            nonlocal last_filter_time
            current_time = time.time()
            if current_time - last_filter_time[0] < debounce_interval:
                return
            last_filter_time[0] = current_time
            search_text = e.control.value.strip().lower()
            if not search_text:
                reset_table()
                return
            
            # Table structure is now container -> column -> row -> datatable
            if table_ref.current:
                # Navigate to the DataTable through the nested structure
                datatable = table_ref.current.content.controls[0].controls[0]
                for row in datatable.rows:
                    # Get text from each cell
                    combined_text = " ".join(str(cell.content.content.value) for cell in row.cells).lower()
                    row.visible = search_text in combined_text
                datatable.update()

        def reset_table():
            # Table structure is now container -> column -> row -> datatable
            if table_ref.current:
                # Navigate to the DataTable through the nested structure
                datatable = table_ref.current.content.controls[0].controls[0]
                for row in datatable.rows:
                    row.visible = True
                datatable.update()

        def update_filter_hint(e, search_field):
            filter_type = e.control.value
            hints = {"Process Name": f"Search {log_type} by Process Name...", "PID": f"Search {log_type} by PID...",
                     "CPU Usage": f"Search {log_type} by CPU Usage (e.g., '>50%')...", "Memory Usage": f"Search {log_type} by Memory Usage (e.g., '>10%')...",
                     "Status": f"Search {log_type} by Status...", "Alert Description": f"Search {log_type} by Alert Description..."}
            search_field.hint_text = hints[filter_type]
            search_field.update()

        search_field = ft.TextField(
            border=ft.InputBorder.NONE, height=35, text_size=12, bgcolor='transparent', color='white',
            hint_text=f"Search {title}...", hint_style=ft.TextStyle(color='#6c757d'), expand=True,
            content_padding=ft.padding.only(left=8, right=8), on_change=filter_table
        )
        filter_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(opt) for opt in ["Process Name", "PID", "CPU Usage", "Memory Usage", "Status", "Alert Description"]],
            value="Process Name", width=120, bgcolor='transparent', color='white', border_color="#03DAC6",
            on_change=lambda e: update_filter_hint(e, search_field)
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Row(controls=[ft.Icon(ft.Icons.SEARCH, color='#6c757d', size=16), search_field], spacing=5),
                                 bgcolor=glass_bgcolor, blur=container_blur, border_radius=10, padding=ft.padding.only(left=10, right=10), expand=True),
                    ft.Container(content=filter_dropdown, bgcolor=glass_bgcolor, blur=container_blur, border_radius=10, padding=5),
                    ft.Container(content=ft.PopupMenuButton(items=[ft.PopupMenuItem(text=opt) for opt in ["Newest First", "Oldest First", "CPU (High to Low)", "CPU (Low to High)"]], icon=ft.Icons.SORT, tooltip="Sort"),
                                 bgcolor=glass_bgcolor, blur=container_blur, border_radius=10, padding=5)
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=10
        )

    running_processes_columns = ["Process Name", "CPU Usage", "Memory Usage", "Status", "Security Check"]
    critical_alerts_columns = ["Process Name", "PID", "Alert Description", "Timestamp"]
    process_logs_columns = ["Process Name", "PID", "CPU Usage", "Memory Usage", "Status", "Timestamp"]

    running_processes_panel = ft.Container(content=create_process_table(running_processes_columns, table_ref=running_processes_table_ref), expand=True, visible=True)
    critical_alerts_panel = ft.Container(content=create_process_table(critical_alerts_columns, table_ref=critical_alerts_table_ref), expand=True, visible=False)
    process_logs_table = create_process_table(process_logs_columns, table_ref=process_logs_table_ref)

    def update_tab(e):
        running_processes_panel.visible = (tabs.selected_index == 0)
        critical_alerts_panel.visible = (tabs.selected_index == 1)
        e.page.update()

    tabs = ft.Tabs(tabs=[ft.Tab(text="Running Processes", icon=ft.Icons.PLAY_ARROW), ft.Tab(text="Critical Alerts", icon=ft.Icons.WARNING)], selected_index=0, indicator_color="#03DAC6", on_change=update_tab)

    left_panel = ft.Container(content=ft.Column([ft.Text("Process Monitoring", size=18, weight=ft.FontWeight.BOLD, color="white"), tabs, running_processes_panel, critical_alerts_panel]), expand=True, bgcolor=glass_bgcolor, blur=container_blur, shadow=container_shadow, border_radius=15, padding=20)
    right_panel = ft.Container(content=ft.Column([ft.Text("Process Logs", size=18, weight=ft.FontWeight.BOLD, color="white"), process_logs_table, ft.Container(height=10)]), expand=True, bgcolor=glass_bgcolor, blur=container_blur, shadow=container_shadow, border_radius=15, padding=20)

    search_bars = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=create_search_filter_bar("Processes/Alerts", running_processes_table_ref if tabs.selected_index == 0 else critical_alerts_table_ref, "Processes/Alerts"), expand=1),
                ft.Container(content=create_search_filter_bar("Process Logs", process_logs_table_ref, "Process Logs"), expand=1),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color="white", tooltip="Refresh Now", on_click=lambda e: update_process_data(e.page))
            ], spacing=4
        ),
        margin=ft.margin.only(left=10, right=10, top=2)
    )

    status_text = ft.Text("Initializing...", color="white", size=12, ref=status_text_ref)
    layout = ft.Column(controls=[search_bars, ft.Row(controls=[left_panel, right_panel], spacing=4, expand=True), status_text], spacing=0, expand=True)

    def init_process_monitor(page: ft.Page):
        logger.info("Process monitor UI initialized")
        start_updates(page)
        update_process_data(page)

    return layout, init_process_monitor

if __name__ == "__main__":
    def main(page: ft.Page):
        layout, init = create_process_monitoring_layout("#20f4f4f4", ft.Blur(10, 10, ft.BlurTileMode.REPEATED), ft.BoxShadow(1, 15, Colors.BLACK54, Offset(2, 2)))
        page.add(layout)
        init(page)
    ft.app(target=main)