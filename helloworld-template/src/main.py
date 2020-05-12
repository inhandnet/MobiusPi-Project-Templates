import os
import sys
import logging
import time
from parse_config import YamlConfig
from mobiuspi_lib.config import Config as APPConfig

debug_format = '[%(asctime)s] [%(levelname)s] [%(filename)s %(lineno)d]: %(message)s'
logging.basicConfig(format=debug_format, level=logging.INFO)

def main(argv=sys.argv):
    logging.info("Hello, world! Welcome to the Inhand!")
    print("Hello, world! Welcome to the Inhand!")

    """get config file of user app  
         APPConfig(app_name="appname")
            'appname' is the name of user app
            it should the same as the name in setup.py
         app_config.get_app_cfg_file()
            get user app configuration file
    """
    app = APPConfig(app_name="appname") 
    app_config_file = app.get_app_cfg_file()
    if not app_config_file:
        logging.warn("Do not find config file, please import first!")
        return

    #print("app config file:%s" % app_config_file)
    config = YamlConfig(app_config_file)
    config_others = config.get_option_config('config', 'others')
    while True:
        logging.info("decription:%s" % (config.get_option_config('config', 'description')))
        print("decription:%s" % (config.get_option_config('config', 'description')))

        logging.info("debug:%s" % (config_others['LOG']['debug']))
        print("debug:%s" % (config_others['LOG']['debug']))

        time.sleep(10)

if __name__ == '__main__':
    main()
