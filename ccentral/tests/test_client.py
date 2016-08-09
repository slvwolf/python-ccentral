import unittest

from etcd import Client
from mock import Mock

from ccentral.client import CCentral


class TestClient(unittest.TestCase):

    def setUp(self):
        self.etcd = Mock(Client)
        self.client = CCentral("service", self.etcd)

    """ Service info is updated """
    def test_update_service_info(self):
        self.client.add_service_info("key", "data", ttl=50)
        self.etcd.set.assert_called_with("/ccentral/services/service/info/key", "data", 50)
