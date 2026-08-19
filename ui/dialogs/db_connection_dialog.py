"""
数据库连接对话框 — 连接配置 + 表选择 + 配置保存
"""

import json
import base64
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QListWidget,
    QListWidgetItem, QDialogButtonBox, QMessageBox, QSpinBox,
    QWidget, QFormLayout,
)
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QFont

from core.i18n import i18n
from core.sql_loader import SqlLoader, DEFAULT_PORTS
from ui.theme import colors as theme_colors


def _obscure(text: str) -> str:
    """加密密码 — Windows DPAPI 优先，失败降级 base64（兼容旧数据/异常场景）"""
    try:
        from core.secret_store import encrypt_secret
        return encrypt_secret(text)
    except Exception:
        return base64.b64encode(text.encode()).decode()


def _unobscure(text: str) -> str:
    """解密密码 — 支持 dpapi: 前缀与旧版无前缀 base64"""
    try:
        from core.secret_store import decrypt_secret
        return decrypt_secret(text)
    except Exception:
        try:
            return base64.b64decode(text.encode()).decode()
        except Exception:
            return ""


def _load_saved_configs() -> Dict[str, dict]:
    settings = QSettings("QA-Tool", "DBConnections")
    raw = settings.value("connections", "[]")
    try:
        return {c["name"]: c for c in json.loads(raw)}
    except Exception:
        return {}


def _save_configs(configs: Dict[str, dict]):
    settings = QSettings("QA-Tool", "DBConnections")
    settings.setValue("connections", json.dumps(list(configs.values()), ensure_ascii=False))


