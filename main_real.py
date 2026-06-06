# -*- coding: utf-8 -*-
from carekeeper_providers import RealCareKeeperProvider
from carekeeper_ui import run_app


if __name__ == "__main__":
    run_app(RealCareKeeperProvider(), mode_name="Real Hardware")
