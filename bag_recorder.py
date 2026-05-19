# from modules.bag_recorder_module import IModule, AsState
import threading
import time
from typing import List

from rclpy.node import Node
from rclpy.serialization import serialize_message
from std_msgs.msg import String

from rclpy.node import Node
from modules.imodule import IModule
import rosbag2_py

from .topics_collector import TopicsCollector

class bag_recorder(IModule):
    def __init__(
                self,
                recorder_node: Node, 
                debug: bool, config: dict, logger=None, create_timer=None, start_state=None, create_publisher=None
                ) -> None:
        
        super().__init__(
            debug = debug, config = config, logger=logger, create_timer=create_timer, start_state=start_state, create_publisher=create_publisher
            )
        
        self.bag_name = "test"
        self.bag_topics = ["/imu/data"]
        self.all_topics = Node.get_topic_names_and_types(recorder_node)
        self.recorder_node=recorder_node
        self.writer = rosbag2_py.SequentialWriter()
        self.topics: TopicsCollector = TopicsCollector()
        self.bag_is_open=False
        self.lock = threading.Lock()
        self.active_callbacks = 0

    def _module_init(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: init")
            self._logger.info("[bag_recorder]: --------all topics------")
            self._logger.info(f"[bag_recorder]: {self.all_topics}")
            self._logger.info("[bag_recorder]: ------------------------")
        # super().__init__('simple_bag_recorder')
        self.topics.parse(self.bag_topics, self.all_topics)
        
        if self._debug:
            self._logger.info("[bag_recorder]: --------bag topics------")
            self._logger.info(f"[bag_recorder]: {self.bag_topics}")
            self._logger.info("[bag_recorder]: ------------------------")

        storage_options = rosbag2_py.StorageOptions(
            uri=self.bag_name,
            storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.writer.open(storage_options, converter_options)
        self.bag_is_open=True
        
        for topic in self.bag_topics:
            # self._logger.info(f"[bag_recorder] topic name data type: {type(topic)}")
            # self._logger.info(f"[bag_recorder] topic type data type: {type(self.topics.extract_topic_type_as_string(topic))}")
            # self._logger.info(f"[bag_recorder] 'cdr' data type: {type('cdr')}")
            # self._logger.info(f"[bag_recorder] '10' data type: {type('10')}")
            # var_test=self.topics.extract_topic_type_as_string(topic)
            # self._logger.info(f"[bag_recorder] var test data type: {type(var_test)}")
            if self._debug:
                self._logger.info("[bag_recorder]: --------topic-----------")
                self._logger.info(f"[bag_recorder]: {topic}")
                self._logger.info("[bag_recorder]: ------------------------")
            self.writer.create_topic(rosbag2_py.TopicMetadata(
                name=topic,
                type=self.topics.extract_topic_type_as_string(topic),
                serialization_format='cdr',
                offered_qos_profiles='10'
            ))  
        
    
    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: start")
        for topic in self.bag_topics:
            if self._debug:
                self._logger.info("[bag_recorder]: --------topic-----------")
                self._logger.info(f"[bag_recorder]: {topic}")
                self._logger.info("[bag_recorder]: ------------------------")
            # self._logger.info(f"[bag_recorder] topic: {topic}")
            # self._logger.info(f"[bag_recorder] {self.topics.extract_topic_type_as_string(topic)}")
            # self._logger.info(f"[bag_recorder] {self.topics.extract_topic_type_as_class(topic)}")
            self.recorder_node.create_subscription(
                msg_type=self.topics.extract_topic_type_as_class(topic),
                topic=topic,
                qos_profile=10,
                callback=self.callback(topic)
            )
        
        
        # self._logger.info("[bag_recorder] module start")
        # self._logger.info(f"[bag_recorder] {self.bag_topics}")
        # self._logger.info(f"[bag_recorder] {type(self.bag_topics)}")
        # self._logger.info(f"[bag_recorder] {self.all_topics}")
        # self._logger.info(f"[bag_recorder] {type(self.all_topics)}")

        

    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: stop")
            self._logger.info("[bag_recorder]: waiting for writings to finish")
        self.bag_is_open=False
        while True:
            with self.lock:
                if self.active_callbacks == 0:
                    break
                time.sleep(0.05)
        self._logger.info("[bag_recorder]: all writings finished")
        self.writer.close()
        for subscription in self.recorder_node.subscriptions:
            self.recorder_node.destroy_subscription(subscription)

    def callback(self, topic_name):
        def topic_callback(msg):
            # self._logger.info('got msg: "%s"' % msg)
            self._logger.info('got msg: "%d"' % self.active_callbacks)
            if not self.bag_is_open :
                return
            with self.lock:
                self.active_callbacks += 1

            try:
                self._logger.info('got msg: "%d"' % self.active_callbacks)
                self.writer.write(
                    topic_name,
                    serialize_message(msg),
                    self.recorder_node.get_clock().now().nanoseconds)
            finally:
                with self.lock:
                    self.active_callbacks -= 1
            # self._logger.info(f"[bag_recorder]: writing on topic {topic_name}")

            self._logger.info('got msg: "%d"' % self.active_callbacks)
        return topic_callback

