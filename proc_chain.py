import flet as ft
from flet import Colors, Blur, BlurTileMode, BoxShadow
import os
import psutil
import datetime
import time
import threading
import platform
from functools import lru_cache
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_DEPTH = 20
MAX_ROWS = 50
process_cache = {}
tree_cache = {}

@lru_cache(maxsize=128)
def get_ancestors_and_dead_parent(pid):
    living_ancestors = []
    dead_ancestor = None
    current_pid = pid
    for _ in range(MAX_DEPTH):
        try:
            proc = psutil.Process(current_pid)
            parent = proc.parent()
            if not parent:
                break
            living_ancestors.append(parent.pid)
            current_pid = parent.pid
        except psutil.NoSuchProcess:
            dead_ancestor = current_pid
            break
        except Exception:
            break
    return tuple(living_ancestors), dead_ancestor

def toggle_section(event, sub_column):
    arrow_container = event.control
    expanded = arrow_container.data.get("expanded", False)
    arrow_text_obj = arrow_container.content
    arrow_text_obj.value = "▼" if not expanded else "▶"
    sub_column.visible = not expanded
    arrow_container.data["expanded"] = not expanded
    event.page.update()

def build_progeny_node(pid, depth=0):
    cache_key = (pid, depth)
    if cache_key in tree_cache:
        return tree_cache[cache_key]
    controls = []
    if depth >= MAX_DEPTH:
        controls.append(ft.Text(f"Max depth {MAX_DEPTH} reached", color="red", size=12))
    else:
        try:
            proc = psutil.Process(pid)
            children = proc.children(recursive=False)[:MAX_ROWS]
            for child in children:
                grandkids = len(child.children(recursive=False)) > 0
                arrow_symbol = "▶" if grandkids else "  "
                arrow_container = ft.Container(data={"expanded": False}, content=ft.Text(arrow_symbol, color="white", size=12))
                sub_column = ft.Column(visible=False)
                if grandkids:
                    arrow_container.on_click = lambda e, sc=sub_column: toggle_section(e, sc)
                    sub_column.controls.extend(build_progeny_node(child.pid, depth + 1))
                row = ft.Row([arrow_container, ft.Text(f"{child.name()} (PID: {child.pid})", color="white", size=12)], spacing=5)
                controls.extend([row, sub_column])
        except psutil.NoSuchProcess:
            controls.append(ft.Text(f"PID {pid} no longer exists", color="red", size=12))
        except Exception as e:
            controls.append(ft.Text(f"Error: {e}", color="red", size=12))
    tree_cache[cache_key] = controls
    return controls

@lru_cache(maxsize=128)
def build_ancestry_list(pid):
    lines = []
    try:
        proc = psutil.Process(pid)
        ancestry = []
        for _ in range(MAX_DEPTH):
            parent = proc.parent()
            if not parent:
                break
            ancestry.append(parent)
            proc = parent
        ancestry.reverse()
        indent = 0
        for p in ancestry:
            lines.append(ft.Text(" " * indent + f"{p.name()} (PID: {p.pid})", color="white", size=12))
            indent += 4
    except Exception as e:
        lines.append(ft.Text(f"Error: {e}", color="red", size=12))
    return tuple(lines)

def create_full_tree_view(pid):
    ancestry_arrow = ft.Container(data={"expanded": False}, content=ft.Text("▶", color="white", size=12))
    ancestry_subcol = ft.Column(visible=False)
    ancestry_lines = list(build_ancestry_list(pid))
    ancestry_subcol.controls = ancestry_lines
    if ancestry_lines:
        ancestry_arrow.on_click = lambda e, sc=ancestry_subcol: toggle_section(e, sc)
        ancestry_label = ft.Text("Ancestry", color="yellow", weight="bold")
    else:
        ancestry_arrow.content.value = "  "
        ancestry_label = ft.Text("No parents", color="gray")

    try:
        proc = psutil.Process(pid)
        pid_label = ft.Text(f"Selected: {proc.name()} (PID: {pid})", color="cyan", size=12, weight="bold")
    except Exception as e:
        pid_label = ft.Text(f"Error: {e}", color="red", size=12)

    progeny_arrow = ft.Container(data={"expanded": False}, content=ft.Text("▶", color="white", size=12))
    progeny_subcol = ft.Column(visible=False)
    child_nodes = build_progeny_node(pid)
    progeny_subcol.controls = child_nodes
    if child_nodes:
        progeny_arrow.on_click = lambda e, sc=progeny_subcol: toggle_section(e, sc)
        progeny_label = ft.Text("Progeny", color="yellow", weight="bold")
    else:
        progeny_arrow.content.value = "  "
        progeny_label = ft.Text("No children", color="gray")

    tree_view = ft.ListView(
        controls=[ft.Row([ancestry_arrow, ancestry_label], spacing=5), ancestry_subcol, pid_label,
                  ft.Row([progeny_arrow, progeny_label], spacing=5), progeny_subcol],
        expand=True, spacing=5
    )
    tree_view.pid = pid  # Store PID for comparison
    return tree_view

