# -*- coding:utf-8 -*-

import yaml

class YamlConfig:
    """A class that Parses the yaml style configuration file of user app.
    
    usage:
       file = './config.yaml'
       configs = YamlConfig(file)
           file --> config file name 
       configs.exist_config_option('config', 'description')
           examine if this configuration exists
       configs.get_option_config('config', 'description')
           get Specific configuration
       configs.get_configs()
           get all configurations from config file
   
    """

    def __init__(self, filename):
        self.configs = None

        with open(filename, "r") as f:
            self.configs = yaml.load(f)

    def exist_config_option(self, section, option):
        state = False
        if self.configs and section in self.configs and option in self.configs[section]:
            state = True
        return state

    def get_option_config(self, section, option):
        if self.exist_config_option(section, option):
            return self.configs[section][option]
        else:
            return None

    def convert_config_to_integer(self, section, option):
        if self.exist_config_option(section, option):
            try:
                return int(self.configs[section][option])
            except Exception as error:
                print("can not convert config %s to integer. Error:%s" % (self.configs[section][option], error))

    def get_configs(self):
        return self.configs


if __name__ == '__main__':
    filename = "./config.yaml"
    config_instance = YamlConfig(filename)
    yaml_configs = config_instance.get_configs()

