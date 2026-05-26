import flet as ft
from flet import Colors, Blur, BlurTileMode, BoxShadow, ShadowBlurStyle, Offset
import psutil
import time
import threading
from datetime import datetime
import logging
import re

# -----------------------------------------
# MAIN CHANGES FOR FASTER MONITORING:
# 1) Update interval increased to 10 seconds.
# 2) Logging level = WARNING by default.
# 3) Partial skipping of ephemeral connections or loopback.
# 4) Caching process name lookups.
# -----------------------------------------

UPDATE_INTERVAL_SECONDS = 10  # was 5

logging.basicConfig(
    filename='network_monitor.log',
    level=logging.WARNING,  # was logging.DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DARK_BLUE = "#0B0F19"
TEAL_BLUE = "#027B8C"
LIGHT_GRAY = "#D9E2EC"
ACCENT_COLOR = "#03DAC6"
CARD_BG = "#112240"

ip_pattern_ipv4 = re.compile(r'(\d+\.\d+\.\d+\.\d+)')
ip_pattern_ipv6 = re.compile(r'((?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4})')

# Cache for process names, so we don't repeatedly call psutil.Process(pid).name()
process_name_cache = {}

class FletLogHandler(logging.Handler):
    def __init__(self, ipv4_logs_table_ref, ipv6_logs_table_ref):
        super().__init__()
        self.ipv4_logs_table_ref = ipv4_logs_table_ref
        self.ipv6_logs_table_ref = ipv6_logs_table_ref

    def emit(self, record):
        try:
            ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
            level = record.levelname
            msg = record.getMessage()

            new_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Container(content=ft.Text(ts, color="white", size=11))),
                    ft.DataCell(ft.Container(content=ft.Text(level, color="white", size=11))),
                    ft.DataCell(ft.Container(content=ft.Text(msg, color="white", size=11))),
                ]
            )

            ipv4_match = ip_pattern_ipv4.search(msg)
            ipv6_match = ip_pattern_ipv6.search(msg)
            if ipv4_match:
                if self.ipv4_logs_table_ref.current:
                    # Navigate through the nested structure to get to the DataTable
                    table = self.ipv4_logs_table_ref.current.content.controls[0].controls[0]
                    table.rows.append(new_row)
                    table.rows = table.rows[-50:]
            elif ipv6_match:
                if self.ipv6_logs_table_ref.current:
                    # Navigate through the nested structure to get to the DataTable
                    table = self.ipv6_logs_table_ref.current.content.controls[0].controls[0]
                    table.rows.append(new_row)
                    table.rows = table.rows[-50:]
            else:
                # no IP found => log to both
                if self.ipv4_logs_table_ref.current:
                    # Navigate through the nested structure to get to the DataTable
                    t4 = self.ipv4_logs_table_ref.current.content.controls[0].controls[0]
                    t4.rows.append(new_row)
                    t4.rows = t4.rows[-50:]
                if self.ipv6_logs_table_ref.current:
                    # Navigate through the nested structure to get to the DataTable
                    t6 = self.ipv6_logs_table_ref.current.content.controls[0].controls[0]
                    t6.rows.append(new_row)
                    t6.rows = t6.rows[-50:]
        except Exception as e:
            logger.error(f"Error in FletLogHandler.emit: {str(e)}")