def get_process_history(pid):
    try:
        proc = psutil.Process(pid)
        create_time = datetime.datetime.fromtimestamp(proc.create_time())
        duration = datetime.datetime.now() - create_time
        return {"Start Time": create_time.strftime("%Y-%m-%d %H:%M:%S"), "Duration": str(duration).split(".")[0], "Status": proc.status()}
    except Exception as e:
        return {"Error": str(e)}

def get_extra_insights(pid):
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()) if proc.cmdline() else "N/A"
        username = proc.username()
        return {"Command Line": cmdline, "Username": username, "Status": proc.status()}
    except Exception as e:
        return {"Error": str(e)}

def get_dll_usage(pid):
    try:
        proc = psutil.Process(pid)
        if platform.system() == "Windows" and hasattr(proc, 'memory_maps'):
            modules = proc.memory_maps(grouped=False)[:10]
            return [m.path for m in modules if m.path.lower().endswith('.dll')] or ["No DLLs found"]
        return [f"Not supported or no data on {platform.system()}"]
    except Exception as e:
        return [f"Error: {str(e)}"]

def get_full_tree_pids(pid):
    all_pids = {pid}
    try:
        proc = psutil.Process(pid)
        for _ in range(MAX_DEPTH):
            parent = proc.parent()
            if not parent:
                break
            all_pids.add(parent.pid)
            proc = parent
        children = proc.children(recursive=True)[:MAX_ROWS]
        all_pids.update(child.pid for child in children)
    except:
        pass
    return all_pids

def get_resource_metrics(pid):
    try:
        proc = psutil.Process(pid)
        mem_usage = proc.memory_info().rss / (1024 ** 2)
        children_count = len(proc.children())
        niceness = proc.nice()
        net = psutil.net_io_counters()
        return {
            "CPU Usage (%)": f"{proc.cpu_percent(interval=0.1):.1f}",
            "Memory Usage (MB)": f"{mem_usage:.1f}",
            "Network In (MB)": f"{net.bytes_recv / (1024 ** 2):.1f}",
            "Network Out (MB)": f"{net.bytes_sent / (1024 ** 2):.1f}",
            "Children Count": str(children_count),
            "Niceness": str(niceness),
        }
    except Exception as e:
        return {"Error": str(e)}

def get_tree_resource_rows(pid):
    all_tree_pids = sorted(get_full_tree_pids(pid))[:MAX_ROWS]
    rows = []
    for p in all_tree_pids:
        try:
            proc = psutil.Process(p)
            usage = get_resource_metrics(p)
            if "Error" in usage:
                rows.append([str(p), proc.name(), usage["Error"], "", "", "", "", ""])
            else:
                rows.append([str(p), proc.name(), usage["CPU Usage (%)"], usage["Memory Usage (MB)"],
                             usage["Network In (MB)"], usage["Network Out (MB)"], usage["Children Count"], usage["Niceness"]])
        except:
            pass
    return rows

