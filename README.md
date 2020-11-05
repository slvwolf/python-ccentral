# python-ccentral

Python client for CCentral configuration management. Client communicates
directly with etcd.

WebUI for configuration management and monitoring metrics can be found
from https://github.com/slvwolf/ccentral.

## Example Usage
    import ccentral

    cc = ccentral.CCentral("my_service", "etcd-host:1234")
    cc.add_field("config_a", "Dynamic configuration", default="test", description="Configuration string")

    # Read configuration
    print(cc.get("config_a"))

    # Increment counters
    cc.inc_instance_counter("run")

    # Set text info
    cc.add_instance_info("version", "1.2")

    # Set text info (common in cluster)
    cc.add_service_info("shared_key", "shared_value")

