import json
import logging
import time
import uuid
import ccentral

from etcd import Client, EtcdKeyNotFound, EtcdException

_log = logging.getLogger("ccentral")


class CCentral:

    LOCATION_SCHEMA = "/ccentral/services/%s/schema"
    LOCATION_CONFIG = "/ccentral/services/%s/config"
    LOCATION_CLIENTS = "/ccentral/services/%s/clients/%s"

    def __init__(self, service_name, etcd="127.0.0.1:2379", update_interval=60):
        self.fail_loudly = False
        self._host, self._port = etcd.split(":")
        self.__etcd_client = Client(self._host, int(self._port))
        self.service_name = service_name
        self.update_interval = update_interval
        self.__last_check = 0
        self.__schema = {}
        self.__config = {}
        self.id = uuid.uuid4().get_hex()
        self.__version = ""

    def add_field(self, key, title, type="string", default="", description=""):
        self.__schema[key] = {"title": title, "type": type, "default": str(default), "description": description}

    def refresh(self, force=False):
        if self.__last_check == 0:
            self._push_schema()
        if force or time.time() - self.__last_check > self.update_interval:
            self._pull_config()
            self.__last_check = time.time()
            self._push_client()

    def get(self, key):
        self.refresh()
        if key in self.__config:
            return self.__config[key]["value"]
        if key in self.__schema:
            return self.__schema[key]["default"]
        raise ccentral.ConfigNotDefined()

    def _push_client(self):
        try:
            client = {"v": self.__version, "ts": time.time()}
            self.__etcd_client.set(CCentral.LOCATION_CLIENTS % (self.service_name, self.id), json.dumps(client),
                                   2*self.update_interval)
        except EtcdException, e:
            # This is not really critical as the schema is only used by the WebUI
            _log.warn("Could not store client info: %s", e)

    def _push_schema(self):
        try:
            self.__etcd_client.set(CCentral.LOCATION_SCHEMA % self.service_name, json.dumps(self.__schema))
        except EtcdException, e:
            # This is not really critical as the schema is only used by the WebUI
            _log.warn("Could not store schema: %s", e)

    def _pull_config(self):
        try:
            data = self.__etcd_client.get(CCentral.LOCATION_CONFIG % self.service_name).value
            self.__config = json.loads(data)
            self.__version = self.__config.get("v", {}).get("value", "unknown")
        except EtcdKeyNotFound:
            # No custom configuration has been set
            self.__config = {}
            self.__version = "defaults"
        except EtcdException, e:
            _log.warn("Could not store schema: %s", e)
            if self.__last_check == 0 or self.fail_loudly:
                raise ccentral.ConfigPullFailed()

    def get_version(self):
        self.refresh()
        return self.__version
