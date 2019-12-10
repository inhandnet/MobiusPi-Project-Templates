# -*- coding:utf-8 -*-

import yaml


class Config:
    def __init__(self):
        self.others = dict()

    def has_option(self, section, option):
        state = False
        if self.others and section in self.others and option in self.others[
                section]:
            state = True
        return state

    def get(self, section, option, raw=False, vars=None):
        return self.others[section][option]

    def getint(self, section, option, raw=False, vars=None):
        return int(self.others[section][option])

    # 解析变量文件
    def parse_yaml_config(self, filename):
        with open(filename, "r") as f:
            s = yaml.load(f)
            self.others = s['config']['others']
            print(s)
            return s


if __name__ == '__main__':
    filename = "./config.yaml"
    config_instance = Config()
    config_instance.parse_yaml_config(filename)
