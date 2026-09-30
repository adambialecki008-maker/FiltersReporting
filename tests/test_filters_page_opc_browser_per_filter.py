from filters_reporting.gui.pages import filters_page as page_module
from filters_reporting.models.filter import Filter


class FakeEdit:
    def __init__(self, value=""):
        self._value = value

    def text(self):
        return self._value

    def setText(self, value):
        self._value = value

    def setFocus(self):
        pass


class FakePage:
    def __init__(self, filter_obj):
        self.selected_filter_id = filter_obj.filter_id
        self._filter_obj = filter_obj
        self.opc_url_edit = FakeEdit(filter_obj.opc_url or "")
        self.delta_p_node_edit = FakeEdit(filter_obj.delta_p_node_id or "")
        self.status_node_edit = FakeEdit(filter_obj.status_node_id or "")
        self.alarm_node_edit = FakeEdit(filter_obj.alarm_node_id or "")

    def find_filter_by_id(self, filter_id):
        if filter_id == self._filter_obj.filter_id:
            return self._filter_obj
        return None


def test_browser_worker_passes_filter_to_browser(monkeypatch):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_auth_type="UsernamePassword",
        opc_username="operator1",
    )
    calls = []

    monkeypatch.setattr(
        page_module,
        "browse_opc_ua_server",
        lambda endpoint, **kwargs: calls.append((endpoint, kwargs)) or object(),
    )

    worker = page_module.OpcUaBrowseWorker(
        filter_obj.opc_url,
        filter_obj=filter_obj,
    )
    worker.run()

    assert calls == [
        (
            "opc.tcp://10.0.0.1:4840",
            {
                "timeout_seconds": 5.0,
                "max_depth": 10,
                "max_nodes": 3000,
                "filter_obj": filter_obj,
            },
        )
    ]


def test_filters_page_passes_selected_machine_config_to_dialog(monkeypatch):
    filter_obj = Filter(
        name="F7",
        filter_id=7,
        opc_url="opc.tcp://10.0.0.7:4840",
        opc_security_policy="Aes256Sha256RsaPss",
        opc_security_mode="SignAndEncrypt",
        opc_auth_type="UsernamePassword",
        opc_username="operator7",
    )
    page = FakePage(filter_obj)
    captured = {}

    class FakeDialog:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def exec(self):
            return page_module.QDialog.Rejected

    monkeypatch.setattr(
        page_module,
        "OpcUaBrowserDialog",
        FakeDialog,
    )

    page_module.FiltersPage.open_opc_browser(page)

    assert captured["endpoint"] == filter_obj.opc_url
    assert captured["filter_obj"] is filter_obj
    assert captured["delta_p_node_id"] == ""
    assert captured["status_node_id"] == ""
    assert captured["alarm_node_id"] == ""