class DbConnectionDialog(QDialog):
    connection_established = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sql_loader = SqlLoader()
        self.saved_configs: Dict[str, dict] = _load_saved_configs()
        self.selected_tables: List[str] = []
        self._setup_ui()
        self._load_config_combo()

    def _setup_ui(self):
        tc = theme_colors()
        self.setWindowTitle(i18n.tr("db.connection_title"))
        self.setStyleSheet(f"background-color: {tc['bg_body']};")
        self.setMinimumSize(720, 560)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        saved_group = QGroupBox(i18n.tr("db.saved_configs"))
        saved_layout = QHBoxLayout(saved_group)
        self.config_combo = QComboBox()
        self.config_combo.setMinimumHeight(30)
        self.config_combo.currentIndexChanged.connect(self._on_config_selected)
        saved_layout.addWidget(self.config_combo, 1)
        btn_delete = QPushButton(i18n.tr("db.delete_config"))
        btn_delete.clicked.connect(self._on_delete_config)
        saved_layout.addWidget(btn_delete)
        layout.addWidget(saved_group)

        conn_group = QGroupBox(i18n.tr("db.connection_params"))
        form = QFormLayout(conn_group)
        form.setSpacing(6)

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["MySQL", "PostgreSQL", "SQL Server"])
        self.db_type_combo.setCurrentText("MySQL")
        self.db_type_combo.currentTextChanged.connect(self._on_db_type_changed)
        form.addRow(i18n.tr("db.db_type") + ":", self.db_type_combo)

        self.host_edit = QLineEdit("localhost")
        self.host_edit.setMinimumHeight(28)
        form.addRow(i18n.tr("db.host") + ":", self.host_edit)

        port_row = QHBoxLayout()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(3306)
        self.port_spin.setFixedWidth(100)
        port_row.addWidget(self.port_spin)
        port_row.addStretch()
        form.addRow(i18n.tr("db.port") + ":", port_row)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText(i18n.tr("db.database_ph"))
        self.database_edit.setMinimumHeight(28)
        form.addRow(i18n.tr("db.database") + ":", self.database_edit)

        self.user_edit = QLineEdit("root")
        self.user_edit.setMinimumHeight(28)
        form.addRow(i18n.tr("db.user") + ":", self.user_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(28)
        form.addRow(i18n.tr("db.password") + ":", self.password_edit)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton(i18n.tr("db.test_connection"))
        self.test_btn.setMinimumHeight(32)
        self.test_btn.clicked.connect(self._on_test_connection)
        test_row.addWidget(self.test_btn)
        self.conn_status = QLabel("")
        self.conn_status.setStyleSheet(f"color: {tc['text_muted']};")
        test_row.addWidget(self.conn_status, 1)
        form.addRow("", test_row)

        layout.addWidget(conn_group)

        table_group = QGroupBox(i18n.tr("db.select_tables"))
        table_layout = QVBoxLayout(table_group)
        self.table_list = QListWidget()
        self.table_list.setSelectionMode(QListWidget.MultiSelection)
        self.table_list.setMinimumHeight(150)
        self.table_list.setStyleSheet(
            f"QListWidget {{ background: {tc['bg_card']}; color: {tc['text_primary']}; "
            f"border: 1px solid {tc['border_light']}; }}"
            f"QListWidget::item:selected {{ background: {tc['accent']}; }}"
        )
        table_layout.addWidget(self.table_list)

        table_btn_row = QHBoxLayout()
        btn_select_all = QPushButton(i18n.tr("db.select_all"))
        btn_select_all.clicked.connect(self.table_list.selectAll)
        table_btn_row.addWidget(btn_select_all)
        btn_deselect_all = QPushButton(i18n.tr("db.deselect_all"))
        btn_deselect_all.clicked.connect(self.table_list.clearSelection)
        table_btn_row.addWidget(btn_deselect_all)
        table_btn_row.addStretch()
        btn_refresh = QPushButton(i18n.tr("db.refresh_tables"))
        btn_refresh.clicked.connect(self._on_refresh_tables)
        table_btn_row.addWidget(btn_refresh)
        table_layout.addLayout(table_btn_row)

        layout.addWidget(table_group, 1)

        save_row = QHBoxLayout()
        self.save_check = QCheckBox(i18n.tr("db.save_config"))
        save_row.addWidget(self.save_check)
        self.config_name_edit = QLineEdit()
        self.config_name_edit.setPlaceholderText(i18n.tr("db.config_name_ph"))
        self.config_name_edit.setMinimumHeight(28)
        save_row.addWidget(self.config_name_edit, 1)
        layout.addLayout(save_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_db_type_changed(self, db_type: str):
        port_map = {"MySQL": 3306, "PostgreSQL": 5432, "SQL Server": 1433}
        self.port_spin.setValue(port_map.get(db_type, 3306))

    def _on_config_selected(self, index: int):
        if index < 0:
            return
        name = self.config_combo.currentText()
        if name in self.saved_configs:
            cfg = self.saved_configs[name]
            type_map = {"mysql": "MySQL", "postgresql": "PostgreSQL", "mssql": "SQL Server"}
            self.db_type_combo.setCurrentText(type_map.get(cfg.get("db_type", ""), "MySQL"))
            self.host_edit.setText(cfg.get("host", "localhost"))
            self.port_spin.setValue(cfg.get("port", 3306))
            self.database_edit.setText(cfg.get("database", ""))
            self.user_edit.setText(cfg.get("user", ""))
            self.password_edit.setText(_unobscure(cfg.get("password_enc", "")))
            self.save_check.setChecked(True)
            self.config_name_edit.setText(name)

    def _on_delete_config(self):
        name = self.config_combo.currentText()
        if not name:
            return
        if name in self.saved_configs:
            del self.saved_configs[name]
            _save_configs(self.saved_configs)
            self._load_config_combo()
            self.conn_status.setText(i18n.tr("db.config_deleted"))

    def _get_config_from_ui(self) -> dict:
        db_type_map = {"MySQL": "mysql", "PostgreSQL": "postgresql", "SQL Server": "mssql"}
        return {
            "db_type": db_type_map.get(self.db_type_combo.currentText(), "mysql"),
            "host": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "database": self.database_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "password": self.password_edit.text(),
        }

    def _on_test_connection(self):
        config = self._get_config_from_ui()
        try:
            self.sql_loader.connect(config)
            self.conn_status.setText(i18n.tr("db.conn_success"))
            self.conn_status.setStyleSheet("color: #27ae60;")
            self._load_table_list()
            QMessageBox.information(self, i18n.tr("db.test_title"), i18n.tr("db.conn_success_msg"))
        except Exception as e:
            self.conn_status.setText(i18n.tr("db.conn_failed"))
            self.conn_status.setStyleSheet("color: #e74c3c;")
            QMessageBox.critical(self, i18n.tr("db.test_title"), f"{i18n.tr('db.conn_failed_msg')}\n{str(e)}")

    def _load_table_list(self):
        self.table_list.clear()
        try:
            names = self.sql_loader.get_table_names()
            for name in sorted(names):
                item = QListWidgetItem(name)
                item.setCheckState(Qt.Unchecked)
                self.table_list.addItem(item)
            if not names:
                self.conn_status.setText(i18n.tr("db.no_tables"))
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("db.error"), str(e))

    def _on_refresh_tables(self):
        if not self.sql_loader.is_connected():
            QMessageBox.warning(self, i18n.tr("db.error"), i18n.tr("db.conn_first"))
            return
        self._load_table_list()
        self.conn_status.setText(i18n.tr("db.tables_refreshed"))

    def _load_config_combo(self):
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        self.config_combo.addItem("")
        for name in self.saved_configs:
            self.config_combo.addItem(name)
        self.config_combo.blockSignals(False)

    def _on_accept(self):
        config = self._get_config_from_ui()
        if not config["host"] or not config["database"]:
            QMessageBox.warning(self, i18n.tr("db.error"), i18n.tr("db.fill_required"))
            return

        if not self.sql_loader.is_connected():
            try:
                self.sql_loader.connect(config)
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("db.error"),
                                     f"{i18n.tr('db.conn_failed_msg')}\n{str(e)}")
                return

        selected = []
        for i in range(self.table_list.count()):
            item = self.table_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        if not selected:
            QMessageBox.warning(self, i18n.tr("db.error"), i18n.tr("db.select_tables_hint"))
            return

        self.selected_tables = selected

        if self.save_check.isChecked():
            name = self.config_name_edit.text().strip()
            if name:
                cfg = config.copy()
                cfg["password_enc"] = _obscure(cfg.pop("password", ""))
                cfg["name"] = name
                self.saved_configs[name] = cfg
                _save_configs(self.saved_configs)

        self.connection_established.emit(config)
        self.accept()

    def get_selection(self) -> Tuple[str, List[str]]:
        config = self._get_config_from_ui()
        return config, self.selected_tables
