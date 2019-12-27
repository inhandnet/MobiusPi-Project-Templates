import os
import sys
import logging
import time
from parse_config import YamlConfig
from mobiuspi_lib.config import Config as APPConfig

logging.basicConfig(level=logging.DEBUG)

def main(argv=sys.argv):
    logging.debug("Hello, world! Welcome to the Inhand!")
    print("Hello, world! Welcome to the Inhand!")

    """get config file of user app  
         APPConfig(name="appname")
            'appname' is the name of user app
         app_config.get_app_cfg_file()
            get user app configuration file
    """
    app = APPConfig(name="appname") 
    app_config_file = app.get_app_cfg_file()
    if not app_config_file:
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