def create_network_monitoring_layout(glass_bgcolor, container_blur, container_shadow):
    ipv4_live_table_ref = ft.Ref[ft.Container]()
    ipv6_live_table_ref = ft.Ref[ft.Container]()
    ipv4_logs_table_ref = ft.Ref[ft.Container]()
    ipv6_logs_table_ref = ft.Ref[ft.Container]()
    status_text_ref = ft.Ref[ft.Text]()

    connections = {}
    connection_logs = {"ipv4": [], "ipv6": []}

    def get_process_name(pid):
        """Use a cache to avoid repeated psutil calls for the same pid."""
        if not pid or pid == "N/A":
            return "Unknown"
        if pid in process_name_cache:
            return process_name_cache[pid]
        try:
            p = psutil.Process(pid)
            name = p.name()
            process_name_cache[pid] = name
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name_cache[pid] = "Unknown"
            return "Unknown"

    def get_network_data():
        try:
            current_time = datetime.now()
            current_conns = {}
            conns = psutil.net_connections()
            for conn in conns:
                # skip loopback or ephemeral if desired:
                if conn.laddr and conn.laddr.ip in ["127.0.0.1", "::1"]:
                    continue
                if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                    ip = conn.raddr.ip
                    if not ip:
                        continue
                    pid = conn.pid if conn.pid else "N/A"
                    process_name = get_process_name(pid)

                    current_conns[ip] = {
                        'connected_at': current_time,
                        'process_name': process_name,
                        'pid': pid,
                        'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}",
                        'status': conn.status,
                        'bytes_recv': psutil.net_io_counters().bytes_recv,
                        'bytes_sent': psutil.net_io_counters().bytes_sent,
                        'security_check': "Safe",
                    }
                    if ip not in connections:
                        logger.info(f"New connection detected: {ip}")
                        connections[ip] = current_conns[ip]
                        row = [
                            process_name,
                            str(pid),
                            f"{conn.raddr.ip}:{conn.raddr.port}",
                            current_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Pending",
                            conn.status,
                            f"{psutil.net_io_counters().bytes_recv / 1024:.2f} KB",
                            f"{psutil.net_io_counters().bytes_sent / 1024:.2f} KB"
                        ]
                        if ':' in ip:
                            connection_logs["ipv6"].append(row)
                        else:
                            connection_logs["ipv4"].append(row)

            # detect disconnections
            for ip in list(connections.keys()):
                if ip not in current_conns:
                    logger.info(f"Connection disconnected: {ip}")
                    disconnected_at = datetime.now()
                    net_counters = psutil.net_io_counters()
                    bytes_sent = net_counters.bytes_sent - connections[ip]['bytes_sent']
                    bytes_recv = net_counters.bytes_recv - connections[ip]['bytes_recv']
                    row = [
                        connections[ip]['process_name'],
                        connections[ip]['pid'],
                        connections[ip]['remote_addr'],
                        connections[ip]['connected_at'].strftime("%Y-%m-%d %H:%M:%S"),
                        "Safe",
                        "Disconnected",
                        f"{bytes_recv / 1024:.2f} KB",
                        f"{bytes_sent / 1024:.2f} KB"
                    ]
                    if ':' in ip:
                        connection_logs["ipv6"].append(row)
                    else:
                        connection_logs["ipv4"].append(row)
                    del connections[ip]

            connection_logs["ipv4"] = connection_logs["ipv4"][-50:]
            connection_logs["ipv6"] = connection_logs["ipv6"][-50:]

            # Build live IPv4/IPv6 data
            live_ipv4 = []
            live_ipv6 = []
            for ip, c in connections.items():
                # decide IPv4 vs IPv6 by looking for colon
                if '.' in c['remote_addr'].split(':')[0]:
                    live_ipv4.append([
                        c['process_name'],
                        c['pid'],
                        c['remote_addr'],
                        c['security_check'],
                        c['status'],
                        f"{c['bytes_recv'] / 1024:.2f} KB",
                        f"{c['bytes_sent'] / 1024:.2f} KB"
                    ])
                else:
                    live_ipv6.append([
                        c['process_name'],
                        c['pid'],
                        c['remote_addr'],
                        c['security_check'],
                        c['status'],
                        f"{c['bytes_recv'] / 1024:.2f} KB",
                        f"{c['bytes_sent'] / 1024:.2f} KB"
                    ])
            status = f"Found {len(live_ipv4)} IPv4 and {len(live_ipv6)} IPv6 connections"
            return live_ipv4, live_ipv6, status
        except Exception as e:
            logger.error(f"Error fetching network data: {str(e)}")
            return [], [], f"Error fetching network data: {str(e)}"

    def create_network_table(columns, sample_data=None, table_ref=None):
        if sample_data is None:
            sample_data = []
       
        # Create a DataTable with a large width to accommodate columns
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(col, color="white", size=11))
                for col in columns
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(cell), color="white", size=11))
                        for cell in row
                    ]
                ) for row in sample_data
            ],
            border=ft.border.all(0, "transparent"),
            horizontal_lines=ft.border.BorderSide(1, "#363636"),
            heading_row_color=Colors.with_opacity(0.1, "white"),
            heading_row_height=45,
            data_row_min_height=30,
            data_row_max_height=40,
            column_spacing=8,
            width=len(columns) * 200,  # Adjust the width based on the number of columns
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

    def update_network_data(page):
        live_ipv4, live_ipv6, status = get_network_data()

        if status_text_ref.current:
            status_text_ref.current.value = status

        if ipv4_live_table_ref.current:
            # Navigate through the nested structure to get to the DataTable
            t = ipv4_live_table_ref.current.content.controls[0].controls[0]
            t.rows = [
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text(str(cell), color="white", size=11)) for cell in row]
                ) for row in live_ipv4
            ]

        if ipv6_live_table_ref.current:
            # Navigate through the nested structure to get to the DataTable
            t = ipv6_live_table_ref.current.content.controls[0].controls[0]
            t.rows = [
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text(str(cell), color="white", size=11)) for cell in row]
                ) for row in live_ipv6
            ]

        if ipv4_logs_table_ref.current:
            # Navigate through the nested structure to get to the DataTable
            t4 = ipv4_logs_table_ref.current.content.controls[0].controls[0]
            t4.rows = [
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text(str(cell), color="white", size=11)) for cell in row]
                ) for row in connection_logs["ipv4"]
            ]
        if ipv6_logs_table_ref.current:
            # Navigate through the nested structure to get to the DataTable
            t6 = ipv6_logs_table_ref.current.content.controls[0].controls[0]
            t6.rows = [
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text(str(cell), color="white", size=11)) for cell in row]
                ) for row in connection_logs["ipv6"]
            ]

        page.update()

    def start_updates(page):
        def update_loop():
            while True:
                try:
                    update_network_data(page)
                    time.sleep(UPDATE_INTERVAL_SECONDS)  # was 5, now 10
                except Exception as e:
                    logger.error(f"Error in update loop: {str(e)}")
                    time.sleep(UPDATE_INTERVAL_SECONDS)
        t = threading.Thread(target=update_loop, daemon=True)
        t.start()

    # ---------- UI Layout (unchanged) ----------
    ipv4_live_columns = [
        "Process Name", "PID", "IP Address", "Security Check",
        "Status", "Data in", "Data out"
    ]
    ipv6_live_columns = [
        "Process Name", "PID", "IP Address", "Security Check",
        "Status", "Data in", "Data out"
    ]
    ipv4_logs_columns = [
        "Process Name", "PID", "IP Address", "Connection Start Timestamp",
        "Security Check", "Status", "Data in", "Data out"
    ]
    ipv6_logs_columns = [
        "Process Name", "PID", "IP Address", "Connection Start Timestamp",
        "Security Check", "Status", "Data in", "Data out"
    ]

    left_top_section = ft.Container(
        content=ft.Column([
            ft.Text("Live Network Connections: IPv4", size=18, weight=ft.FontWeight.BOLD, color="white"),
            create_network_table(ipv4_live_columns, table_ref=ipv4_live_table_ref),
        ]),
        expand=True,
        bgcolor=glass_bgcolor,
        blur=container_blur,
        shadow=container_shadow,
        border_radius=15,
        padding=20,
    )
    left_bottom_section = ft.Container(
        content=ft.Column([
            ft.Text("Live Network Connections: IPv6", size=18, weight=ft.FontWeight.BOLD, color="white"),
            create_network_table(ipv6_live_columns, table_ref=ipv6_live_table_ref),
        ]),
        expand=True,
        bgcolor=glass_bgcolor,
        blur=container_blur,
        shadow=container_shadow,
        border_radius=15,
        padding=20,
    )
    left_panel = ft.Container(
        content=ft.Column(
            controls=[left_top_section, left_bottom_section],
            spacing=10,
            expand=True,
        ),
        expand=1,
        margin=ft.margin.only(left=10, right=2, top=2, bottom=10),
    )

    right_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Text("Network Connections: IPv4", size=18, weight=ft.FontWeight.BOLD, color="white"),
                        create_network_table(ipv4_logs_columns, table_ref=ipv4_logs_table_ref),
                    ]),
                    expand=True,
                ),
                # Simple spacer between the two sections
                ft.Container(height=20),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Network Connections: IPv6", size=18, weight=ft.FontWeight.BOLD, color="white"),
                        create_network_table(ipv6_logs_columns, table_ref=ipv6_logs_table_ref),
                    ]),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        expand=1,
        bgcolor=glass_bgcolor,
        blur=container_blur,
        shadow=container_shadow,
        border_radius=15,
        margin=ft.margin.only(left=2, right=10, top=2, bottom=10),
        padding=20,
    )

    status_text = ft.Text("Initializing...", color="white", size=12, ref=status_text_ref)
    layout = ft.Column(
        controls=[
            ft.Row(
                controls=[left_panel, right_panel],
                spacing=4,
                expand=True,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            status_text
        ],
        spacing=0,
        expand=True,
    )

    def init_network_monitoring(page: ft.Page):
        logger.info("Initializing network monitoring (manual init)")
        flet_handler = FletLogHandler(ipv4_logs_table_ref, ipv6_logs_table_ref)
        flet_handler.setLevel(logging.DEBUG)
        logger.addHandler(flet_handler)
        start_updates(page)
        update_network_data(page)

    return layout, init_network_monitoring