import unittest

from etcd import Client
from mock import Mock, ANY

from ccentral.client import CCentral


class TestClient(unittest.TestCase):

    def setUp(self):
        self.etcd = Mock(Client)
        self.client = CCentral("service", self.etcd)

    """ Service info is updated """
    def test_update_service_info(self):
        self.client.add_service_info("key", "data", ttl=50)
        self.etcd.set.assert_called_with("/ccentral/services/service/info/key", "data", 50)

    """ Counter history is added to instance data """
    def test_counters(self):
        self.client.inc_instance_counter("c", 10, now=1)
        self.client._push_client(now=70)
        self.etcd.set.assert_called_with(ANY, '{"c_c": [10], "ts": 70, "v": ""}', ANY)