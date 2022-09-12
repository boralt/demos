#!/usr/bin/env python3

from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
import logging
import time
from threading import Thread, current_thread
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import re
import os
import binascii
import traceback
import random
from enum import Enum
from typing import List, Set, Dict, Type

logger = logging.getLogger()


class IntegrationResult:
    """
    Result of alarm integration

    INTEG_UNRELATED - different, not correlated type of alert
    INTEG_REPLACE - active version replaces previously posted alert
    INTEG_RETAIN - keep current posted alert
    """
    INTEG_UNRELATED = 1
    INTEG_REPLACE = 2
    INTEG_RETAIN = 3


class AlertItem:
    ''' Interface class '''

    def __init__(self):
        pass

    def to_tag(self) -> Dict:
        ''' Convert into tms tag '''
        raise NotImplementedError("Should be implemented")

    def from_tag(self, tag) -> Dict:
        ''' Convert from tms tag '''
        raise NotImplementedError("Implement if alert integration is enabled")

    def is_same_type(self, another) -> bool:
        ''' check if this alert of the same type as another alert'''
        return False

    def integrate(self, another) -> IntegrationResult:
        ''' return integ result '''
        if not self.is_same_type(another):
            return IntegrationResult.INTEG_UNRELATED
        return IntegrationResult.INTEG_RETAIN

    def clear_alert(self):
        ''' Update alert content to make it cleared '''
        raise NotImplementedError("Implement if alert integration is enabled")
        pass

    def is_cleared(self):
        ''' Is this alert already cleared '''
        return False

    @classmethod
    def get_subscription_schema(cls):
        ''' evestream definition  '''
        raise NotImplementedError("Implement if alert integration is enabled")

    @classmethod
    def alert_filter(cls) -> Dict:
        ''' Must be implemented, defines filter for object of this type
            for example: {"is_regex":True, "tagname": "mytag", attributes: {"key":"value"}}'''
        raise NotImplementedError("Must be implemented by derived class")


