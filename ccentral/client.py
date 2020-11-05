from typing import Dict
from pyformance.registry import Histogram
import hashlib
import json
import logging
import os
import threading
import time
import uuid
import traceback
import sys
import etcd
import ccentral

_log = logging.getLogger("ccentral")

TTL_DAY = 24 * 60 * 60
TTL_WEEK = TTL_DAY*7
VERSION = "0.4.1"
API_VERSION = "1"


class IncCounter:

    def __init__(self, now, interval=60, history=60):
        self._interval = interval
        self.__history_size = history
        self.history = []
        self.__lock = threading.Lock()
        self.__c_value = 0
        self.__c_time = now

    def _tick(self, now):
        while self.__c_time + self._interval < now:
            self.history.append(self.__c_value)
            self.__c_value = 0
            self.__c_time += self._interval
            while len(self.history) > self.__history_size:
                self.history.pop(0)

    def tick(self, now):
        with self.__lock:
            self._tick(now)

    def inc(self, amount, now):
        with self.__lock:
            self._tick(now)
            self.__c_value += amount


class EtcdWrapper:
    LOCATION_SERVICE_BASE = "/ccentral/services/%s"
    LOCATION_ERRORS = LOCATION_SERVICE_BASE + "/errors/%s"

    def __init__(self, etcd_c):
        if isinstance(etcd_c, str):
            self._host, self._port = etcd_c.split(":")
            self.etcd = etcd.Client(self._host, int(self._port))
        else:
            self.etcd = etcd_c

    def reconnect(self):
        self.etcd = etcd.Client(self.etcd.host, self.etcd.port)

    def get_and_set_error(self, service, error_hash, error):
        key = self.LOCATION_ERRORS % (service, error_hash)
        record = error
        try:
            record = json.loads(self.etcd.get(key).value)
            record["count"] += error["count"]
        except etcd.EtcdKeyNotFound:
            pass
        record["last"] = int(time.time())
        self.etcd.set(key, json.dumps(error), TTL_WEEK)


