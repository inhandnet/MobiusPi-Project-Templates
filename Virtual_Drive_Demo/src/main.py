#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Virtual Drive Demo
Created on 2022/3/8
@author: Inhand
'''

import sys
import time
import json
import logging
import libevent
from parse_config import ConfigPars
from mqclient import MQClientLibevent


debug_format = '[%(asctime)s] [%(levelname)s] [%(filename)s %(lineno)d]: %(message)s'
logging.basicConfig(format=debug_format, level=logging.INFO)

# The topic of upload data to DSA
READ_DRIVER_TOPIC = "ds2/eventbus/south/read/"
# The topic of DSA modifying measure values
WRITE_DRIVER_TOPIC = "ds2/eventbus/south/write/+"
# The topic of the response after DSA modifies the measuring value 
EVENT_BUS_SOUTH_WRITE_RESP = "ds2/eventbus/south/write/{requestServiceId}/response"


class App(object):
    def __init__(self, vendor_name, app_name):
        self.config = ConfigPars(app_name)
        self.config.load_config_file()
        self.base = libevent.Base()
        self.libeventmq = MQClientLibevent(self.base, vendor_name)
        self.pub_timer = libevent.Timer(
                         self.base, self.on_pub_timer_handler, userdata=None)
        self.gl_measure_values = list()

    # Define upload data and trigger periodically  
    def on_pub_timer_handler(self, evt, userdata):
        controllers = list()
        publish_payload = dict()
        timestamp = int(round(time.time()))

        if not self.libeventmq.is_ready():
            return

        for ctrl in self.config.cfg["controllers"]:
            measures = list()
            table_dict = dict()
            for mea in self.config.cfg["measures"]:
                if mea["ctrlName"] == ctrl["name"]:
                    table_dict = {}
                    table_dict["name"] = mea["name"]
                    table_dict["health"] = 1
                    table_dict["timestamp"] = timestamp
                    table_dict["value"] = self.get_measure_value(ctrl["name"], mea)
                    measures.append(table_dict)
            table_dict = {}
            table_dict["name"] = ctrl["name"]
            table_dict["version"] = ""
            table_dict["health"] = 1
            table_dict["timestamp"] = timestamp
            table_dict["measures"] = measures
            controllers.append(table_dict)
        publish_payload["controllers"] = controllers

        logging.info("Publish message:%s" % publish_payload)
        self.libeventmq.publish(READ_DRIVER_TOPIC, json.dumps(publish_payload))
        self.pub_timer.add(5)

    def on_write_measure_value(self, topic, payload):
        logging.info("receive topic: %s , payload: %s" % (topic, payload))
        if isinstance(payload, (str, bytes)):
            payload = json.loads(payload)

        for ctrl in payload["payload"]:
            for measure in ctrl["measures"]:
                err_code, params = self.upgrate_measure_value(ctrl["name"], measure["name"], measure["value"])

                measure["error_code"] = err_code
                measure["error_reason"] = params
                del measure["value"]

        serviceId = topic.split("/")[-1]
        self.libeventmq.publish(EVENT_BUS_SOUTH_WRITE_RESP.format(requestServiceId=serviceId), json.dumps(payload))

    def run(self):
        self.pub_timer.add(5)
        self.base.loop()

    def measure_is_exist(self, con_name, mea_name):
        for meas in self.config.cfg["measures"]:
            if meas["ctrlName"] == con_name and meas["name"] == mea_name:
                return True

        return False

    def find_measure_value(self, con_name, mea_name):
        for info in self.gl_measure_values:
            if info["ctrl_name"] == con_name and info["mea_name"] == mea_name:
                return info

        return None

    def upgrate_measure_value(self, con_name, mea_name, value):
        if not self.measure_is_exist(con_name, mea_name):
            return 1, "Failed"

        measure = self.find_measure_value(con_name, mea_name)
        if measure:
            measure['value'] = value
        else:
            self.gl_measure_values.append({"ctrl_name": con_name, "mea_name": mea_name, "value": value})

        return 0, "Success"

    # If the measuring point value is not modified, the default value will be uploaded 
    def get_measure_value(self, con_name, mea):
        measure = self.find_measure_value(con_name, mea['name'])
        if measure:
            return measure["value"]
        else:
            if mea["dataType"] == "STRING":
                return 'ABCD'
            elif mea["dataType"] in ["FLOAT", "DOUBLE"]:
                return 100.0
            else:
                return 100


def main(argv=sys.argv):
    app = App('inhand', 'Virtual_Drive_Demo')
    app.libeventmq.init_mqclient()
    app.libeventmq.add_sub(WRITE_DRIVER_TOPIC, app.on_write_measure_value)
    app.libeventmq.connect()
    app.run()


if __name__ == '__main__':
    main()
