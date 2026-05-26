import flet as ft
from flet import Colors, Blur, BlurTileMode, BoxShadow, ShadowBlurStyle, Offset
import json
import os
import re
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
from collections import deque
import plotly.express as px
from flet_webview import WebView

# Table and logs constants
TABLE_PAGE_SIZE = 100
MAX_LIVE_LOGS = 50

# Visual styling from network monitor
DARK_BLUE = "#0B0F19"  # Main background color
TEAL_BLUE = "#027B8C"
LIGHT_GRAY = "#D9E2EC"
ACCENT_COLOR = "#03DAC6"  # Glowing accent color
CARD_BG = "#112240"  # Card background color

# Row backgrounds for errors or warnings
ERROR_ROW_BG = "#B22222"
WARNING_ROW_BG = "#3A3F3F"

def get_file_line_count(file_path):
    count = 0
    try:
        with open(file_path, "r") as f:
            for _ in f:
                count += 1
    except Exception as e:
        print("Error counting file lines:", e)
    return count

def read_all_lines(file_path):
    lines = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                lines.append(line.rstrip("\n"))
    except Exception as e:
        print("Error reading file:", e)
    return lines

class LogEntry:
    def __init__(self, timestamp, level, script, module, funcName, lineNo, message, **kwargs):
        try:
            self.timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except Exception:
            self.timestamp = None
        self.level = level
        self.script = script
        self.module = module
        self.funcName = funcName
        self.lineNo = lineNo
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)

def parse_log_line(json_line):
    """
    Expects JSON lines with keys:
      timestamp, level, script, module, funcName, lineNo, message
    Returns a dict or None if invalid.
    """
    try:
        data = json.loads(json_line)
        required = ["timestamp", "level", "script", "module", "funcName", "lineNo", "message"]
        if not all(k in data for k in required):
            return None
        return data
    except:
        return None

def build_df_from_lines(lines):
    """
    Convert lines of JSON logs into a DataFrame with columns:
      [timestamp, level, script, module, funcName, lineNo, message]
    """
    rows = []
    for ln in lines:
        parsed = parse_log_line(ln)
        if not parsed:
            continue
        entry = LogEntry(**parsed)
        rows.append({
            "timestamp": entry.timestamp,
            "level": entry.level or "UNKNOWN",
            "script": entry.script or "",
            "module": entry.module or "",
            "funcName": entry.funcName or "",
            "lineNo": entry.lineNo,
            "message": entry.message or "",
        })
    return pd.DataFrame(rows)