class CCentral:
    LOCATION_SERVICE_BASE = "/ccentral/services/%s"
    LOCATION_SCHEMA = LOCATION_SERVICE_BASE + "/schema"
    LOCATION_CONFIG = LOCATION_SERVICE_BASE + "/config"
    LOCATION_CLIENTS = LOCATION_SERVICE_BASE + "/clients/%s"
    LOCATION_SERVICE_INFO = LOCATION_SERVICE_BASE + "/info/%s"

    def __init__(self, service_name, etcd="127.0.0.1:2379", update_interval=60):
        """
        :type service_name: str
        :type etcd: str|Client
        :type update_interval: int
        """
        self.fail_loudly = False
        self.required_on_launch = False
        self._host = "127.0.0.1"
        self._port = 2379
        self._e = EtcdWrapper(etcd)
        self.__etcd_client = self._e.etcd
        self.service_name = service_name
        self.update_interval = update_interval
        self._auto_refresh = True
        self.__last_check = 0
        self.__schema = {}
        self.__config = {}
        self.__client = {}
        self.__counters = {}
        self.__histograms = {}  # type: Dict[str, Histogram]
        self.__errors = {}
        self.__start = int(time.time())
        self.id = uuid.uuid4().hex
        self.__version = ""

    def reconnect(self):
        """
        Reconnect to ETCD. This might be useful if you need to run forks of CCentral.
        """
        self._e.reconnect()
        self.__etcd_client = self._e.etcd

    def add_service_info(self, key, data, ttl=TTL_DAY):
        """
        Simple service centric metric which will be visible from the WebUI
        :type key: str
        :type data: str
        :type ttl: int
        :param key: Key
        :param data: Value (string)
        :param ttl: Time to live in seconds
        """
        self.__etcd_client.set(CCentral.LOCATION_SERVICE_INFO % (self.service_name, key), data, ttl)
        if self._auto_refresh:
            self.refresh()

    def log_exception(self, key=None):
        """
        Log Exception

        :type key: str
        :param key: Provide own key used for grouping errors, if skipped will be SHA1 hash of the exception
        """
        tb = traceback.format_exc().splitlines()
        key_hash = hashlib.sha1()
        for k in tb:
            key_hash.update(k.encode("utf8"))
        if not key:
            key = key_hash.hexdigest()
        if key in self.__errors:
            self.__errors[key]["count"] += 1
        else:
            self.__errors[key] = {"count": 1, "traceback": json.dumps(tb)}

    def add_instance_info(self, key, data):
        """
        Simple instance centric metric which will be visible from the WebUI
        :param key: Key
        :param data: Value (string)
        :return:
        """
        self.__client["k_" + key] = data
        if self._auto_refresh:
            self.refresh()

    def add_histogram(self, key, time_in_ms):
        """
        Add or update histogram
        :type key: str
        :type time_in_ms: int
        :param key: Key
        :param time_in_ms: Time in milliseconds
        """
        histogram = self.__histograms.get(key)  # type: Histogram
        if histogram:
            histogram.add(time_in_ms)
        else:
            histogram = Histogram()
            self.__histograms[key] = histogram

    def inc_instance_counter(self, key, amount=1, now=None):
        """
        Simple instance centric metric which will be visible from the WebUI
        :type key: str
        :type amount: int
        :type now: int
        :param key: Key
        :param amount: Increment
        :param now: Epoch time of the event (None for current)
        :return: None
        """
        if not now:
            now = time.time()
        if key not in self.__counters:
            self.__counters[key] = IncCounter(now)
        self.__counters[key].inc(amount, now)
        if self._auto_refresh:
            self.refresh(now=now)

    def add_field(self, key, title, type="string", default="", description=""):
        self.__schema[key] = {"title": title, "type": type, "default": str(default), "description": description}

    def refresh(self, force=False, now=None):
        if not now:
            now = time.time()
        if self.__last_check == 0:
            self._push_schema()
        if force or now - self.__last_check > self.update_interval:
            self._pull_config()
            self.__last_check = now
            self._push_client(now)

    def get(self, key):
        self.refresh()
        if key in self.__config:
            return self.__config[key]["value"]
        if key in self.__schema:
            return self.__schema[key]["default"]
        raise ccentral.ConfigNotDefined()

    def _push_client(self, now):
        try:
            self.__client["v"] = self.__version
            self.__client["cv"] = "python-%s" % VERSION
            self.__client["lv"] = sys.version
            self.__client["av"] = API_VERSION
            self.__client["ts"] = now
            self.__client["started"] = self.__start
            self.__client["uinterval"] = self.update_interval
            self.__client["hostname"] = os.getenv("HOSTNAME", "N/A")
            for key, c in self.__histograms.items():
                snap = c.get_snapshot()
                data = [snap.get_75th_percentile(),
                        snap.get_95th_percentile(),
                        snap.get_99th_percentile(),
                        snap.get_median()]
                self.__client["h_" + key] = data
            for key, c in self.__counters.items():
                c.tick(now)
                self.__client["c_" + key] = c.history
            self.__etcd_client.set(CCentral.LOCATION_CLIENTS % (self.service_name, self.id), json.dumps(self.__client),
                                   2*self.update_interval)
            for key, error in self.__errors.items():
                self._e.get_and_set_error(self.service_name, key, error)
            self.__errors = {}
        except etcd.EtcdException as e:
            # This is not really critical as the schema is only used by the WebUI
            _log.warning("Could not store client info: %s", e)

    def _push_schema(self):
        try:
            self.__etcd_client.set(CCentral.LOCATION_SCHEMA % self.service_name, json.dumps(self.__schema))
        except etcd.EtcdException as e:
            # This is not really critical as the schema is only used by the WebUI
            _log.warning("Could not store schema: %s", e)

    def _pull_config(self):
        try:
            data = self.__etcd_client.get(CCentral.LOCATION_CONFIG % self.service_name).value
            self.__config = json.loads(data)
            self.__version = self.__config.get("v", {}).get("value", "unknown")
        except etcd.EtcdKeyNotFound:
            # No custom configuration has been set
            self.__config = {}
            self.__version = "defaults"
        except etcd.EtcdException as e:
            _log.warning("Could not store schema: %s", e)
            if (self.__last_check == 0 or self.fail_loudly) and self.required_on_launch:
                raise ccentral.ConfigPullFailed()

    def get_version(self):
        self.refresh()
        return self.__version
