import threading
import time

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGroupBox, QTabWidget,
    QPlainTextEdit, QLineEdit, QGridLayout, QFrame,
    QSplitter, QSizePolicy, QCheckBox, QMessageBox,
    QInputDialog, QApplication,
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont

from core.i18n import i18n
from core.devices import (
    DeviceRegistry, DeviceState, discover_devices,
    Device, Esp32InputDevice, Esp32OutputDevice, MaixcamVisionDevice,
)
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH
from ui.tabs.base_tab import BaseAnalysisTab


DEVICE_ICONS = {
    "esp32_in": "📥",
    "esp32_out": "📤",
    "maixcam": "📷",
}
DEVICE_BADGE = {
    "esp32_in": "ESP32-IN",
    "esp32_out": "ESP32-OUT",
    "maixcam": "MAIXCAM",
}


class DeviceCard(QFrame):
    clicked = Signal(str)

    def __init__(self, device: Device, parent=None):
        super().__init__(parent)
        self.device_id = device.device_id
        self._setup_ui(device)

    def _setup_ui(self, device: Device):
        tc = theme_colors(self)
        self.setFixedSize(220, 110)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QFrame {{ background-color: {tc['bg_card']}; border: 1px solid {tc['border']}; "
            f"border-radius: 8px; padding: 8px; }}"
            f"QFrame:hover {{ border-color: {tc['accent']}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        icon = QLabel(DEVICE_ICONS.get(device.device_type, "🔌"))
        icon.setFont(QFont("Segoe UI Emoji", 18))
        top.addWidget(icon)
        name = QLabel(device.display_name)
        name.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        name.setStyleSheet(f"color: {tc['text_primary']}; background: transparent;")
        top.addWidget(name, 1)
        badge = QLabel(DEVICE_BADGE.get(device.device_type, "UNKNOWN"))
        badge.setFont(QFont("Microsoft YaHei", 8))
        badge.setStyleSheet(
            f"color: {tc['text_muted']}; background: {tc['bg_body']}; "
            f"border-radius: 4px; padding: 1px 6px;"
        )
        top.addWidget(badge)
        layout.addLayout(top)

        status_row = QHBoxLayout()
        color_map = {
            DeviceState.ONLINE: "#4caf50",
            DeviceState.OFFLINE: "#ff9800",
            DeviceState.ERROR: "#f44336",
            DeviceState.DISCOVERED: "#2196f3",
        }
        dot_color = color_map.get(device.state, "#888")
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 14px; background: transparent;")
        status_row.addWidget(dot)
        status_text = {
            DeviceState.ONLINE: i18n.tr("device.status_online"),
            DeviceState.OFFLINE: i18n.tr("device.status_offline"),
            DeviceState.ERROR: i18n.tr("device.status_error"),
            DeviceState.DISCOVERED: i18n.tr("device.status_online"),
        }.get(device.state, "?")
        status_lbl = QLabel(status_text)
        status_lbl.setFont(QFont("Microsoft YaHei", 9))
        status_lbl.setStyleSheet(f"color: {tc['text_secondary']}; background: transparent;")
        status_row.addWidget(status_lbl)
        status_row.addStretch()
        port_lbl = QLabel(device.port)
        port_lbl.setFont(QFont("Consolas", 8))
        port_lbl.setStyleSheet(f"color: {tc['text_dim']}; background: transparent;")
        status_row.addWidget(port_lbl)
        layout.addLayout(status_row)

        hb = time.time() - device.last_heartbeat if device.last_heartbeat else 0
        if hb > 0:
            ts = QLabel(f"心跳 {int(hb)}s前")
            ts.setFont(QFont("Microsoft YaHei", 8))
            ts.setStyleSheet(f"color: {tc['text_muted']}; background: transparent;")
            layout.addWidget(ts)

    def mousePressEvent(self, event):
        self.clicked.emit(self.device_id)
        super().mousePressEvent(event)


class DeviceTab(BaseAnalysisTab):
    update_devices = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = DeviceRegistry(on_device_changed=self._on_device_state_changed)
        self._selected_device_id = None
        self._card_widgets: dict[str, DeviceCard] = {}
        self._discovery_running = False
        self._setup_ui()
        self._connect_signals()
        self._load_persistent()

    def _setup_ui(self):
        tc = theme_colors(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel(i18n.tr("device.title"))
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']}; background: transparent;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.auto_check = QCheckBox(i18n.tr("device.auto_discover"))
        self.auto_check.setFont(QFont("Microsoft YaHei", 10))
        self.auto_check.setStyleSheet(f"color: {tc['text_primary']};")
        toolbar.addWidget(self.auto_check)

        self.refresh_btn = QPushButton(i18n.tr("device.refresh"))
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; "
            f"border: none; border-radius: 4px; padding: 4px 16px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
        )
        toolbar.addWidget(self.refresh_btn)

        self.online_label = QLabel(i18n.tr("device.online_count").format(online=0, total=0))
        self.online_label.setFont(QFont("Microsoft YaHei", 10))
        self.online_label.setStyleSheet(f"color: {tc['text_secondary']};")
        toolbar.addWidget(self.online_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        card_scroll = QScrollArea()
        card_scroll.setWidgetResizable(True)
        card_scroll.setFrameShape(QFrame.NoFrame)
        card_container = QWidget()
        self.card_grid = QGridLayout(card_container)
        self.card_grid.setContentsMargins(4, 4, 4, 4)
        self.card_grid.setSpacing(8)
        self.card_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._empty_hint = QLabel(i18n.tr("device.no_devices"))
        self._empty_hint.setFont(QFont("Microsoft YaHei", 11))
        self._empty_hint.setStyleSheet(f"color: {tc['text_muted']}; background: transparent;")
        self._empty_hint.setAlignment(Qt.AlignCenter)
        self.card_grid.addWidget(self._empty_hint, 0, 0)
        card_scroll.setWidget(card_container)
        splitter.addWidget(card_scroll)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {tc['border']}; "
            f"background: {tc['bg_card']}; border-radius: 4px; }}"
            f"QTabBar::tab {{ color: {tc['text_secondary']}; "
            f"background: transparent; padding: 6px 14px; }}"
            f"QTabBar::tab:selected {{ color: {tc['accent_bright']}; }}"
        )
        self._event_log = QPlainTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.setStyleSheet(f"background: {tc['bg_body']}; color: {tc['text_primary']};")
        self.detail_tabs.addTab(self._event_log, i18n.tr("device.detail.events"))

        self._data_preview = QPlainTextEdit()
        self._data_preview.setReadOnly(True)
        self._data_preview.setStyleSheet(f"background: {tc['bg_body']}; color: {tc['text_primary']};")
        self.detail_tabs.addTab(self._data_preview, i18n.tr("device.detail.data_preview"))

        self._output_console = QWidget()
        oc_layout = QVBoxLayout(self._output_console)
        self._output_text = QPlainTextEdit()
        self._output_text.setReadOnly(True)
        self._output_text.setStyleSheet(f"background: {tc['bg_body']}; color: {tc['text_primary']};")
        oc_layout.addWidget(self._output_text, 1)
        cmd_row = QHBoxLayout()
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText(i18n.tr("device.detail.placeholder"))
        self._cmd_input.setStyleSheet(
            f"background: {tc['bg_body']}; color: {tc['text_primary']}; "
            f"border: 1px solid {tc['border']}; border-radius: 4px; padding: 4px 8px;"
        )
        cmd_row.addWidget(self._cmd_input, 1)
        self._send_btn = QPushButton(i18n.tr("device.detail.send"))
        self._send_btn.setFixedHeight(32)
        self._send_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        cmd_row.addWidget(self._send_btn)
        oc_layout.addLayout(cmd_row)
        self.detail_tabs.addTab(self._output_console, i18n.tr("device.detail.output_console"))

        self._recognition_list = QPlainTextEdit()
        self._recognition_list.setReadOnly(True)
        self._recognition_list.setStyleSheet(f"background: {tc['bg_body']}; color: {tc['text_primary']};")
        self.detail_tabs.addTab(self._recognition_list, i18n.tr("device.detail.recognition"))

        self._detail_placeholder = QLabel(i18n.tr("device.detail.no_selection"))
        self._detail_placeholder.setFont(QFont("Microsoft YaHei", 11))
        self._detail_placeholder.setStyleSheet(f"color: {tc['text_muted']};")
        self._detail_placeholder.setAlignment(Qt.AlignCenter)
        self.detail_tabs.addTab(self._detail_placeholder, i18n.tr("device.detail.no_selection"))
        self.detail_tabs.setCurrentWidget(self._detail_placeholder)

        splitter.addWidget(self.detail_tabs)
        splitter.setSizes([400, 500])
        layout.addWidget(splitter, 1)

        self._import_btn = QPushButton(i18n.tr("device.detail.import"))
        self._import_btn.setFixedHeight(36)
        self._import_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self._import_btn.setVisible(False)
        layout.addWidget(self._import_btn)

    def _connect_signals(self):
        self.auto_check.toggled.connect(self._on_auto_toggle)
        self.refresh_btn.clicked.connect(self._on_refresh)
        self._send_btn.clicked.connect(self._on_send_command)
        self._cmd_input.returnPressed.connect(self._send_btn.click)
        self._import_btn.clicked.connect(self._on_import_data)
        self.update_devices.connect(self._on_update_devices)

    def _on_auto_toggle(self, enabled: bool):
        if enabled:
            self._start_discovery()
        else:
            self._stop_discovery()

    def _start_discovery(self):
        if self._discovery_running:
            return
        self._discovery_running = True
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop, daemon=True,
            name="device-discovery"
        )
        self._discovery_thread.start()

    def _stop_discovery(self):
        self._discovery_running = False

    def _discovery_loop(self):
        while self._discovery_running:
            try:
                found = discover_devices(timeout=0.3)
                self.update_devices.emit(found)
            except Exception:
                pass
            for _ in range(30):
                if not self._discovery_running:
                    return
                time.sleep(0.1)

    def _on_update_devices(self, found: list):
        for info in found:
            if self._registry.get(info.device_id):
                self._registry.set_online(info.device_id)
            else:
                dev_type = info.device_type
                if dev_type == "esp32_in":
                    dev = Esp32InputDevice(info.device_id, info.port, info.baudrate, info.fw_version)
                elif dev_type == "esp32_out":
                    dev = Esp32OutputDevice(info.device_id, info.port, info.baudrate, info.fw_version)
                elif dev_type == "maixcam":
                    dev = MaixcamVisionDevice(info.device_id, info.port, info.baudrate, info.fw_version)
                else:
                    dev = Device(info.device_id, dev_type, info.port, info.baudrate, info.fw_version)
                self._registry.add(dev)
        self._rebuild_cards()

    def _on_refresh(self):
        if self._discovery_running:
            self._stop_discovery()
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("...")
        QApplication.processEvents()

        def _run():
            try:
                found = discover_devices(timeout=0.5)
                self.update_devices.emit(found)
            finally:
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText(i18n.tr("device.refresh"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_device_state_changed(self, device_id: str, state: DeviceState):
        self._rebuild_cards()

    def _rebuild_cards(self):
        for w in self._card_widgets.values():
            w.setParent(None)
        self._card_widgets.clear()

        devices = self._registry.devices
        total = len(devices)
        online = sum(1 for d in devices.values() if d.state == DeviceState.ONLINE)
        self.online_label.setText(i18n.tr("device.online_count").format(online=online, total=total))

        if not devices:
            self._empty_hint = QLabel(i18n.tr("device.no_devices"))
            self._empty_hint.setFont(QFont("Microsoft YaHei", 11))
            tc = theme_colors(self)
            self._empty_hint.setStyleSheet(f"color: {tc['text_muted']}; background: transparent;")
            self._empty_hint.setAlignment(Qt.AlignCenter)
            self.card_grid.addWidget(self._empty_hint, 0, 0)
            return

        for i, (did, dev) in enumerate(devices.items()):
            card = DeviceCard(dev)
            card.clicked.connect(self._on_card_clicked)
            self._card_widgets[did] = card
            row, col = divmod(i, 3)
            self.card_grid.addWidget(card, row, col)

    def _on_card_clicked(self, device_id: str):
        self._selected_device_id = device_id
        dev = self._registry.get(device_id)
        if not dev:
            return
        self.detail_tabs.removeTab(self.detail_tabs.indexOf(self._detail_placeholder))
        self._update_detail(dev)
        self._import_btn.setVisible(isinstance(dev, Esp32InputDevice))

    def _update_detail(self, dev: Device):
        tc = theme_colors(self)
        self._event_log.clear()
        self._event_log.appendPlainText(f"设备: {dev.display_name} ({dev.device_id})")
        self._event_log.appendPlainText(f"类型: {dev.device_type}  端口: {dev.port}  固件: {dev.fw_version}")
        self._event_log.appendPlainText(f"状态: {dev.state.value}")

        self._data_preview.clear()
        if isinstance(dev, Esp32InputDevice):
            data = dev.get_recent_data(20)
            if data:
                self._data_preview.appendPlainText(
                    ", ".join(f"{v:.4f}" for v in data)
                )
            else:
                self._data_preview.appendPlainText("暂无数据")

        self._output_text.clear()
        if isinstance(dev, Esp32OutputDevice):
            for ts, cmd in dev.command_history[:10]:
                self._output_text.appendPlainText(f"[{ts:.1f}] {cmd}")

        self._recognition_list.clear()
        if isinstance(dev, MaixcamVisionDevice):
            for rec in dev.get_recent_records(10):
                conf = rec.get("confidence", 0)
                cls = rec.get("class", "?")
                self._recognition_list.appendPlainText(
                    f"{cls} (置信度: {conf:.2f})"
                )

        self.detail_tabs.setCurrentIndex(0)

    def _on_send_command(self):
        cmd = self._cmd_input.text().strip()
        if not cmd or not self._selected_device_id:
            return
        dev = self._registry.get(self._selected_device_id)
        if isinstance(dev, Esp32OutputDevice):
            try:
                dev.send_command(cmd)
                self._output_text.appendPlainText(f"> {cmd}")
                self._cmd_input.clear()
            except Exception as e:
                QMessageBox.warning(self, "指令错误", str(e))
        else:
            QMessageBox.information(self, "提示", "该设备不支持指令下发")

    def _on_import_data(self):
        if not self._selected_device_id:
            return
        dev = self._registry.get(self._selected_device_id)
        if not isinstance(dev, Esp32InputDevice):
            return
        data = dev.get_recent_data(50)
        if not data:
            QMessageBox.information(self, "提示", "该设备暂无数据")
            return
        import pandas as pd
        from core.session_manager import session_manager
        df = pd.DataFrame({"value": data})
        session_manager.set_current_data(
            raw_data={"device_data": df},
            file_path=f"device://{dev.device_id}",
        )
        QMessageBox.information(
            self, "导入完成",
            f"已导入 {len(data)} 条数据，请切换到其他分析 Tab 查看"
        )

    def _load_persistent(self):
        saved = self._registry.load_persistent()
        for item in saved:
            dtype = item.get("device_type", "unknown")
            did = item.get("device_id", "")
            if dtype == "esp32_in":
                dev = Esp32InputDevice(did, item.get("port", ""), item.get("baudrate", 115200))
            elif dtype == "esp32_out":
                dev = Esp32OutputDevice(did, item.get("port", ""), item.get("baudrate", 115200))
            elif dtype == "maixcam":
                dev = MaixcamVisionDevice(did, item.get("port", ""), item.get("baudrate", 115200))
            else:
                dev = Device(did, dtype, item.get("port", ""))
            dev.custom_name = item.get("custom_name", "")
            dev.state = DeviceState.OFFLINE
            self._registry.add(dev)
        self._rebuild_cards()