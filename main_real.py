# -*- coding: utf-8 -*-
from carekeeper_logging import configure_logging
from carekeeper_providers import RealCareKeeperProvider
from carekeeper_ui import run_app


if __name__ == "__main__":
    configure_logging()
    run_app(RealCareKeeperProvider(), mode_name="Real Hardware")
