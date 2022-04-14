
import os
import ssl
import time
import socket
from socket import gaierror
import logging as logger
import paho.mqtt.client as mqtt
import libevent

MQ_NOT_READY = 0
MQ_READY = 1


def get_port():
    MQTT_BROKER_PORT = 1883
    port_file = "/var/run/python/mqtt_broker_local.port"
    if os.path.exists(port_file):
        try:
            with open(port_file, "r") as f:
                port_int = int(f.read())
                if port_int:
                    if port_int > 65535 or port_int < 0:
                        raise ValueError("The port should be 0~65535")
                    return port_int
                else:
                    pass
        except Exception:
            pass
    return MQTT_BROKER_PORT


class MqttSetting(object):
    MQTT_QOS_LEVEL = 0


class LocalBrokerBadConfError(ValueError):
    pass


class LocalPublishError(ValueError):
    pass


class MQClient(object):
    def __init__(self, client_id,
                 broker_host='127.0.0.1', broker_port=get_port(),
                 username=None, passwd=None, keepalive=60,
                 tls=False, capath=None, max_queue_size=1024,
                 clean_session=None, userdata=None, protocol=mqtt.MQTTv311,
                 after_connect=None, on_connected=None, on_disconnected=None):
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.keepalive = keepalive
        self.username = username
        self.passwd = passwd
        self.tls = tls
        self.capath = capath
        self.clean_session = clean_session
        self.userdata = userdata
        self.protocol = protocol

        self.mqtt_client = mqtt.Client(self.client_id, clean_session=self.clean_session,
                                       userdata=self.userdata,
                                       protocol=self.protocol)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        # self.mqtt_client.on_subscribe = self._on_subscribe
        self.mqtt_client.on_publish = self._on_publish
        self.mqtt_client.on_message = self._on_message
        self.max_queue_size = max_queue_size
        self.mqtt_client.max_queued_messages_set(self.max_queue_size)
        self.mqtt_client.max_inflight_messages_set(1)  # force in-order
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._after_connect = after_connect
        self._state = MQ_NOT_READY
        self.subs = dict()
        self.pub_acks = dict()
        self.pub_topic_cbs = dict()

    def connect(self):
        '''This function should be called once after MQClient object is created'''
        try:
            if self.username and self.passwd:
                self.mqtt_client.username_pw_set(self.username, self.passwd)
            if self.tls is True and self.capath:
                self.mqtt_client.tls_set(ca_certs=self.capath, tls_version=ssl.PROTOCOL_TLSv1_2)
            ret = self.mqtt_client.connect(self.broker_host, self.broker_port, self.keepalive)
            if self._after_connect is not None:
                self._after_connect(self.mqtt_client)
            return ret
        except Exception as e:
            logger.error('connect. %s' % e.__str__())

    def reconnect(self):
        try:
            self.mqtt_client.reconnect()
            if self._after_connect is not None:
                self._after_connect(self.mqtt_client)
        except gaierror as e:
            time.sleep(5)
            raise e
        except ValueError as e:
            logger.warn('reconnect -> connect. %s' % e.__str__())
            self.connect()
        except socket.error as se:
            logger.warn('reconnect -> connect. %s' % se.__str__())
            self.mqtt_client = mqtt.Client(self.client_id, clean_session=self.clean_session,
                                           userdata=self.userdata,
                                           protocol=self.protocol)
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            self.mqtt_client.on_publish = self._on_publish
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.max_queued_messages_set(self.max_queue_size)
            self.mqtt_client.max_inflight_messages_set(1)  # force in-order
            self.connect()
        except Exception as e:
            logger.error('reconnect. %s (host: %s, port: %s)' % (e.__str__(), self.broker_host, self.broker_port))

    def disconnect(self):
        return self.mqtt_client.disconnect()

    def loop(self):
        '''This function could be called in a while True loop'''
        try:
            return self.mqtt_client.loop()
        except socket.error as err:
            logger.error("loop error %s" % (err.__str__()))
            self._on_disconnect(self.mqtt_client, None, mqtt.MQTT_ERR_NO_CONN)
        return 404

    def loop_misc(self):
        '''This function could be called every some seconds to handle
        retry and ping'''
        try:
            self.mqtt_client.loop_misc()
        except socket.error as err:
            logger.error("loop error %s" % (err.__str__()))
            self._on_disconnect(self.mqtt_client, None, mqtt.MQTT_ERR_NO_CONN)

    def loop_read(self):
        '''This function could be called while the read IO is valid'''
        self.mqtt_client.loop_read()

    def loop_write(self):
        '''This function could be called while the write IO is valid'''
        if self.mqtt_client.want_write():
            self.mqtt_client.loop_write()

    def socket(self):
        return self.mqtt_client.socket()

    def get_state(self):
        return self._state

    def is_ready(self):
        return self._state == MQ_READY

    def add_sub(self, topic, callback, qos=MqttSetting.MQTT_QOS_LEVEL):
        '''
            This function should be call after MQClient object is created
            callback is a function(payload)
        '''
        d = dict()
        d['callback'] = callback
        d['qos'] = qos
        self.subs[topic] = d
        if self._state == MQ_READY:
            qos = self.subs[topic]['qos']
            logger.debug('key %s, value %s' % (topic, qos))
            self.mqtt_client.subscribe(topic, qos)

    def del_sub(self, topic):
        if topic in self.subs:
            del self.subs[topic]
            if self._state == MQ_READY:
                self.mqtt_client.unsubscribe(topic)

    def publish(self, topic, payload, qos=MqttSetting.MQTT_QOS_LEVEL, userdata=None):
        if self.get_state() == MQ_READY:
            try:
                mqttc_msg_info = self.mqtt_client.publish(topic, payload, qos)
                if mqttc_msg_info.rc is mqtt.MQTT_ERR_QUEUE_SIZE:
                    logger.info("publish return warning: %d(%s)" % (
                                mqttc_msg_info.rc, 'local queue overflow'))
                    for _ in range(0, mqtt.MQTT_ERR_QUEUE_SIZE):
                        if self.loop() > 0:
                            raise socket.error("Unknown exception...")
                        # self.mqtt_client.loop_write()
                elif (mqttc_msg_info.rc is not mqtt.MQTT_ERR_SUCCESS) \
                        and (mqttc_msg_info.rc is not mqtt.MQTT_ERR_NO_CONN):
                    logger.error("publish() return error: %d(%s)" % (
                        mqttc_msg_info.rc,
                        mqtt.error_string(mqttc_msg_info.rc)))
                    raise LocalPublishError(
                        'Local publish error, %s' %
                        mqtt.error_string(mqttc_msg_info.rc))
                else:
                    # print('mid %d' % mqttc_msg_info.mid)
                    if qos > 0 and userdata is not None and (topic in self.pub_topic_cbs):
                        d = dict()
                        d['topic'] = topic
                        d['userdata'] = userdata
                        self.pub_acks[mqttc_msg_info.mid] = d
                    # schedule loop write when msg is queued. If fail, wait for
                    # loop_misc() to retry
                    # self.mqtt_client.loop_write()  # this function will block process if qos =0
                    return True
            except socket.error as err:
                logger.error(
                    "publish() exception: %s topic %s  payload %s" %
                    (err.__str__(), topic, payload))
                self._on_disconnect(self.mqtt_client, None,
                                    mqtt.MQTT_ERR_NO_CONN)
            except Exception as e:
                logger.error(
                    "publish() exception: %s topic %s  payload %s" %
                    (e.__str__(), topic, payload))
        return False

    def _subscribe_topics(self):
        for topic in self.subs.keys():
            qos = self.subs[topic]['qos']
            logger.debug('key %s, value %s' % (topic, qos))
            self.mqtt_client.subscribe(topic, qos)

    def _on_connect(self, client, userdata, flags, rc):
        logger.info("_on_connect: rc = %d." % rc)
        if rc == mqtt.CONNACK_ACCEPTED:
            self._state = MQ_READY
            self._subscribe_topics()
            if self._on_connected is not None:
                self._on_connected(client)
        elif rc == mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:
            if self._state == MQ_READY:
                if self._on_disconnected is not None:
                    self._on_disconnected(client)
                self.reconnect()
        else:
            if self._state == MQ_READY:
                if self._on_disconnected is not None:
                    self._on_disconnected(client)
                raise LocalBrokerBadConfError(mqtt.connack_string(rc))

    def _on_disconnect(self, client, userdata, rc):
        logger.debug("_on_disconnect: rc = %d." % (rc, ))
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.warn('disconnected on disconnect() call')
            self._state = MQ_NOT_READY
            if self._on_disconnected is not None:
                self._on_disconnected(client)
        else:
            self._state = MQ_NOT_READY
            if self._on_disconnected is not None:
                self._on_disconnected(client)
            self.reconnect()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        pass

    def _on_publish(self, client, userdata, mid):
        if mid in self.pub_acks.keys():
            topic = self.pub_acks[mid]['topic']
            # print('on_publish topic %s, mid %d' % (topic, mid))
            if (topic is not None) and (topic in self.pub_topic_cbs):
                callback = self.pub_topic_cbs[topic]
                if callback is not None:
                    callback(self.pub_acks[mid]['topic'],
                             self.pub_acks[mid]['userdata'])
            del self.pub_acks[mid]

    def _on_message(self, client, userdata, msg):
        found = False
        # logger.info('MQ Client receives message, topic %s ...' %
        #                   msg.topic)
        for sub in self.subs.keys():
            if mqtt.topic_matches_sub(sub, msg.topic):
                found = True
                callback = self.subs[sub]['callback']
                if callback is not None:
                    try:
                        callback(msg.topic, msg.payload)
                    except Exception as e:
                        logger.warn('%s' % e.__str__())
                break
        if not found:
            pass


