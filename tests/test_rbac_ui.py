"""v2.6.2 RBAC 权限矩阵 UI 层测试

覆盖:
- 权限矩阵 (_ROLE_PERMISSIONS) 正确性
- MainWindow._has_permission / _check_permission (user=None 全放行 + 四角色)
- _TAB_PERMISSIONS 映射 (tab 28 = import, 其余 = view)
- refresh_menu_for_user 菜单置灰 (action-key 注册制)
- _apply_permission_filter 侧边栏/欢迎页过滤
- Sidebar.set_permission_filter / T44 import_db_clicked 信号
- WelcomePage.set_permission_filter
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from core.auth import AuthManager, User, _ROLE_PERMISSIONS
from ui.sidebar import Sidebar
from ui.welcome_page import WelcomePage


# ── 公共 fixture ──────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def make_user():
    """工厂: 创建指定角色的 User (无真实密码哈希)"""
    def _make(role, username="testuser"):
        return User(
            username=username,
            password_hash="$pbkdf2-sha256$150000$AAAA$BBBB",
            role=role,
            department="质量部",
            team="一组",
        )
    return _make


# ── 1. 权限矩阵正确性 ─────────────────────────────────

class TestPermissionMatrix:
    """验证 _ROLE_PERMISSIONS 四角色 × 十权限键"""

    ALL_ACTIONS = {
        "import", "analyze", "clean", "export", "view",
        "manage_users", "manage_dept_users", "settings",
        "share_project", "view_shared",
    }

    def test_admin_has_all_permissions(self):
        perms = AuthManager.get_permissions("admin")
        assert perms == _ROLE_PERMISSIONS["admin"]
        assert "settings" in perms
        assert "manage_users" in perms

    def test_dept_admin_has_no_settings_no_manage_users(self):
        perms = AuthManager.get_permissions("dept_admin")
        assert "settings" not in perms
        assert "manage_users" not in perms
        assert "manage_dept_users" in perms
        assert "import" in perms

    def test_analyst_has_no_settings_no_manage(self):
        perms = AuthManager.get_permissions("analyst")
        assert "settings" not in perms
        assert "manage_dept_users" not in perms
        assert "manage_users" not in perms
        assert perms == {"import", "analyze", "clean", "export", "view",
                         "share_project", "view_shared"}

    def test_readonly_minimal(self):
        perms = AuthManager.get_permissions("readonly")
        assert perms == {"export", "view", "view_shared"}

    def test_all_roles_have_view(self):
        for role in ("admin", "dept_admin", "analyst", "readonly"):
            assert "view" in AuthManager.get_permissions(role)

    def test_readonly_cannot_import_analyze_clean(self):
        perms = AuthManager.get_permissions("readonly")
        assert "import" not in perms
        assert "analyze" not in perms
        assert "clean" not in perms

    def test_check_permission_static(self, make_user):
        admin = make_user("admin")
        readonly = make_user("readonly")
        assert AuthManager.check_permission(admin, "settings") is True
        assert AuthManager.check_permission(readonly, "settings") is False
        assert AuthManager.check_permission(readonly, "export") is True
        assert AuthManager.check_permission(readonly, "import") is False

    def test_unknown_role_returns_empty(self):
        assert AuthManager.get_permissions("superadmin") == set()


# ── 2. _TAB_PERMISSIONS 映射 ──────────────────────────

class TestTabPermissions:
    def test_data_tab_requires_import(self):
        from ui.main_window import _TAB_PERMISSIONS
        assert _TAB_PERMISSIONS[28] == "import"

    def test_other_tabs_default_to_view(self):
        from ui.main_window import _TAB_PERMISSIONS
        # tab 1 (SPC), 7 (IE), 27 (dashboard) 不在映射中 → 默认 view
        for idx in (1, 7, 12, 27, 33, 34):
            assert idx not in _TAB_PERMISSIONS

    def test_plugin_tab_start_from_registry(self):
        from ui.main_window import _PLUGIN_TAB_START
        from ui._tab_registry import INDEX_MAP
        assert _PLUGIN_TAB_START == max(INDEX_MAP.keys()) + 1


# ── 3. MainWindow._has_permission ─────────────────────

class TestHasPermission:
    """测试 user=None 全放行 + 四角色权限差异"""

    def _make_mw(self, qapp, user=None):
        """创建轻量 MainWindow (patch QMessageBox 防弹窗)"""
        from ui.main_window import MainWindow
        mw = MainWindow(user=user)
        return mw

    def test_user_none_allows_everything(self, qapp):
        mw = self._make_mw(qapp, user=None)
        for action in ("import", "analyze", "clean", "export", "settings",
                        "share_project", "view_shared", "view"):
            assert mw._has_permission(action) is True, f"user=None 应放行 {action}"

    def test_admin_allows_settings(self, qapp, make_user):
        mw = self._make_mw(qapp, user=make_user("admin"))
        assert mw._has_permission("settings") is True
        assert mw._has_permission("import") is True

    def test_readonly_denied_import(self, qapp, make_user):
        mw = self._make_mw(qapp, user=make_user("readonly"))
        assert mw._has_permission("import") is False
        assert mw._has_permission("analyze") is False
        assert mw._has_permission("clean") is False
        assert mw._has_permission("export") is True
        assert mw._has_permission("view") is True

    def test_analyst_denied_settings(self, qapp, make_user):
        mw = self._make_mw(qapp, user=make_user("analyst"))
        assert mw._has_permission("settings") is False
        assert mw._has_permission("analyze") is True

    def test_dept_admin_denied_settings(self, qapp, make_user):
        mw = self._make_mw(qapp, user=make_user("dept_admin"))
        assert mw._has_permission("settings") is False
        assert mw._has_permission("import") is True


# ── 4. _check_permission (拒绝时审计+弹窗) ────────────

class TestCheckPermission:
    def test_permitted_returns_true(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("admin"))
        assert mw._check_permission("import") is True

    def test_denied_returns_false_and_audits(self, qapp, make_user, tmp_path, monkeypatch):
        import core.audit as audit_mod
        log_file = tmp_path / "audit.log"
        monkeypatch.setattr(audit_mod, "LOG_FILE", str(log_file))

        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("readonly"))

        with patch("ui.main_window.QMessageBox.warning") as mock_warn:
            result = mw._check_permission("import")
        assert result is False
        mock_warn.assert_called_once()
        content = log_file.read_text(encoding="utf-8")
        assert "permission_denied" in content
        assert "import" in content

    def test_user_none_never_denied(self, qapp):
        from ui.main_window import MainWindow
        mw = MainWindow(user=None)
        with patch("ui.main_window.QMessageBox.warning") as mock_warn:
            assert mw._check_permission("settings") is True
        mock_warn.assert_not_called()


# ── 5. refresh_menu_for_user (W44 action-key 置灰) ────

class TestRefreshMenu:
    def test_admin_all_actions_enabled(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("admin"))
        mw.refresh_menu_for_user()
        for action, perm in mw._action_permissions:
            assert action.isEnabled(), f"admin 的 {perm} 应启用"

    def test_readonly_disables_import_analyze_clean(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("readonly"))
        mw.refresh_menu_for_user()
        disabled_perms = {perm for action, perm in mw._action_permissions
                          if not action.isEnabled()}
        assert "import" in disabled_perms
        assert "analyze" in disabled_perms
        assert "clean" in disabled_perms
        assert "settings" in disabled_perms

    def test_user_mgmt_visible_for_admin(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("admin"))
        mw.refresh_menu_for_user()
        assert mw._user_mgmt_action.isVisible() is True

    def test_user_mgmt_visible_for_dept_admin(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("dept_admin"))
        mw.refresh_menu_for_user()
        assert mw._user_mgmt_action.isVisible() is True

    def test_user_mgmt_hidden_for_analyst(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("analyst"))
        mw.refresh_menu_for_user()
        assert mw._user_mgmt_action.isVisible() is False

    def test_user_mgmt_hidden_for_readonly(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("readonly"))
        mw.refresh_menu_for_user()
        assert mw._user_mgmt_action.isVisible() is False

    def test_user_none_all_enabled(self, qapp):
        from ui.main_window import MainWindow
        mw = MainWindow(user=None)
        mw.refresh_menu_for_user()
        for action, perm in mw._action_permissions:
            assert action.isEnabled(), f"user=None 的 {perm} 应启用"


# ── 6. _apply_permission_filter (侧边栏 + 欢迎页) ─────

class TestApplyPermissionFilter:
    def test_user_none_all_tabs_visible(self, qapp):
        from ui.main_window import MainWindow
        mw = MainWindow(user=None)
        mw._apply_permission_filter()
        for idx, btn in mw.sidebar.nav_buttons.items():
            assert not btn.isHidden(), f"user=None tab {idx} 应可见"

    def test_readonly_data_tab_hidden(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("readonly"))
        mw._apply_permission_filter()
        # tab 28 (data_tools) 需要 import 权限, readonly 无 → 隐藏
        if 28 in mw.sidebar.nav_buttons:
            assert mw.sidebar.nav_buttons[28].isHidden()

    def test_readonly_view_tabs_visible(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("readonly"))
        mw._apply_permission_filter()
        # tab 1 (SPC) 默认 view 权限, readonly 有 view → 可见
        if 1 in mw.sidebar.nav_buttons:
            assert not mw.sidebar.nav_buttons[1].isHidden()

    def test_admin_all_tabs_visible(self, qapp, make_user):
        from ui.main_window import MainWindow
        mw = MainWindow(user=make_user("admin"))
        mw._apply_permission_filter()
        if 28 in mw.sidebar.nav_buttons:
            assert not mw.sidebar.nav_buttons[28].isHidden()


# ── 7. Sidebar.set_permission_filter ─────────────────

class TestSidebarFilter:
    def test_all_visible_when_all_allowed(self, qapp):
        sb = Sidebar()
        all_indices = set(sb.nav_buttons.keys())
        sb.set_permission_filter(all_indices)
        for idx, btn in sb.nav_buttons.items():
            assert not btn.isHidden()

    def test_home_always_visible(self, qapp):
        sb = Sidebar()
        sb.set_permission_filter({0})
        assert not sb.nav_buttons[0].isHidden()

    def test_non_allowed_hidden(self, qapp):
        sb = Sidebar()
        sb.set_permission_filter({0, 1})
        for idx, btn in sb.nav_buttons.items():
            if idx in (0, 1):
                assert not btn.isHidden()
            else:
                assert btn.isHidden()


# ── 8. WelcomePage.set_permission_filter ─────────────

class TestWelcomePageFilter:
    def test_all_visible_when_all_allowed(self, qapp):
        wp = WelcomePage()
        all_perms = {"import", "analyze", "clean", "export", "view",
                     "settings", "share_project", "view_shared"}
        wp.set_permission_filter(all_perms)
        for card, perm in wp._card_permissions:
            assert not card.isHidden()

    def test_import_cards_hidden_without_import(self, qapp):
        wp = WelcomePage()
        wp.set_permission_filter({"view", "export"})
        for card, perm in wp._card_permissions:
            if perm == "import":
                assert card.isHidden()
            elif perm is None:
                assert not card.isHidden()


# ── 9. T44: Sidebar.import_db_clicked 信号 ───────────

class TestT44SidebarSignal:
    def test_sidebar_has_import_db_clicked_signal(self):
        assert hasattr(Sidebar, "import_db_clicked")
