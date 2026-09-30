from types import SimpleNamespace

import pytest

import filters_reporting.collection.opc_ua_browser as browser


class FakeNodeId:
    def __init__(self, text, namespace_index):
        self._text = text
        self.NamespaceIndex = namespace_index

    def to_string(self):
        return self._text


class FakeNode:
    def __init__(
        self,
        node_id,
        namespace_index,
        name,
        node_class,
        children=None,
        display_name=None,
        children_error=False,
    ):
        self.nodeid = FakeNodeId(node_id, namespace_index)
        self._name = name
        self._display_name = display_name
        self._node_class = node_class
        self._children = list(children or [])
        self._children_error = children_error

    def read_browse_name(self):
        return SimpleNamespace(Name=self._name)

    def read_display_name(self):
        return SimpleNamespace(Text=self._display_name)

    def read_node_class(self):
        return self._node_class

    def get_children(self):
        if self._children_error:
            raise RuntimeError("cannot browse")
        return list(self._children)


class FakeClient:
    def __init__(self, root, namespaces=None):
        self.root = root
        self.namespaces = namespaces or [
            "http://opcfoundation.org/UA/",
            "urn:test",
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_namespace_array(self):
        return self.namespaces

    def get_objects_node(self):
        return self.root


def install_client(monkeypatch, root):
    client = FakeClient(root)
    factory_calls = []

    def factory(endpoint, timeout, sync_wrapper_timeout):
        factory_calls.append((endpoint, timeout, sync_wrapper_timeout))
        return client

    monkeypatch.setattr(browser, "Client", factory)

    return client, factory_calls


def test_browse_rejects_empty_endpoint():
    with pytest.raises(
        ValueError,
        match="Endpoint OPC UA nie może być pusty",
    ):
        browser.browse_opc_ua_server("   ")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"max_depth": 0},
            "max_depth musi być >= 1",
        ),
        (
            {"max_nodes": 0},
            "max_nodes musi być >= 1",
        ),
    ],
)
def test_browse_rejects_invalid_limits(kwargs, message):
    with pytest.raises(ValueError, match=message):
        browser.browse_opc_ua_server(
            "opc.tcp://localhost:4840",
            **kwargs,
        )


def test_browse_builds_tree_skips_system_branch_and_sorts_children(
    monkeypatch,
):
    variable_class = browser.ua.NodeClass.Variable
    object_class = SimpleNamespace(name="Object")

    var_b = FakeNode(
        "ns=2;s=B",
        2,
        "B",
        variable_class,
        display_name="Beta",
    )

    var_a = FakeNode(
        "ns=2;s=A",
        2,
        "A",
        variable_class,
        display_name="Alpha",
    )

    user_folder = FakeNode(
        "ns=2;s=Machine",
        2,
        "Machine",
        object_class,
        children=[var_b, var_a],
        display_name="Machine",
    )

    system_node = FakeNode(
        "i=2253",
        0,
        "Server",
        object_class,
        display_name="Server",
    )

    root = FakeNode(
        "i=85",
        0,
        "Objects",
        object_class,
        children=[
            system_node,
            user_folder,
        ],
        display_name="Objects",
    )

    _, calls = install_client(monkeypatch, root)

    result = browser.browse_opc_ua_server(
        "  opc.tcp://localhost:4840  ",
        timeout_seconds=2.5,
    )

    assert result.endpoint == "opc.tcp://localhost:4840"

    assert result.node_count == 4

    assert result.truncated is False

    assert [child.name for child in result.root.children] == ["Machine"]

    machine = result.root.children[0]

    assert [child.name for child in machine.children] == [
        "Alpha",
        "Beta",
    ]

    assert all(child.selectable for child in machine.children)

    assert calls == [
        (
            "opc.tcp://localhost:4840",
            2.5,
            7.5,
        )
    ]


def test_browse_marks_result_truncated_at_depth_limit(
    monkeypatch,
):
    object_class = SimpleNamespace(name="Object")

    child = FakeNode(
        "ns=2;s=Child",
        2,
        "Child",
        object_class,
        display_name="Child",
    )

    root = FakeNode(
        "i=85",
        0,
        "Objects",
        object_class,
        children=[child],
        display_name="Objects",
    )

    install_client(monkeypatch, root)

    result = browser.browse_opc_ua_server(
        "opc.tcp://localhost:4840",
        max_depth=1,
    )

    assert result.truncated is True
    assert result.node_count == 2


def test_browse_marks_result_truncated_at_node_limit(
    monkeypatch,
):
    object_class = SimpleNamespace(name="Object")

    children = [
        FakeNode(
            f"ns=2;s={i}",
            2,
            str(i),
            object_class,
            display_name=str(i),
        )
        for i in range(3)
    ]

    root = FakeNode(
        "i=85",
        0,
        "Objects",
        object_class,
        children=children,
        display_name="Objects",
    )

    install_client(monkeypatch, root)

    result = browser.browse_opc_ua_server(
        "opc.tcp://localhost:4840",
        max_nodes=2,
    )

    assert result.truncated is True
    assert result.node_count == 2


def test_browse_keeps_node_when_reading_children_fails(
    monkeypatch,
):
    object_class = SimpleNamespace(name="Object")

    broken = FakeNode(
        "ns=2;s=Broken",
        2,
        "Broken",
        object_class,
        display_name="Broken",
        children_error=True,
    )

    root = FakeNode(
        "i=85",
        0,
        "Objects",
        object_class,
        children=[broken],
        display_name="Objects",
    )

    install_client(monkeypatch, root)

    result = browser.browse_opc_ua_server("opc.tcp://localhost:4840")

    assert [child.name for child in result.root.children] == ["Broken"]

    assert result.root.children[0].children == []