class MQClientLibevent(object):
    def __init__(self, base, client_id):
        self.base = base
        self.mqclient = None
        self.readEvt = None
        self.writeEvt = None
        self.client_id = client_id
        self.target_host = '127.0.0.1'
        self.target_port = get_port()
        self.target_username = None
        self.target_passwd = None
        self.keepalive = 240
        self.clean_session = None
        self.max_queue_size = 1024
        self.protocol = mqtt.MQTTv311

        self.timer = 1

        self.mq_timer = libevent.Timer(
            self.base, self._mq_timer_handler, userdata=None)

    def init_mqclient(self):
        self.mqclient = MQClient(
            self.client_id,
            broker_host=self.target_host,
            broker_port=self.target_port,
            username=self.target_username,
            passwd=self.target_passwd,
            keepalive=self.keepalive,
            max_queue_size=self.max_queue_size,
            clean_session=self.clean_session,
            protocol=self.protocol,
            after_connect=self._after_connect,
            on_disconnected=self._on_disconnected)

    def linkCheckout(self):
        try:
            s = socket.socket()
            s.settimeout(1)
            status = s.connect_ex((self.target_host, self.target_port))
            s.close()
            if status == 0:
                logger.debug("Network Connection OK.")
                return True
        except Exception as e:
            logger.debug("Link checkout except: %s" % e)
        logger.warn("Network connection failed. host: %s, port: %s" % (self.target_host, self.target_port))
        return False

    def loop(self):
        self.mqclient.loop()

    def connect(self):
        if self.linkCheckout():
            self.mqclient.connect()
        self.mq_timer.add(self.timer)

    def disconnect(self):
        self.mq_timer.delete()
        self.mqclient.disconnect()

    def add_sub(self, topic, callback, qos=MqttSetting.MQTT_QOS_LEVEL):
        self.mqclient.add_sub(topic, callback, qos)

    def del_sub(self, topic):
        self.mqclient.del_sub(topic)

    def publish(self, topic, payload, qos=MqttSetting.MQTT_QOS_LEVEL, userdata=None):
        res = self.mqclient.publish(topic, payload, qos, userdata=userdata)
        if res:
            self.writeEvt.add()
        return res

    def is_ready(self):
        return self.mqclient.is_ready()

    def _mq_timer_handler(self, evt, userdata):
        timestamp = time.time()
        try:
            if self.readEvt is not None:
                self.mqclient.loop_misc()
                self.mqclient.loop_write()
            elif self.linkCheckout():
                self.mqclient.reconnect()
            else:
                self.timer = 15
        except Exception as e:
            logger.error('%s' % e.__str__())
        use_time = time.time() - timestamp
        self.mq_timer.add(abs(use_time) + self.timer)

    def _mq_do_read(self, evt, fd, what, userdata):
        # TODO: For QoS>0, will loop_read() handle and send the protocol
        # packages? Or it only push the protocol packages to the queue and
        # wait the loop_write() to acturly send them?
        self.mqclient.loop_read()
        if self.readEvt is not None:
            self.readEvt.add()

    def _mq_do_write(self, evt, fd, what, userdata):
        self.mqclient.loop_write()
        # TODO: This writeEvt will only be called one time,
        # is that a good thing?
        # self.writeEvt.add()

    def _after_connect(self, client):
        if self.mqclient.socket() is not None:
            if self.readEvt is not None:
                self.readEvt.delete()
            if self.writeEvt is not None:
                self.writeEvt.delete()
            self.readEvt = libevent.Event(
                self.base, client.socket().fileno(),
                libevent.EV_READ | libevent.EV_PERSIST, self._mq_do_read)
            self.writeEvt = libevent.Event(
                self.base, client.socket().fileno(),
                libevent.EV_WRITE, self._mq_do_write)
            logger.debug('add MQ read & write event')
            self.readEvt.add()
            self.writeEvt.add()
            self.timer = 1

    def _on_disconnected(self, client):
        logger.warn('delete MQ read & write event')
        self.readEvt.delete()
        self.writeEvt.delete()
        self.readEvt = None
        self.writeEvt = None
        # self.mq_timer.delete()
