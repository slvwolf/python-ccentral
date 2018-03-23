import time
import ccentral

c = ccentral.Client("example_service")

while True:
    c.inc_instance_counter("counter", 1)
    time.sleep(1)
