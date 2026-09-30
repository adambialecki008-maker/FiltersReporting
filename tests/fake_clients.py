from filters_reporting.collection.opc_ua_client import OpcUaFilterClient


class FakeReconnectClient(OpcUaFilterClient):
    def __init__(self, filter_obj, expected_sample):
        super().__init__(filter_obj)
        self.client = object()
        self.expected_sample = expected_sample
        self.read_count = 0
        self.connect_count = 0
        self.disconnect_count = 0

    async def read_sample(self):
        self.read_count += 1

        if self.read_count == 1:
            raise Exception("Test connection error")

        return self.expected_sample

    async def connect(self):
        self.connect_count += 1
        self.client = object()

    async def disconnect(self):
        self.disconnect_count += 1
        self.client = None


class FakeReconnectFailClient(OpcUaFilterClient):
    def __init__(self, filter_obj):
        super().__init__(filter_obj)
        self.client = object()

    async def read_sample(self):
        raise Exception("Read failed")

    async def connect(self):
        raise Exception("Reconnect failed")

    async def disconnect(self):
        self.client = None


class FakeDisconnectedClient(OpcUaFilterClient):
    def __init__(self, filter_obj, expected_sample):
        super().__init__(filter_obj)
        self.expected_sample = expected_sample
        self.client = None
        self.read_count = 0
        self.connect_count = 0
        self.disconnect_count = 0

    async def connect(self):
        self.connect_count += 1
        self.client = object()

    async def read_sample(self):
        self.read_count += 1
        return self.expected_sample

    async def disconnect(self):
        self.disconnect_count += 1
        self.client = None