class AlertTypeIntegrator:
    def __init__(self, AlertItemClass: Type[AlertItem], bootstrap_servers):
        self.AlertClass = AlertItemClass
        self.bootstrap_servers = bootstrap_servers
        # alerts just detected
        self.active_alerts = []
        # alerts currently posted into TMS
        self.current_alerts = []
        # producer properties
        conf_prod = {'bootstrap.servers': self.bootstrap_servers,
                     "message.max.bytes": 2000000,
                     "request.timeout.ms": 15000,
                     "retry.backoff.ms": 1000,
                     "retries": 5,
                     "request.required.acks": "all"
                     }
        self.producer = Producer(conf_prod)
        self.consumer = None
        self.rx_topic = "alert_integrator"
        self.topic_data = "TM_Default_Data_Topic_Request"
        self.topic_control = "TM_Default_Ctrl_Topic_Request"
        self.group_id = "alarm-gr"

    def _get_kafka_consumer(self):
        if self.consumer:
            return self.consumer
        conf_cons = {'bootstrap.servers': self.bootstrap_servers,
                     'group.id': "alert_integrator",
                     'auto.offset.reset': 'smallest',
                     'auto.commit.interval.ms': 1000}
        self.consumer = Consumer(conf_cons)
        return self.consumer

    def add_active_alert(self, alert: AlertItem):
        """ Add alerts conditions that active at this moment """
        self.active_alerts.append(alert)

    def _receive_tms_alerts(self, topic, request_id):
        """Fetches alert managed by this object."""
        self.current_alerts = []
        try:
            kafka_consumer = self._get_kafka_consumer()
            try:
                kafka_consumer.subscribe([topic])
            except Exception as err:
                logger.info("Exception consumer subscribe: {} from topic {}".format(str(err), topic))
            timeout = 5.0
            while True:
                msg = kafka_consumer.poll(timeout=timeout)
                timeout = 0.5
                if msg is None:
                    break
                if msg.error():
                    logger.info(
                        "Error topic:{} partition:{} error:{}".format(msg.topic(), msg.partition(), msg.error()))
                else:
                    req = json.loads(msg.value())
                    logger.info("Read back from TMS: {}".format(req))
                    if req["request_id"] == request_id:
                        for data_points in req["data"]["tags"]:
                            for data_point in data_points["datapoints"]:
                                alert = self.AlertClass()
                                self.current_alerts.append(alert)
                                try:
                                    alert.from_tag(data_point)
                                except Exception as e:
                                    logger.info("Unable to decode alert from tms\n{}".format(traceback.format_exc()))
                pass
            kafka_consumer.commit()
        except Exception as e:
            logger.info("Exception consumer: {} from topic {}\n{}".format(str(e), topic, traceback.format_exc()))

    def _acked(self, err, msg):
        if err is not None:
            logger.info("Failed to deliver message: {} to kafka, receiving error {}".format(str(msg), str(err)))
        else:
            sent = msg.value()
            logger.info("ACK {}".format(sent))

    def start_eventstream(self):
        """ Register eventstream for this alert type.
            Only needed if automatic eventstream is not used """
        evs_request = {}
        evs_request["request_id"] = int(time.time())
        evs_request["request"] = "start_eventstreams"
        evs_request["request_data"] = self.AlertClass.get_subscription_schema()
        data = json.dumps(evs_request)
        self.producer.produce(self.topic_control, data, callback=self._acked)
        self.producer.flush()

    def stop_eventstream(self):
        """ Deregister evenstream for this this alert type """
        id = self.AlertClass.get_subscription_schema()["eventstream_id"]
        data = {"eventstream_id": id}
        stop_request = {}
        stop_request["request_id"] = int(time.time())
        stop_request["request"] = "stop_eventstreams"
        stop_request["request_data"] = data
        data = json.dumps(stop_request)
        self.producer.produce(self.topic_control, data, callback=self._acked)
        self.producer.flush()

    def fetch_current_alerts(self):
        """"" Fetch alerts that are currenly raised in tms
              Needs to be invoked only if alert integration is need """
        query = self.AlertClass.alert_filter()
        request_id = int(time.time())
        # cookie = {"dpu": "", "tagname": query["tagname"] , "timestamp": time.time()}
        req = {"request_id": request_id, "request": "query",  # "request_cookie": cookie,
               "request_data": {"tags": [query]}, "response_topic": self.rx_topic}
        self.producer.produce(self.topic_data, json.dumps(req), callback=self._acked)
        self._receive_tms_alerts(self.rx_topic, request_id)

    def prepare_update(self, alerts: List[AlertItem]) -> Dict:
        tags = []
        for alert in alerts:
            tags.append(alert.to_tag())

        ingest_request = {}
        query = self.AlertClass.alert_filter()
        ingest_cookie = {"dpu": "", "timestamp": time.time(), "tagname": query["tagname"]}
        ingest_request["request_id"] = int(time.time())
        ingest_request["request"] = "ingest"
        ingest_request["request_cookie"] = ingest_cookie
        ingest_request["request_data"] = {"tags": tags}
        return ingest_request

    def _post_to_tmdata(self, req: Dict):
        req_str = json.dumps(req)
        self.producer.produce(self.topic_data, req_str, callback=self._acked)
        self.producer.flush(timeout=5.0)

    def update_tms_alerts(self):
        """ Integrate active alerts with current (in tms) alerts.
        If current alerts are not fetched from tms then only active alerts
        are sent """
        alerts_to_post = []
        alerts_to_disable = []
        alerts_to_retain = []
        # alerts_to_eval = [a for a in self.active_alerts]
        alerts_to_eval = [a for a in self.current_alerts]

        for active_alert in self.active_alerts:
            matched = False
            for current_alert in alerts_to_eval:
                integ_action = active_alert.integrate(current_alert)
                if integ_action == IntegrationResult.INTEG_RETAIN:
                    alerts_to_retain.append(active_alert)
                    alerts_to_eval.remove(current_alert)
                    matched = True
                    break
                elif integ_action == IntegrationResult.INTEG_UNRELATED:
                    continue
                elif integ_action == IntegrationResult.INTEG_REPLACE:
                    alerts_to_post.append(active_alert)
                    alerts_to_eval.remove(current_alert)
                    matched = True
            if not matched:
                alerts_to_post.append(active_alert)
        # remaining alerts_to eval should be deleted
        for alert in alerts_to_eval:
            if alert.is_cleared():
                # already cleared alert. Nothing to do
                alerts_to_eval.remove(alert)
            else:
                alert.clear_alert()
        # prepare update
        if alerts_to_eval or alerts_to_post:
            req = self.prepare_update(alerts_to_eval + alerts_to_post)
            logger.info("Prepare to send {}".format(req))
            self._post_to_tmdata(req)