def build_small_chart(df, text_color):
    """
    Builds a small bar chart (Plotly) of logs per hour.
    If df is empty, returns a simple "No data" text in the same color.
    """
    if df.empty:
        return ft.Text("No data", color=text_color)

    df["timestamp_hour"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:00")
    group = df.groupby("timestamp_hour").size().reset_index(name="count")
    group = group.sort_values("timestamp_hour")

    fig = px.bar(
        group,
        x="timestamp_hour",
        y="count",
        title="Logs per Hour",
        labels={"timestamp_hour": "Hour", "count": "Count"},
        color_discrete_sequence=[ACCENT_COLOR]  # Use the teal accent color
    )

    # Update figure layout to match dark theme
    fig.update_layout(
        paper_bgcolor=DARK_BLUE,
        plot_bgcolor=DARK_BLUE,
        font=dict(color=LIGHT_GRAY),
        title_font_color=LIGHT_GRAY,
        margin=dict(l=40, r=20, t=40, b=40),
    )

    # Update axes
    fig.update_xaxes(
        gridcolor="#2D3748",
        tickfont=dict(color=LIGHT_GRAY),
        title_font=dict(color=LIGHT_GRAY)
    )
    fig.update_yaxes(
        gridcolor="#2D3748",
        tickfont=dict(color=LIGHT_GRAY),
        title_font=dict(color=LIGHT_GRAY)
    )

    html_str = fig.to_html(include_plotlyjs="cdn", full_html=False)
    return WebView(html=html_str, width=350, height=300)

def create_logs_analytics_layout(
    base_path,
    glass_bgcolor=CARD_BG,
    container_blur=Blur(20, BlurTileMode.REPEATED),
    container_shadow=BoxShadow(
        spread_radius=1,
        blur_radius=10,
        color="#14E1F4",
        offset=Offset(0, 0),
        blur_style=ShadowBlurStyle.OUTER,
    ),
    accent_color=ACCENT_COLOR,
    background_color=DARK_BLUE,
    card_color=CARD_BG,
    text_color=LIGHT_GRAY
):
    """
    Creates the logs analytics UI, using the enhanced color scheme based on network monitor.
    """

    global_lock = threading.Lock()
    global_df = pd.DataFrame()
    live_logs_buffer = deque([], maxlen=MAX_LIVE_LOGS)
    log_file_path = None

    # Filter state
    start_datetime = None
    end_datetime = None

    # Stats text
    total_count_text = ft.Text("0", color=text_color, size=20, weight=ft.FontWeight.BOLD)
    info_count_text = ft.Text("0", color=text_color, size=20, weight=ft.FontWeight.BOLD)
    warn_count_text = ft.Text("0", color=text_color, size=20, weight=ft.FontWeight.BOLD)
    error_count_text = ft.Text("0", color=text_color, size=20, weight=ft.FontWeight.BOLD)

    def update_stats(df):
        if df.empty:
            total_count_text.value = "0"
            info_count_text.value = "0"
            warn_count_text.value = "0"
            error_count_text.value = "0"
        else:
            total_count = len(df)
            info_count = len(df[df["level"].str.upper() == "INFO"])
            warn_count = len(df[df["level"].str.upper() == "WARNING"])
            error_count = len(df[df["level"].str.upper().isin(["ERROR", "CRITICAL"])])
            total_count_text.value = str(total_count)
            info_count_text.value = str(info_count)
            warn_count_text.value = str(warn_count)
            error_count_text.value = str(error_count)

    def make_stat_card(title, value_widget, icon_name):
        return ft.Container(
            width=180,
            height=100,
            bgcolor=glass_bgcolor,
            blur=container_blur,
            shadow=container_shadow,
            border_radius=15,
            padding=15,
            content=ft.Row(
                controls=[
                    ft.Icon(name=icon_name, color=accent_color, size=30),
                    ft.Column(
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(title, color=text_color, size=14, weight=ft.FontWeight.BOLD),
                            value_widget,
                        ],
                    )
                ],
                alignment=ft.MainAxisAlignment.START
            ),
        )

    stats_row = ft.Row(
        controls=[
            make_stat_card("Total Logs", total_count_text, ft.Icons.LIST),
            make_stat_card("Infos", info_count_text, ft.Icons.INFO),
            make_stat_card("Warnings", warn_count_text, ft.Icons.WARNING),
            make_stat_card("Errors", error_count_text, ft.Icons.ERROR),
        ],
        alignment="start",
    )

    small_chart_container = ft.Container(
        width=350,
        height=300,
        bgcolor=glass_bgcolor,
        blur=container_blur,
        shadow=container_shadow,
        border_radius=15,
        padding=15,
        alignment=ft.alignment.top_center,
        content=ft.Text("No data", color=text_color)
    )

    # Create a glass-style data table with enhanced visuals
    def create_styled_data_table(columns):
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(col, color=text_color, weight=ft.FontWeight.BOLD, size=12))
                for col in columns
            ],
            rows=[],
            border=ft.border.all(0, "transparent"),
            horizontal_lines=ft.border.BorderSide(1, "#363636"),
            heading_row_color=Colors.with_opacity(0.1, "white"),
            heading_row_height=45,
            data_row_min_height=35,
            data_row_max_height=50,
            column_spacing=10,
            width=1000,
        )

    # Create styled data tables
    data_table_columns = ["Timestamp", "Level", "Script", "Module", "Function", "Line No", "Message"]
    data_table = create_styled_data_table(data_table_columns)
    live_logs_table = create_styled_data_table(data_table_columns)

    # ------------- Utility functions -------------
    def apply_filters_to_df(df):
        if df.empty:
            return df
        mask = pd.Series([True] * len(df), index=df.index)

        if start_datetime and end_datetime:
            mask = mask & (df["timestamp"] >= start_datetime) & (df["timestamp"] <= end_datetime)

        if script_field.value.strip():
            s_lower = script_field.value.strip().lower()
            mask = mask & (df["script"].str.lower() == s_lower)

        if module_field.value.strip():
            m_lower = module_field.value.strip().lower()
            mask = mask & (df["module"].str.lower() == m_lower)

        if message_field.value.strip():
            try:
                pattern = re.compile(message_field.value.strip(), re.IGNORECASE)
                mask = mask & df["message"].apply(lambda x: bool(pattern.search(x)))
            except:
                return pd.DataFrame([])

        if level_dropdown.value.strip():
            lvl_lower = level_dropdown.value.strip().lower()
            mask = mask & (df["level"].str.lower() == lvl_lower)

        search_txt = search_field.value.strip().lower()
        if search_txt:
            mask = mask & df["message"].str.lower().str.contains(search_txt)

        return df[mask]

    def update_small_chart():
        with global_lock:
            df_copy = global_df.copy()
        df_filtered = apply_filters_to_df(df_copy)
        if df_filtered.empty or "timestamp" not in df_filtered.columns:
            small_chart_container.content = ft.Text("No data", color=text_color)
        else:
            df_valid = df_filtered.dropna(subset=["timestamp"])
            small_chart_container.content = build_small_chart(df_valid, text_color)
        small_chart_container.update()

    def update_table(df):
        data_table.rows.clear()
        if df.empty:
            data_table.rows = []
        else:
            df_sorted = df.sort_values("timestamp", na_position="first").reset_index(drop=True)
            row_count = len(df_sorted)
            start_idx = max(0, row_count - TABLE_PAGE_SIZE)
            subset = df_sorted.iloc[start_idx:row_count]
            for _, row_ in subset.iterrows():
                ts_str = row_["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(row_["timestamp"]) else ""
                lvl = (row_["level"] or "").upper()

                if lvl in ["ERROR", "CRITICAL"]:
                    row_bg = ERROR_ROW_BG
                elif lvl == "WARNING":
                    row_bg = WARNING_ROW_BG
                else:
                    row_bg = glass_bgcolor

                data_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(ts_str, color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["level"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["script"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["module"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["funcName"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(str(row_["lineNo"]) if pd.notnull(row_["lineNo"]) else "", color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["message"], color=text_color, size=12)),
                        ],
                        color=row_bg
                    )
                )

    def update_live_logs_table():
        live_logs_table.rows.clear()
        with global_lock:
            lines = list(live_logs_buffer)
        df_live = build_df_from_lines(lines)
        df_live_filtered = apply_filters_to_df(df_live)
        if not df_live_filtered.empty:
            for _, row_ in df_live_filtered.iterrows():
                ts_str = row_["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(row_["timestamp"]) else ""
                lvl = (row_["level"] or "").upper()

                if lvl in ["ERROR", "CRITICAL"]:
                    row_bg = ERROR_ROW_BG
                elif lvl == "WARNING":
                    row_bg = WARNING_ROW_BG
                else:
                    row_bg = glass_bgcolor

                live_logs_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(ts_str, color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["level"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["script"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["module"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["funcName"], color=text_color, size=12)),
                            ft.DataCell(ft.Text(str(row_["lineNo"]) if pd.notnull(row_["lineNo"]) else "", color=text_color, size=12)),
                            ft.DataCell(ft.Text(row_["message"], color=text_color, size=12)),
                        ],
                        color=row_bg
                    )
                )

    def apply_all_filters():
        with global_lock:
            df_copy = global_df.copy()
        df_filtered = apply_filters_to_df(df_copy)
        update_stats(df_filtered)
        update_table(df_filtered)
        update_live_logs_table()
        update_small_chart()

    # ------------- Buttons / Fields -------------
    def create_styled_button(text, icon, on_click_handler=None):
        btn = ft.ElevatedButton(
            text,
            icon=icon,
            bgcolor="transparent",
            color=text_color,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                elevation=5,
                animation_duration=300,
            ),
            on_click=on_click_handler
        )
        return btn

    def create_styled_field(label, hint_text, width):
        return ft.TextField(
            label=label,
            hint_text=hint_text,
            width=width,
            border_color=accent_color,
            color=text_color,
            border_radius=8,
            label_style=ft.TextStyle(color=text_color),
            cursor_color=accent_color,
            focused_border_color=accent_color,
            focused_color=text_color,
        )

    load_button = create_styled_button("Load File", ft.Icons.UPLOAD_FILE)
    reset_button = create_styled_button("Reset", ft.Icons.RESTART_ALT)
    export_button = create_styled_button("Export", ft.Icons.DOWNLOAD)

    search_field = create_styled_field("Search in Messages", "Type to filter by text...", 300)

    quick_filter_dropdown = ft.Dropdown(
        label="Time Filter",
        options=[
            ft.dropdown.Option("Custom"),
            ft.dropdown.Option("Last Hour"),
            ft.dropdown.Option("Last 24 Hours"),
            ft.dropdown.Option("Last 7 Days"),
            ft.dropdown.Option("Last 30 Days"),
        ],
        value="Custom",
        width=200,
        border_color=accent_color,
        color=text_color,
        focused_border_color=accent_color,
        focused_color=text_color,
    )

    start_label = ft.Text("Start: Not Set", color=text_color, weight=ft.FontWeight.BOLD)
    end_label = ft.Text("End: Not Set", color=text_color, weight=ft.FontWeight.BOLD)

    script_field = create_styled_field("Script Name", "Enter script...", 200)
    module_field = create_styled_field("Module Name", "Enter module...", 200)
    message_field = create_styled_field("Message (Regex)", "Enter regex...", 300)

    level_dropdown = ft.Dropdown(
        label="Log Level",
        options=[
            ft.dropdown.Option(""),
            ft.dropdown.Option("INFO"),
            ft.dropdown.Option("DEBUG"),
            ft.dropdown.Option("WARNING"),
            ft.dropdown.Option("ERROR"),
            ft.dropdown.Option("CRITICAL")
        ],
        value="",
        width=150,
        border_color=accent_color,
        color=text_color,
        focused_border_color=accent_color,
        focused_color=text_color,
    )

    apply_filter_button = create_styled_button("Apply", ft.Icons.FILTER_LIST)

    advanced_filters_container = ft.Column(visible=False, controls=[
        ft.Row([script_field, module_field, message_field, level_dropdown])
    ])

    expand_filters_button = ft.IconButton(
        icon=ft.Icons.ARROW_DROP_DOWN,
        icon_color=accent_color,
        tooltip="Show Advanced Filters",
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            bgcolor=Colors.with_opacity(0.2, accent_color),
        )
    )

    def toggle_advanced_filters(e):
        advanced_filters_container.visible = not advanced_filters_container.visible
        if advanced_filters_container.visible:
            expand_filters_button.icon = ft.Icons.ARROW_DROP_UP
            expand_filters_button.tooltip = "Hide Advanced Filters"
        else:
            expand_filters_button.icon = ft.Icons.ARROW_DROP_DOWN
            expand_filters_button.tooltip = "Show Advanced Filters"
        expand_filters_button.update()
        advanced_filters_container.update()

    expand_filters_button.on_click = toggle_advanced_filters

    file_picker = ft.FilePicker()
    def file_picker_result(e: ft.FilePickerResultEvent):
        nonlocal log_file_path, global_df
        if e.files:
            log_file_path = e.files[0].path
            lines = read_all_lines(log_file_path)
            df_part = build_df_from_lines(lines)
            with global_lock:
                global_df = df_part
            apply_all_filters()
    file_picker.on_result = file_picker_result

    def load_button_click(e):
        file_picker.pick_files(allow_multiple=False)
    load_button.on_click = load_button_click

    def reset_filters_click(e):
        nonlocal start_datetime, end_datetime
        script_field.value = ""
        module_field.value = ""
        message_field.value = ""
        level_dropdown.value = ""
        quick_filter_dropdown.value = "Custom"
        start_label.value = "Start: Not Set"
        end_label.value = "End: Not Set"
        search_field.value = ""
        start_datetime = None
        end_datetime = None

        script_field.update()
        module_field.update()
        message_field.update()
        level_dropdown.update()
        quick_filter_dropdown.update()
        start_label.update()
        end_label.update()
        search_field.update()

        apply_all_filters()
    reset_button.on_click = reset_filters_click

    def export_logs_click(e):
        with global_lock:
            df_copy = global_df.copy()
        df_filtered = apply_filters_to_df(df_copy)
        if df_filtered.empty:
            print("No logs to export.")
            return
        try:
            df_copy = df_filtered.copy()
            df_copy["timestamp"] = df_copy["timestamp"].apply(lambda t: t.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(t) else "")
            export_path = "exported_logs.csv"
            df_copy.to_csv(export_path, index=False)
            print(f"Exported logs to {export_path}.")
        except Exception as ex:
            print(f"Export error: {ex}")
    export_button.on_click = export_logs_click

    def apply_filter_button_click(e):
        apply_all_filters()
    apply_filter_button.on_click = apply_filter_button_click

    def quick_filter_changed(e):
        nonlocal start_datetime, end_datetime
        now = datetime.now()
        if quick_filter_dropdown.value == "Last Hour":
            start_datetime = now - timedelta(hours=1)
            end_datetime = now
        elif quick_filter_dropdown.value == "Last 24 Hours":
            start_datetime = now - timedelta(days=1)
            end_datetime = now
        elif quick_filter_dropdown.value == "Last 7 Days":
            start_datetime = now - timedelta(days=7)
            end_datetime = now
        elif quick_filter_dropdown.value == "Last 30 Days":
            start_datetime = now - timedelta(days=30)
            end_datetime = now
        else:
            start_datetime = None
            end_datetime = None

        if start_datetime and end_datetime:
            start_label.value = f"Start: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            end_label.value = f"End: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            start_label.value = "Start: Not Set"
            end_label.value = "End: Not Set"

        start_label.update()
        end_label.update()
        apply_all_filters()
    quick_filter_dropdown.on_change = quick_filter_changed
    search_field.on_change = lambda e: apply_all_filters()

    # Create a styled container for filters
    filters_container = ft.Container(
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row([load_button, reset_button, export_button, expand_filters_button]),
                ft.Row([search_field, quick_filter_dropdown, apply_filter_button]),
                ft.Row([start_label, end_label]),
                advanced_filters_container,
            ]
        ),
        padding=20,
        border_radius=15,
        bgcolor=glass_bgcolor,
        blur=container_blur,
        shadow=container_shadow,
    )

    # Layout top row: stats + filters
    left_column = ft.Column(
        spacing=15,
        controls=[
            filters_container,
            stats_row,
        ]
    )

    top_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            left_column,
            ft.Container(width=30),
            small_chart_container
        ]
    )

    # Create glowing divider like in network monitor
    glowing_divider = ft.Container(
        content=ft.Divider(height=0, color=accent_color),
        alignment=ft.alignment.center,
        width=2000,
        shadow=BoxShadow(
            spread_radius=1,
            blur_radius=8,
            color=accent_color,
            offset=Offset(0, 0),
            blur_style=ShadowBlurStyle.OUTER,
        ),
    )

    # Create styled tabs container
    table_tab = ft.Tab(
        text="Log Table",
        icon=ft.Icons.VIEW_LIST,
        content=ft.Container(
            content=data_table,
            bgcolor=glass_bgcolor,
            blur=container_blur,
            shadow=container_shadow,
            border_radius=15,
            padding=15,
            expand=True,
        )
    )

    live_logs_tab = ft.Tab(
        text="Live Logs",
        icon=ft.Icons.LIVE_TV,
        content=ft.Container(
            content=live_logs_table,
            bgcolor=glass_bgcolor,
            blur=container_blur,
            shadow=container_shadow,
            border_radius=15,
            padding=15,
            expand=True,
        )
    )

    tabs_control = ft.Tabs(
        selected_index=0,
        tabs=[table_tab, live_logs_tab],
        expand=True
    )

    # Status text
    status_text = ft.Text("Log Analytics Ready", color=accent_color, size=12, weight=ft.FontWeight.BOLD)

    main_col = ft.Column(
        spacing=15,
        expand=True,
        controls=[
            top_row,
            glowing_divider,
            tabs_control,
            status_text
        ],
    )

    # Create a gradient background effect like in the network monitoring tool
    # with glass effect applied to the main container
    layout = ft.Container(
        content=main_col,
        expand=True,
        bgcolor=glass_bgcolor,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=[
                "#0B0F19",  # Dark blue at top
                "#101726",  # Slightly lighter in middle
                "#192338"   # Even lighter at bottom for depth
            ],
        ),
        blur=container_blur,
        shadow=container_shadow,
        border_radius=15,
        padding=15
    )

    # Use a normal background thread for live logs
    def refresh_live_logs_loop():
        nonlocal log_file_path
        while True:
            time.sleep(3)
            if log_file_path:
                try:
                    lines = read_all_lines(log_file_path)
                    last_50 = lines[-50:] if len(lines) >= 50 else lines
                    with global_lock:
                        live_logs_buffer.clear()
                        live_logs_buffer.extend(last_50)
                    update_live_logs_table()
                    update_small_chart()
                    status_text.value = f"Log file: {os.path.basename(log_file_path)} - Last updated: {datetime.now().strftime('%H:%M:%S')}"
                    status_text.update()
                except Exception as ex:
                    print("Error refreshing live logs:", ex)
                    status_text.value = f"Error: {ex}"
                    status_text.update()

    def init_logs_analytics(page: ft.Page):
        """
        Attach the file picker, start the background logs thread, do initial UI update.
        """
        page.overlay.append(file_picker)
        t = threading.Thread(target=refresh_live_logs_loop, daemon=True)
        t.start()
        page.update()

    return layout, init_logs_analytics