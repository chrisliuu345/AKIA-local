import threading
import time

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGroupBox, QTabWidget,
    QPlainTextEdit, QLineEdit, QGridLayout, QFrame,
    QSplitter, QSizePolicy, QCheckBox, QMessageBox,
    QInputDialog, QApplication, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QColor

from core.i18n import i18n
from core.devices import (
    DeviceRegistry, DeviceState, MessageType, discover_devices,
    probe_network_device,
    Device, Esp32InputDevice, Esp32OutputDevice, MaixcamVisionDevice,
    DeviceMonitor,
)
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
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


class _ElidedLabel(QLabel):
    """QLabel that elides its text (PySide6 QLabel has no setTextElideMode)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def set_full_text(self, text: str):
        self._full = text
        self._apply()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply()

    def _apply(self):
        fm = self.fontMetrics()
        width = max(8, self.width())
        super().setText(fm.elidedText(self._full, Qt.ElideMiddle, width))


class DeviceCard(QFrame):
    clicked = Signal(str)
    monitor_stop_requested = Signal(str)
    monitor_resume_requested = Signal(str)

    def __init__(self, device: Device, monitoring: bool = True, parent=None):
        super().__init__(parent)
        self.device_id = device.device_id
        self._selected = False
        self._monitoring = monitoring
        self._setup_ui(device)

    def _setup_ui(self, device: Device):
        tc = theme_colors(self)
        self.setFixedWidth(240)
        self.setCursor(Qt.PointingHandCursor)
        self._set_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        icon = QLabel(DEVICE_ICONS.get(device.device_type, "🔌"))
        icon.setFont(QFont("Segoe UI Emoji", 16))
        icon.setStyleSheet("background: transparent;")
        top.addWidget(icon)
        name = _ElidedLabel(device.display_name)
        name.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        name.setStyleSheet(f"color: {tc['text_primary']}; background: transparent;")
        name.setToolTip(device.display_name)
        top.addWidget(name, 1)
        badge = QLabel(DEVICE_BADGE.get(device.device_type, "UNKNOWN"))
        badge.setFont(QFont("Microsoft YaHei", 8))
        badge.setStyleSheet(
            f"color: {tc['text_muted']}; background: {tc['bg_body']}; "
            f"border-radius: 4px; padding: 1px 6px;"
        )
        top.addWidget(badge)
        layout.addLayout(top)

        color_map = {
            DeviceState.ONLINE: "#4caf50",
            DeviceState.OFFLINE: "#ff9800",
            DeviceState.ERROR: "#f44336",
            DeviceState.DISCOVERED: "#2196f3",
        }
        state_color = color_map.get(device.state, "#888")
        status_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {state_color}; font-size: 13px; background: transparent;")
        status_row.addWidget(dot)
        status_text = {
            DeviceState.ONLINE: i18n.tr("device.status_online"),
            DeviceState.OFFLINE: i18n.tr("device.status_offline"),
            DeviceState.ERROR: i18n.tr("device.status_error"),
            DeviceState.DISCOVERED: i18n.tr("device.status_online"),
        }.get(device.state, "?")
        status_lbl = QLabel(status_text)
        status_lbl.setFont(QFont("Microsoft YaHei", 9))
        status_lbl.setStyleSheet(f"color: {state_color}; background: transparent;")
        status_row.addWidget(status_lbl)

        parts = [device.port] if device.port else []
        hb = time.time() - device.last_heartbeat if device.last_heartbeat else 0
        if hb > 0:
            parts.append(i18n.tr("device.heartbeat_ago").format(n=int(hb)))
        if parts:
            info_lbl = QLabel(" · ".join(parts))
            info_lbl.setFont(QFont("Microsoft YaHei", 8))
            info_lbl.setStyleSheet(f"color: {tc['text_dim']}; background: transparent;")
            status_row.addWidget(info_lbl)
        status_row.addStretch()
        layout.addLayout(status_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._stop_btn = QPushButton(i18n.tr("device.monitor_stop"))
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_body']}; color: {tc['text_secondary']}; "
            f"border: 1px solid {tc['border']}; border-radius: 4px; padding: 3px 8px; }}"
            f"QPushButton:hover {{ border-color: {tc['accent']}; }}"
            f"QPushButton:disabled {{ color: {tc['text_dim']}; border-color: {tc['border']}; }}"
        )
        self._resume_btn = QPushButton(i18n.tr("device.monitor_resume"))
        self._resume_btn.setCursor(Qt.PointingHandCursor)
        self._resume_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_body']}; color: {tc['accent_bright']}; "
            f"border: 1px solid {tc['border']}; border-radius: 4px; padding: 3px 8px; }}"
            f"QPushButton:hover {{ border-color: {tc['accent']}; }}"
            f"QPushButton:disabled {{ color: {tc['text_dim']}; border-color: {tc['border']}; }}"
        )
        for b in (self._stop_btn, self._resume_btn):
            b.setFont(QFont("Microsoft YaHei", 9))
        self._stop_btn.clicked.connect(lambda: self.monitor_stop_requested.emit(self.device_id))
        self._resume_btn.clicked.connect(lambda: self.monitor_resume_requested.emit(self.device_id))
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._resume_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self._update_monitor_buttons()

    def _set_style(self, selected: bool):
        tc = theme_colors(self)
        if selected:
            accent = QColor(tc["accent"])
            accent.setAlpha(22)
            self.setStyleSheet(
                f"QFrame {{ background-color: {accent.name(QColor.HexArgb)}; "
                f"border: 1px solid {tc['accent']}; border-radius: 8px; }}"
            )
        else:
            self.setStyleSheet(
                f"QFrame {{ background-color: {tc['bg_card']}; border: 1px solid {tc['border']}; "
                f"border-radius: 8px; }}"
                f"QFrame:hover {{ border-color: {tc['accent']}; }}"
            )

    def set_selected(self, selected: bool):
        if selected != self._selected:
            self._selected = selected
            self._set_style(selected)

    def set_monitoring(self, monitoring: bool):
        if monitoring != self._monitoring:
            self._monitoring = monitoring
            self._update_monitor_buttons()

    def _update_monitor_buttons(self):
        self._stop_btn.setEnabled(self._monitoring)
        self._resume_btn.setEnabled(not self._monitoring)

    def mousePressEvent(self, event):
        self.clicked.emit(self.device_id)
        super().mousePressEvent(event)


class DeviceTab(BaseAnalysisTab):
    update_devices = Signal(object)
    monitor_event = Signal(str, str, object)
    network_device_found = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = DeviceRegistry(on_device_changed=self._on_device_state_changed)
        self._monitor = DeviceMonitor(
            on_event=lambda did, ev, pl: self.monitor_event.emit(did, ev, pl)
        )
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

        self.add_network_btn = QPushButton(i18n.tr("device.add_network"))
        self.add_network_btn.setFixedHeight(32)
        self.add_network_btn.setCursor(Qt.PointingHandCursor)
        self.add_network_btn.setStyleSheet(BUTTON_SECONDARY)
        toolbar.addWidget(self.add_network_btn)

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

        self._preview_table = QTableWidget(0, 0)
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview_table.setStyleSheet(
            f"background: {tc['bg_body']}; color: {tc['text_primary']}; "
            f"gridline-color: {tc['border']};"
        )
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_tabs.addTab(self._preview_table, i18n.tr("device.detail.data_preview"))

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
        self._send_btn.setStyleSheet(BUTTON_SECONDARY)
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
        self._import_btn.setStyleSheet(BUTTON_SECONDARY)
        self._import_btn.setVisible(False)
        layout.addWidget(self._import_btn)

    def _connect_signals(self):
        self.auto_check.toggled.connect(self._on_auto_toggle)
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.add_network_btn.clicked.connect(self._on_add_network)
        self._send_btn.clicked.connect(self._on_send_command)
        self._cmd_input.returnPressed.connect(self._send_btn.click)
        self._import_btn.clicked.connect(self._on_import_data)
        self.update_devices.connect(self._on_update_devices)
        self.monitor_event.connect(self._on_monitor_event)
        self.network_device_found.connect(self._on_network_device_found)
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(1000)
        self._preview_timer.timeout.connect(self._refresh_preview)
        self._preview_timer.start()

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
            self._add_device_info(info)
        self._rebuild_cards()
        if found:
            self._stop_discovery()

    def _add_device_info(self, info):
        """将 DeviceInfo 注册进 registry 并 attach 到 monitor（去重）。"""
        if self._registry.get(info.device_id):
            self._registry.set_online(info.device_id)
            return
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
        self._monitor.start()
        if dev.monitoring:
            self._monitor.attach(dev)

    def _on_add_network(self):
        text, ok = QInputDialog.getText(
            self, i18n.tr("device.add_network_title"),
            i18n.tr("device.add_network_prompt"), text="192.168.50.46:9000")
        address = text.strip() if ok else ""
        if not address:
            return
        try:
            host, port_s = address.rsplit(":", 1)
            int(port_s)
            if not host:
                return
        except ValueError:
            QMessageBox.warning(self, i18n.tr("device.add_network_title"),
                                i18n.tr("device.add_network_invalid"))
            return
        self.add_network_btn.setEnabled(False)

        def _run():
            try:
                info = probe_network_device(address)
            except Exception:
                info = None
            self.network_device_found.emit(info)

        threading.Thread(target=_run, daemon=True, name="network-probe").start()

    def _on_network_device_found(self, info):
        self.add_network_btn.setEnabled(True)
        if info is None:
            QMessageBox.warning(self, i18n.tr("device.add_network_title"),
                                i18n.tr("device.add_network_fail"))
            return
        self._add_device_info(info)
        self._registry.save_persistent()
        self._rebuild_cards()

    def _on_monitor_event(self, device_id: str, event: str, payload: dict):
        dev = self._registry.get(device_id)
        if not dev:
            return
        if event in (MessageType.HELLO, MessageType.DATA, MessageType.META, MessageType.PONG):
            if dev.state != DeviceState.ONLINE:
                self._registry.set_online(device_id)
        elif event == MessageType.ACK:
            if dev.state != DeviceState.ONLINE:
                self._registry.set_online(device_id)
            if device_id == self._selected_device_id:
                result = payload.get("result", payload.get("error", ""))
                if result:
                    self._output_text.appendPlainText(f"✓ {result}")
                else:
                    self._output_text.appendPlainText("✓ ack")
        elif event == "error":
            self._registry.set_error(device_id)
        elif event == "timeout":
            if dev.state == DeviceState.ONLINE:
                self._registry.set_offline(device_id)

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
            self.card_grid.addWidget(self._empty_hint, 0, 0)
            self._empty_hint.show()
            return

        self.card_grid.removeWidget(self._empty_hint)
        self._empty_hint.hide()

        for i, (did, dev) in enumerate(devices.items()):
            card = DeviceCard(dev, monitoring=dev.monitoring)
            card.clicked.connect(self._on_card_clicked)
            card.monitor_stop_requested.connect(self._on_stop_monitoring)
            card.monitor_resume_requested.connect(self._on_resume_monitoring)
            card.set_selected(did == self._selected_device_id)
            self._card_widgets[did] = card
            row, col = divmod(i, 3)
            self.card_grid.addWidget(card, row, col)

    def _on_stop_monitoring(self, device_id: str):
        dev = self._registry.get(device_id)
        if not dev or not dev.monitoring:
            return
        dev.monitoring = False
        self._monitor.detach(dev)
        card = self._card_widgets.get(device_id)
        if card:
            card.set_monitoring(False)

    def _on_resume_monitoring(self, device_id: str):
        dev = self._registry.get(device_id)
        if not dev or dev.monitoring:
            return
        if self._monitor.attach(dev):
            dev.monitoring = True
            card = self._card_widgets.get(device_id)
            if card:
                card.set_monitoring(True)
        else:
            QMessageBox.warning(
                self, i18n.tr("device.monitor_attach_failed_title"),
                i18n.tr("device.monitor_attach_failed").format(name=dev.display_name),
            )

    def _on_card_clicked(self, device_id: str):
        self._selected_device_id = device_id
        for did, card in self._card_widgets.items():
            card.set_selected(did == device_id)
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

        self._refresh_preview()

        self._output_text.clear()
        if isinstance(dev, Esp32OutputDevice):
            for ts, cmd in dev.command_history[:10]:
                self._output_text.appendPlainText(f"[{ts:.1f}] > {cmd}")
            for ack in dev.ack_history[:10]:
                result = ack.get("result", ack.get("error", ""))
                ts = ack.get("timestamp", 0)
                line = f"✓ {result}" if result else "✓ ack"
                if ts:
                    line = f"[{ts:.1f}] {line}"
                self._output_text.appendPlainText(line)

        self._recognition_list.clear()
        if isinstance(dev, MaixcamVisionDevice):
            for rec in dev.get_recent_records(10):
                conf = rec.get("confidence", 0)
                cls = rec.get("class", "?")
                self._recognition_list.appendPlainText(
                    f"{cls} (置信度: {conf:.2f})"
                )

        self.detail_tabs.setCurrentIndex(0)

    def _refresh_preview(self):
        if not self._selected_device_id:
            return
        dev = self._registry.get(self._selected_device_id)
        if not isinstance(dev, Esp32InputDevice):
            return
        labels = dev.channel_labels()
        samples = dev.get_recent_data(20)
        if not samples:
            self._preview_table.setColumnCount(1)
            self._preview_table.setRowCount(1)
            item = QTableWidgetItem("暂无数据")
            item.setTextAlignment(Qt.AlignCenter)
            self._preview_table.setItem(0, 0, item)
            self._preview_table.setHorizontalHeaderLabels([""])
            return
        width = max(len(labels), len(samples[0]))
        labels = labels + [f"CH{i}" for i in range(len(labels), width)]
        self._preview_table.setColumnCount(width)
        self._preview_table.setHorizontalHeaderLabels(labels)
        self._preview_table.setRowCount(len(samples))
        for r, sample in enumerate(samples):
            for c in range(width):
                v = sample[c] if c < len(sample) else None
                text = f"{v:.4f}" if isinstance(v, (int, float)) else str(v)
                self._preview_table.setItem(r, c, QTableWidgetItem(text))

    def _on_send_command(self):
        cmd = self._cmd_input.text().strip()
        if not cmd or not self._selected_device_id:
            return
        dev = self._registry.get(self._selected_device_id)
        if isinstance(dev, Esp32OutputDevice):
            try:
                dev.send_command(cmd)
                self._output_text.appendPlainText(f"> {cmd}")
                self._output_text.appendPlainText("⏳ 等待 ack...")
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
        samples = dev.get_recent_data(50)
        if not samples:
            QMessageBox.information(self, "提示", "该设备暂无数据")
            return
        import pandas as pd
        if dev.channels:
            columns = [c.get("name", f"CH{i}") for i, c in enumerate(dev.channels)]
            width = max(len(columns), len(samples[0]))
            columns = columns + [f"CH{i}" for i in range(len(columns), width)]
        else:
            columns = [f"CH{i}" for i in range(len(samples[0]))]
        df = pd.DataFrame(samples, columns=columns)
        parent = self.window()
        if parent is None or not hasattr(parent, "_route_sheets_to_tabs"):
            return
        raw_data = {"设备采样": df}
        parent.current_data = {
            "file_path": f"device://{dev.device_id}",
            "raw_data": raw_data,
        }
        parent._route_sheets_to_tabs(raw_data)
        QMessageBox.information(
            self, "导入完成",
            f"已导入 {len(samples)} 条采样（{len(columns)} 通道），请切换到其他分析 Tab 查看"
        )

    def closeEvent(self, event):
        self._monitor.stop()
        self._registry.stop_all()
        super().closeEvent(event)

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