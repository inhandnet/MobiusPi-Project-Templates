# -*- coding:utf-8 -*-

import os
import json
import logging
from mobiuspi_lib.config import Config as AppConfig


class ConfigPars:
    def __init__(self, APP_NAME):
        self.cfg = dict()
        self.app_name = APP_NAME
        self.app_config = AppConfig(app_name=APP_NAME)
        self.app_base_path = self.app_config.app_base_path
        self.filename = self.app_base_path + '/cfg/' + self.app_name + '/' + self.app_name + '.cfg'

    def load_config_file(self):
        if not os.path.exists(self.filename):
            self.filename = self.app_base_path + "/app/" + self.app_name + "/config.ini"

        logging.info("Load config file: %s" % self.filename)
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.cfg = json.load(f)
        except Exception:
            raise ValueError("Load config failed")
