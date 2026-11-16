"""实时看板、告警、采集运行时和退出清理。"""

import contextlib

from PySide6.QtWidgets import (
    QMessageBox,
)
from PySide6.QtCore import (
    QUrl,
)
from PySide6.QtGui import QDesktopServices

from core.i18n import i18n


class RuntimeMixin:
    def _shutdown_runtime(self):
        """集中释放后台运行资源：看板服务 / 实时 OEE / 告警引擎 / Tab 实时订阅。

        未清理会导致退出后线程池与总线订阅残留（v3.7.1 修复）。
        """
        import logging
        log = logging.getLogger(__name__)

        from server.app import stop_thread
        try:
            stop_thread(getattr(self, "_dash_thread", None))
        except Exception:
            log.exception("停止实时看板服务失败")
        self._dash_thread = None

        oee = getattr(self, "_oee_computer", None)
        if oee is not None:
            try:
                oee.stop()
            except Exception:
                log.exception("停止实时 OEE 计算失败")
            self._oee_computer = None

        engine = getattr(self, "_alert_engine", None)
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                log.exception("停止告警引擎失败")
            self._alert_engine = None

        runner = getattr(self, "_ingest_runner", None)
        if runner is not None:
            try:
                runner.stop()
            except Exception:
                log.exception("停止采集运行时失败")
            self._ingest_runner = None

        store = getattr(self, "_ts_store", None)
        if store is not None:
            try:
                store.close()
            except Exception:
                log.exception("关闭时序库失败")
            self._ts_store = None

        for tab in list(getattr(self, "_tab_cache", {}).values()):
            shutdown = getattr(tab, "shutdown_stream", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    log.exception("Tab 实时流清理失败")

    def _on_plant_config(self):
        """产线配置可视化编辑（v3.8.0-②）— 保存后热重载看板/OEE/实时图规格。"""
        from ui.dialogs.plant_config_dialog import PlantConfigDialog
        dlg = PlantConfigDialog(self)
        if dlg.exec():
            self._reload_plant_config()
            self.statusBar().showMessage(
                f"{i18n.tr('plant.saved_tip')}: {dlg.path}", 6000)

    def _reload_plant_config(self):
        """就地重载产线拓扑 — 保持对象标识，运行中的看板/OEE 立即生效。"""
        try:
            oee = getattr(self, "_oee_computer", None)
            if oee is not None and getattr(oee, "plant", None) is not None:
                oee.plant.reload()
            elif getattr(self, "_plant_cfg", None) is not None:
                self._plant_cfg.reload()
            else:
                self._plant_cfg = self._load_plant_safe()
            for tab in list(getattr(self, "_tab_cache", {}).values()):
                if hasattr(tab, "_plant_cfg"):
                    tab._plant_cfg = None  # 实时图下次渲染重读
            if getattr(self, "_alert_engine", None) is not None:
                self._restart_alert_engine()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("产线配置热重载失败")

    def _load_plant_safe(self):
        try:
            from core.plant import PlantConfig
            return PlantConfig.load()
        except Exception:
            return None

    def _restart_alert_engine(self):
        engine = getattr(self, "_alert_engine", None)
        if engine is not None:
            with contextlib.suppress(Exception):
                engine.stop()
            self._alert_engine = None
        self._start_alert_engine()

    def _on_live_dashboard(self, checked: bool):
        """启动/停止内置实时看板服务（v3.7.0-P3）。"""
        if checked:
            try:
                from core.plant import PlantConfig
                from core.streaming.oee_live import LiveOEEComputer
                from server.app import dashboard_config, dashboard_url, start_thread

                cfg = dashboard_config()
                plant = PlantConfig.load()
                self._downtime = self._get_downtime_tracker()
                self._oee_computer = LiveOEEComputer(self.stream_bus, plant,
                                                     downtime=self._downtime)
                self._dash_thread = start_thread(
                    self.stream_bus, None, host=cfg["host"], port=cfg["port"],
                    plant=plant, oee=self._oee_computer,
                    downtime=self._downtime, auth_token=cfg["token"])
                self._dash_url = dashboard_url("127.0.0.1", cfg["port"])
            except Exception as e:
                QMessageBox.warning(
                    self, i18n.tr("menu.live_dashboard"),
                    f"{e}\n\npip install -r requirements-server.txt")
                self.live_dash_act.setChecked(False)
                return
            QDesktopServices.openUrl(QUrl(getattr(self, "_dash_url",
                                                  "http://127.0.0.1:8765/")))
        else:
            from server.app import stop_thread

            stop_thread(getattr(self, "_dash_thread", None))
            self._dash_thread = None
            oee = getattr(self, "_oee_computer", None)
            if oee:
                oee.stop()
                self._oee_computer = None

    def _start_alert_engine(self):
        """按产线配置 + user_config 设置安装告警引擎（桌面状态栏通知）。"""
        try:
            from config.settings import get_setting, get_secret
            from core.plant import PlantConfig
            from core.streaming.alerts import (
                AlertEngine, DesktopHandler, rules_from_plant,
                build_default_handlers,
            )
            plant = PlantConfig.load()
            rules = rules_from_plant(plant)
            if not rules:
                return
            desktop = DesktopHandler()
            desktop.alert.connect(
                lambda title, msg: self.statusBar().showMessage(f"{title}: {msg}", 8000))
            journal = self._get_alert_journal()
            settings = {
                "alert_journal": journal,
                "alert_min_severity": get_setting("alert_min_severity", "info"),
                "alert_webhook_url": get_setting("alert_webhook_url", ""),
                "alert_smtp_host": get_setting("alert_smtp_host", ""),
                "alert_smtp_port": get_setting("alert_smtp_port", 25),
                "alert_smtp_user": get_setting("alert_smtp_user", ""),
                "alert_smtp_password": get_secret("alert_smtp_password", ""),
                "alert_email_to": get_setting("alert_email_to", ""),
                "alert_actions": get_setting("alert_actions", {}) or {},
                "alert_actions_enabled": bool(
                    get_setting("alert_actions_enabled", False)),
            }
            self._alert_engine = AlertEngine(
                self.stream_bus, rules, [desktop] + build_default_handlers(settings))
            # v4.4.0 B1：critical 告警自动立案（钩子在采集线程内同步回调）
            self._alert_engine.alert_hook = self._on_live_alert
            self._alert_engine.start()
            self._alert_journal = journal
        except Exception:
            import logging
            logging.getLogger(__name__).exception("alert engine init failed")

    def _get_alert_journal(self):
        """告警日志单例（告警中心与引擎共享同一实例）。"""
        journal = getattr(self, "_alert_journal", None)
        if journal is None:
            from core.streaming.alert_journal import AlertJournal
            journal = AlertJournal()
            self._alert_journal = journal
        journal.event_sink = self._on_alert_event
        return journal

    def _get_downtime_tracker(self):
        """停机追踪单例（实时 OEE / 成本损失 / 看板共用）。"""
        tracker = getattr(self, "_downtime", None)
        if tracker is None:
            from config.settings import get_setting
            from core.streaming.downtime import DowntimeTracker
            tracker = DowntimeTracker(
                reason_codes=get_setting("downtime_reason_codes", None))
            self._downtime = tracker
        return tracker

    def _start_streaming_runtime(self):
        """按 user_config.connectors 启动采集运行时（v3.8.0-⑦）。

        未配置 connectors 时不启动（默认零开销）；启动后设备/连接器数据进入
        StreamBus → 实时 SPC / OEE / 看板 / 告警全链路。单项连接器初始化
        失败只记录健康状态，不影响其他数据源。
        """
        try:
            from config.settings import get_setting
            from connectors.health import HealthRegistry
            from connectors.registry import create_drivers, specs_from_settings
            from core.storage.timeseries import TimeseriesStore, default_store_path
            from core.streaming.collector import IngestRunner

            specs = specs_from_settings(get_setting("connectors", []))
            if not specs:
                return
            drivers, errors = create_drivers(specs)
            health = HealthRegistry(
                base_backoff_s=float(get_setting("connector_backoff_base_s", 1.0)),
                max_backoff_s=float(get_setting("connector_backoff_max_s", 60.0)),
            )
            for spec in specs:
                health.register(str(spec.get("name")), kind="connector")
            for name, message in errors:
                health.mark_error(name, f"初始化失败: {message}")
            if not drivers:
                self._connector_health = health
                return

            db_path = get_setting("ts_db_path", "") or default_store_path()
            store = TimeseriesStore(db_path)
            raw_days = float(get_setting("ts_raw_retention_days", 0) or 0)
            rollup_days = float(get_setting("ts_rollup_retention_days", 0) or 0)
            runner = IngestRunner(
                self.stream_bus, store, drivers,
                raw_retention_s=raw_days * 86400 or None,
                rollup_retention_s=rollup_days * 86400 or None,
                health=health,
                event_sink=self._on_stream_measurements,
            )
            runner.start()
            self._connector_health = health
            self._ingest_runner = runner
            self._ts_store = store
        except Exception:
            import logging
            logging.getLogger(__name__).exception("streaming runtime init failed")

    def _on_connector_health(self):
        """连接器健康页（v3.8.0-⑦）— 状态 / 插件可用性 / 手动重连。"""
        from ui.dialogs.connector_health_dialog import ConnectorHealthDialog
        dlg = ConnectorHealthDialog(getattr(self, "_connector_health", None),
                                    getattr(self, "_ingest_runner", None), self)
        dlg.exec()

    def _on_alert_center(self):
        """告警中心（v3.8.0-③）— 等级筛选 / 确认 / 导出。"""
        from ui.dialogs.alert_center_dialog import AlertCenterDialog
        dlg = AlertCenterDialog(
            self._get_alert_journal(), self,
            case_resolver=self.alert_case_orchestrator.case_for_alert,
            open_case=self._open_case_by_id)
        dlg.exec()
