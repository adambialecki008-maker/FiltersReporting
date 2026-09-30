from __future__ import annotations

from dataclasses import dataclass, field

from asyncua import ua
from asyncua.sync import Client
from asyncua.crypto.truststore import TrustStore
from asyncua.crypto.validator import (
    CertificateValidator,
    CertificateValidatorOptions,
)

from filters_reporting.collection.opc_ua_client import (
    build_filter_security_config,
    configure_client_authentication,
)
from filters_reporting.opcua.security import (
    get_client_security_policy,
    get_message_security_mode,
)


@dataclass(slots=True)
class OpcUaNodeInfo:
    name: str
    browse_name: str
    node_id: str
    node_class: str
    namespace_index: int
    selectable: bool
    children: list["OpcUaNodeInfo"] = field(default_factory=list)


@dataclass(slots=True)
class OpcUaBrowseResult:
    endpoint: str
    namespaces: list[str]
    root: OpcUaNodeInfo
    node_count: int
    truncated: bool


def _configure_sync_client_security(
    client,
    filter_obj,
) -> None:
    if filter_obj is None:
        return

    config = build_filter_security_config(filter_obj)
    config.validate()

    if not config.enabled:
        configure_client_authentication(client, filter_obj)
        return

    policy_class = get_client_security_policy(config.policy)
    mode = get_message_security_mode(config.mode)

    # asyncua.sync.Client wraps the asynchronous client in ``aio_obj``.
    # We configure the same properties used by the collector, but through
    # the synchronous wrapper used by the NodeId browser.
    client.aio_obj.application_uri = config.application_uri

    server_certificate = (
        str(config.server_certificate_path)
        if config.server_certificate_path
        else None
    )

    client.set_security(
        policy_class,
        certificate=str(config.certificate_path),
        private_key=str(config.private_key_path),
        server_certificate=server_certificate,
        mode=mode,
    )

    if config.validate_server_certificate:
        trusted_dir = config.trusted_certificates_dir

        trust_store = TrustStore(
            [trusted_dir],
            [],
        )

        client.tloop.post(trust_store.load())

        validator = CertificateValidator(
            (
                CertificateValidatorOptions.TRUSTED_VALIDATION
                | CertificateValidatorOptions.PEER_SERVER
            ),
            trust_store,
        )

        client.aio_obj.certificate_validator = validator

    configure_client_authentication(client, filter_obj)


def browse_opc_ua_server(
    endpoint: str,
    timeout_seconds: float = 5.0,
    max_depth: int = 10,
    max_nodes: int = 3000,
    filter_obj=None,
) -> OpcUaBrowseResult:
    endpoint = endpoint.strip()

    if not endpoint:
        raise ValueError("Endpoint OPC UA nie może być pusty.")

    if max_depth < 1:
        raise ValueError("max_depth musi być >= 1.")

    if max_nodes < 1:
        raise ValueError("max_nodes musi być >= 1.")

    client = Client(
        endpoint,
        timeout=timeout_seconds,
        sync_wrapper_timeout=(timeout_seconds + 5),
    )

    _configure_sync_client_security(
        client,
        filter_obj,
    )

    with client:
        namespaces = client.get_namespace_array()

        objects_node = client.get_objects_node()

        visited: set[str] = set()

        node_count = 0
        truncated = False

        def build_node(
            node,
            depth: int,
        ) -> OpcUaNodeInfo | None:
            nonlocal node_count
            nonlocal truncated

            node_id = node.nodeid.to_string()

            if node_id in visited:
                return None

            if node_count >= max_nodes:
                truncated = True
                return None

            visited.add(node_id)

            node_count += 1

            browse_name_obj = node.read_browse_name()

            display_name_obj = node.read_display_name()

            node_class_obj = node.read_node_class()

            browse_name = browse_name_obj.Name or node_id

            display_name = display_name_obj.Text or browse_name

            node_class = node_class_obj.name

            node_info = OpcUaNodeInfo(
                name=display_name,
                browse_name=browse_name,
                node_id=node_id,
                node_class=node_class,
                namespace_index=(node.nodeid.NamespaceIndex),
                selectable=(node_class_obj == ua.NodeClass.Variable),
            )

            if depth >= max_depth:
                truncated = True
                return node_info

            try:
                children = node.get_children()
            except Exception:
                return node_info

            # Najpierw nody użytkownika,
            # dopiero później systemowe.
            #
            # Dzięki temu duże gałęzie ns=0
            # nie zużyją limitu zanim
            # dojdziemy do PLC / symulatora.
            children.sort(
                key=lambda child: (
                    child.nodeid.NamespaceIndex == 0,
                    child.nodeid.NamespaceIndex,
                    child.nodeid.to_string(),
                )
            )

            child_infos: list[OpcUaNodeInfo] = []

            for child in children:
                if node_count >= max_nodes:
                    truncated = True
                    break

                # Bezpośrednio pod Objects
                # pomijamy standardowe gałęzie
                # namespace 0.
                #
                # To są m.in. Server oraz inne
                # systemowe elementy OPC UA,
                # których nie potrzebujemy
                # podczas wyboru tagów.
                if depth == 0 and child.nodeid.NamespaceIndex == 0:
                    continue

                try:
                    child_info = build_node(
                        child,
                        depth + 1,
                    )

                except Exception:
                    continue

                if child_info is not None:
                    child_infos.append(child_info)

            child_infos.sort(key=lambda item: (item.name.casefold()))

            node_info.children = child_infos

            return node_info

        root = build_node(
            objects_node,
            0,
        )

        if root is None:
            raise RuntimeError("Nie udało się odczytać " "węzła Objects.")

        return OpcUaBrowseResult(
            endpoint=endpoint,
            namespaces=namespaces,
            root=root,
            node_count=node_count,
            truncated=truncated,
        )
