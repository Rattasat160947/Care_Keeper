# -*- coding: utf-8 -*-
from carekeeper_logging import configure_logging
from carekeeper_providers import MockCareKeeperProvider
from carekeeper_ui import run_app


if __name__ == "__main__":
    configure_logging()
    run_app(MockCareKeeperProvider(), mode_name="Mock UI")