def get_detailed_process_info():
    global process_cache
    process_list = []
    try:
        current_pids = set(p.pid for p in psutil.process_iter(['pid']))
        new_cache = {}
        for proc in psutil.process_iter(['pid', 'name', 'create_time'])[:MAX_ROWS]:
            pid = str(proc.info['pid'])
            if pid in process_cache and proc.pid in current_pids:
                process_list.append(process_cache[pid])
                new_cache[pid] = process_cache[pid]
            else:
                try:
                    info = proc.info
                    name = info['name'] or "Unknown"
                    start_time = datetime.datetime.fromtimestamp(info['create_time']).strftime("%H:%M:%S")
                    duration = str(datetime.datetime.now() - datetime.datetime.fromtimestamp(info['create_time'])).split(".")[0]
                    row = [pid, name, start_time, duration]
                    process_list.append(row)
                    new_cache[pid] = row
                except:
                    continue
        process_cache = new_cache
    except Exception as e:
        logger.error(f"Error in get_detailed_process_info: {e}")
        process_list.append(["N/A", "Error", str(e), "N/A"])
    return process_list if process_list else [["N/A", "No processes found", "N/A", "N/A"]]

class ProcessMonitorDashboard:
    def __init__(self, glass_bgcolor, container_blur, container_shadow):
        self.glass_bgcolor = glass_bgcolor
        self.container_blur = container_blur
        self.container_shadow = container_shadow
        self.layout = self.create_layout()

    def create_layout(self):
        default_pid = os.getpid()
        self.pid_text_field = ft.TextField(
            label="PID", hint_text="Enter PID", value=str(default_pid), bgcolor="#273845", color="white", border_color="white", width=250, on_submit=self.pid_changed
        )
        self.tree_view_container = ft.Container(
            bgcolor=self.glass_bgcolor, blur=self.container_blur, border_radius=6, padding=10, expand=True, content=create_full_tree_view(default_pid)
        )
        top_left_container = ft.Container(
            content=ft.Column(controls=[ft.Text("Process Tree View", size=18, weight="bold", color="white"), self.pid_text_field, self.tree_view_container], spacing=10, expand=True),
            bgcolor=self.glass_bgcolor, blur=self.container_blur, shadow=self.container_shadow, border_radius=10, padding=10, expand=1
        )

        self.tree_resource_table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(col, color="white", size=12)) for col in ["PID", "Name", "CPU (%)", "Mem (MB)", "Net In (MB)", "Net Out (MB)", "Children", "Niceness"]],
            rows=[], 
            border=ft.border.all(0, "transparent"), 
            horizontal_lines=ft.border.BorderSide(1, "#363636"), 
            heading_row_height=40, 
            data_row_min_height=35,
            width=900  # Set a width to ensure scrollbar appears when needed
        )

        # First wrap the DataTable in a Row for horizontal scrolling
        horizontal_scroll_container = ft.Row(
            controls=[self.tree_resource_table],
            scroll="auto",
        )
        
        # Then wrap that in a Column for vertical scrolling if needed
        vertical_scroll_container = ft.Column(
            controls=[horizontal_scroll_container],
            scroll="auto",
            expand=True,
        )

        top_right_container = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Resource Analysis (Tree)", size=18, weight="bold", color="white"), 
                ft.Container(
                    content=vertical_scroll_container,
                    expand=True,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                )
            ], spacing=10, expand=True),
            bgcolor=self.glass_bgcolor, 
            blur=self.container_blur, 
            shadow=self.container_shadow, 
            border_radius=10, 
            padding=10, 
            expand=1
        )

        top_row = ft.Row([top_left_container, top_right_container], spacing=10, expand=1)

        initial_process_data = get_detailed_process_info()
        self.detailed_table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(col, color="white", size=12)) for col in ["PID", "Name", "Start", "Duration"]],
            rows=[ft.DataRow([ft.DataCell(ft.Text(str(cell), color="white", size=12)) for cell in row]) for row in initial_process_data],
            border=ft.border.all(0, "transparent"), horizontal_lines=ft.border.BorderSide(1, "#363636"), heading_row_height=40, data_row_min_height=35
        )
        bottom_left_container = ft.Container(
            content=ft.Column(controls=[ft.Text("Detailed Process Info", size=18, weight="bold", color="white"), ft.ListView([self.detailed_table], expand=True, spacing=5, auto_scroll=False)], spacing=10, expand=True),
            bgcolor=self.glass_bgcolor, blur=self.container_blur, shadow=self.container_shadow, border_radius=10, padding=10, expand=1
        )

        self.history_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(col, color="white", size=12)) for col in ["Metric", "Value"]], rows=[])
        self.insights_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(col, color="white", size=12)) for col in ["Metric", "Value"]], rows=[])
        self.dll_list = ft.Column(controls=[], scroll="auto")
        tabs = ft.Tabs(tabs=[ft.Tab(text="History", content=ft.Container(self.history_table, padding=10, expand=True)),
                             ft.Tab(text="Insights", content=ft.Container(self.insights_table, padding=10, expand=True)),
                             ft.Tab(text="DLL Usage", content=ft.Container(self.dll_list, padding=10, expand=True))], expand=True)
        bottom_right_container = ft.Container(
            content=ft.Column(controls=[ft.Text("Process Details", size=18, weight="bold", color="white"), tabs], spacing=10, expand=True),
            bgcolor=self.glass_bgcolor, blur=self.container_blur, shadow=self.container_shadow, border_radius=10, padding=10, expand=1
        )

        bottom_row = ft.Row([bottom_left_container, bottom_right_container], spacing=10, expand=1)
        return ft.Column([top_row, bottom_row], spacing=10, expand=True)

    def update_ui(self, page, full_update=True):
        try:
            pid = int(self.pid_text_field.value)
        except ValueError:
            pid = os.getpid()

        if full_update or getattr(self.tree_view_container.content, 'pid', None) != pid:
            self.tree_view_container.content = create_full_tree_view(pid)
            self.tree_view_container.update()

        tree_rows = get_tree_resource_rows(pid)
        if self.tree_resource_table.rows != tree_rows:
            self.tree_resource_table.rows = [ft.DataRow([ft.DataCell(ft.Text(str(cell), color="white", size=12)) for cell in row]) for row in tree_rows]
            self.tree_resource_table.update()

        process_data = get_detailed_process_info()
        if self.detailed_table.rows != process_data:
            self.detailed_table.rows = [ft.DataRow([ft.DataCell(ft.Text(str(cell), color="white", size=12)) for cell in row]) for row in process_data]
            self.detailed_table.update()

        history_data = get_process_history(pid)
        history_rows = [ft.DataRow([ft.DataCell(ft.Text(str(k), color="white", size=12)), ft.DataCell(ft.Text(str(v), color="white", size=12))]) for k, v in history_data.items()]
        if self.history_table.rows != history_rows:
            self.history_table.rows = history_rows
            self.history_table.update()

        insights_data = get_extra_insights(pid)
        living_ancestors, dead_ancestor = get_ancestors_and_dead_parent(pid)
        insights_data.update({"Living Ancestors": ", ".join(map(str, living_ancestors)) or "None", "Dead Ancestor": str(dead_ancestor) or "None"})
        insights_rows = [ft.DataRow([ft.DataCell(ft.Text(str(k), color="white", size=12)), ft.DataCell(ft.Text(str(v), color="white", size=12))]) for k, v in insights_data.items()]
        if self.insights_table.rows != insights_rows:
            self.insights_table.rows = insights_rows
            self.insights_table.update()

        dll_data = get_dll_usage(pid)
        if self.dll_list.controls != dll_data:
            self.dll_list.controls = [ft.Text(lib, color="white", size=12) for lib in dll_data]
            self.dll_list.update()

        if full_update:
            page.update()

    def pid_changed(self, e):
        self.update_ui(e.page)

def start_proc_chain_updates(page, dashboard):
    def update_loop():
        last_update = [0]
        ui_update_interval = 1  # Full UI update every 1 second
        while True:
            start_time = datetime.datetime.now()
            dashboard.update_ui(page, full_update=False)
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            current_time = time.time()
            if current_time - last_update[0] >= ui_update_interval:
                page.update()
                last_update[0] = current_time
            time.sleep(max(10 - elapsed, 1))
    threading.Thread(target=update_loop, daemon=True).start()

def create_process_chains_layout(glass_bgcolor, container_blur, container_shadow):
    dashboard = ProcessMonitorDashboard(glass_bgcolor, container_blur, container_shadow)
    return dashboard.layout, dashboard

if __name__ == "__main__":
    def main(page: ft.Page):
        page.title = "Process Monitor Dashboard"
        page.bgcolor = "#212121"
        layout, dashboard = create_process_chains_layout(
            glass_bgcolor="#2A2A2A",
            container_blur=ft.Blur(10, 10),
            container_shadow=ft.BoxShadow(blur_radius=10, color="#55000000")
        )
        page.add(layout)
        start_proc_chain_updates(page, dashboard)
    ft.app(target=main)