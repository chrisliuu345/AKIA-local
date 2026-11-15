"""OPC UA 连接器：不可达端点要报错，回环服务器要能读到节点值。"""
import socket

import pytest

pytest.importorskip("asyncua")

from asyncua.sync import Server
from connectors.plugins.opcua import Connector


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_unreachable_endpoint_reports_error():
    connector = Connector({
        "name": "plc",
        "endpoint": "opc.tcp://127.0.0.1:1/missing",
        "node_ids": {"CH0": "ns=2;i=1"},
    })
    with pytest.raises(ConnectionError, match="连接失败"):
        connector.open()
    assert connector._client is None


def test_loopback_reads_node_and_read_failure_is_reported():
    port = _free_port()
    endpoint = f"opc.tcp://127.0.0.1:{port}/akia-test"
    server = Server()
    server.set_endpoint(endpoint)
    index = server.register_namespace("akia")
    server.start()
    try:
        variable = server.nodes.objects.add_variable(index, "Diameter", 12.5)
        node_id = variable.nodeid.to_string()
        connector = Connector({
            "name": "plc",
            "endpoint": endpoint,
            "node_ids": {"CH0": node_id},
        })
        connector.open()
        try:
            samples = connector.poll()
            assert [(s.channel, s.value) for s in samples] == [("CH0", 12.5)]
            connector.config["node_ids"] = {"CH0": node_id, "CH1": "ns=2;i=99"}
            with pytest.raises(ConnectionError, match="读数失败"):
                connector.poll()
        finally:
            connector.close()
    finally:
        server.stop()
