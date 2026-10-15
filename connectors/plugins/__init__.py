"""连接器插件包 — 协议优先, 按需安装。"""

#: 插件模块名清单（不含包前缀）。源码运行时 registry 直接扫描本目录；
#: 冻结打包（PyInstaller）后源码文件不在磁盘上，无法扫描目录，registry
#: 以本清单为静态回退。**新增插件文件后必须同步登记此清单**。
PLUGIN_MODULES = (
    "cmm_dmis",
    "modbus_tcp",
    "mqtt_sub",
    "opcua",
    "serial_gage",
)

__all__ = ["PLUGIN_MODULES"]
