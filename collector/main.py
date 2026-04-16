"""LakePulse collector: gathers Mac hardware metrics and publishes to ZeroBus."""

import logging
import os
import time

from collector.metrics import collect_all
from collector.zerobus_client import ZeroBusPublisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lakepulse.collector")

INTERVAL_SECONDS = int(os.environ.get("LAKEPULSE_INTERVAL", "5"))


def main() -> None:
    log.info("Starting LakePulse collector (interval=%ds)", INTERVAL_SECONDS)
    publisher = ZeroBusPublisher()

    try:
        while True:
            records = collect_all()
            log.info("Collected %d metrics", len(records))
            publisher.publish(records)
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
