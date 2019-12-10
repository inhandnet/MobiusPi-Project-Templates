import sys
import logging
import time
from parse_config import Config

logging.basicConfig(level=logging.DEBUG)


def main(argv=sys.argv):

    print("Hello, world! Welcome to the Inhand!")
    logging.debug("Hello, world! Welcome to the Inhand!")

    config_file = "/var/user/app/xxx/config.yaml"
    config = Config()
    config_data = config.parse_yaml_config(config_file)
    while True:
        logging.info("decription:%s" % (config_data['config']['description']))
        logging.info("debug:%s" % (config.getint('LOG', 'debug')))
        print("decription:%s" % (config_data['config']['description']))
        print("debug:%s" % (config.getint('LOG', 'debug')))
        time.sleep(10)


if __name__ == '__main__':
    main()
