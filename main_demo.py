# -*- coding: utf-8 -*-
from carekeeper_providers import MockCareKeeperProvider
from carekeeper_ui import run_app


if __name__ == "__main__":
    run_app(MockCareKeeperProvider(), mode_name="Mock UI")
