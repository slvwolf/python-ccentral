import json
import unittest

from etcd import Client
from mock import Mock

from ccentral.client import CCentral, EtcdWrapper


class TestClient(unittest.TestCase):

    def setUp(self):
        self.etcd = Mock(Client)
        self.ewrap = Mock(EtcdWrapper)
        self.etcd.get = Mock()
        self.etcd.get().value = "{}"
        self.client = CCentral("service", self.etcd)
        self.client._e = self.ewrap
        self.client._auto_refresh = False

    """ Service info is updated """
    def test_update_service_info(self):
        self.client.add_service_info("key", "data", ttl=50)
        self.etcd.set.assert_called_with("/ccentral/services/service/info/key", "data", 50)

    """ Counter history is added to instance data """
    def test_counters(self):
        self.client.inc_instance_counter("c", 10, now=1)
        self.client._push_client(now=70)
        d = json.loads(self.etcd.set.call_args[0][1])
        self.assertEquals([10], d["c_c"])

    """ Error is sent """
    def test_collect_error(self):
        try:
            raise Exception("Test")
        except Exception:
            self.client.log_exception(key="foobar")
        self.client.refresh(force=True)
        print(self.ewrap.get_and_set_error.method_calls)
        self.ewrap.get_and_set_error.assert_called_once()

    """ Histogram data is included in client payload """
    def test_histogram_reporting(self):
        self.client.add_histogram("name", 100)
        self.client._push_client(now=70)
        d = json.loads(self.etcd.set.call_args[0][1])
        self.assertEquals([0, 0, 0, 0, 0], d["h_name"])
