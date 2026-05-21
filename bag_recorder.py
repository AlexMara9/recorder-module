# from modules.bag_recorder_module import IModule, AsState
import threading
import time
from typing import List

from rclpy.node import Node, Subscription
from rclpy.serialization import serialize_message
from rclpy.qos import QoSPresetProfiles

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
        self.bag_topics = ["/imu/data","/lidar_imu"]
        # self.bag_topics = ["/test","/test2"]
        self.all_topics = Node.get_topic_names_and_types(recorder_node)
        self.recorder_node=recorder_node
        self.writer = rosbag2_py.SequentialWriter()
        self.topics: TopicsCollector = TopicsCollector()
        self.bag_is_open=False
        self.lock = threading.Lock()
        self.active_callbacks = 0
        self.subs: List[Subscription] = []


    def _module_init(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: INIT")
            self._logger.info(f"[bag_recorder]: all topics |{self.all_topics}|")
            self._logger.info(f"[bag_recorder]: bag topics |{self.bag_topics}|")
        
        self.topics.parse(self.bag_topics, self.all_topics)    

        storage_options = rosbag2_py.StorageOptions(
            uri=self.bag_name,
            storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.writer.open(storage_options, converter_options)
        self.bag_is_open=True
        if self._debug:
                self._logger.info("[bag_recorder]: topic creation...")
        for topic in self.bag_topics:
            if self._debug:
                self._logger.info(f"[bag_recorder] topic: {topic}")
                self._logger.info(f"[bag_recorder]: topic ({topic}) type as string = {self.topics.extract_topic_type_as_string(topic)}")
            self.writer.create_topic(rosbag2_py.TopicMetadata(
                name=topic,
                type=self.topics.extract_topic_type_as_string(topic),
                serialization_format='cdr',
                offered_qos_profiles=''
            ))  


    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: START")
            self._logger.info("[bag_recorder]: subscription creation...")
        for topic in self.bag_topics:
            if self._debug:
                self._logger.info(f"[bag_recorder] topic: {topic}")
                self._logger.info(f"[bag_recorder]: topic ({topic}) type as class = {self.topics.extract_topic_type_as_class(topic)}")
            
            self.subs.append(self.recorder_node.create_subscription(
                msg_type=self.topics.extract_topic_type_as_class(topic),
                topic=topic,
                qos_profile=QoSPresetProfiles.get_from_short_key('sensor_data'),
                # qos_profile=10,
                callback=self.callback(topic)
            ))


    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: stop")
            self._logger.info("[bag_recorder]: waiting for writings to finish...")
        
        self.bag_is_open=False
        while True:
            with self.lock:
                if self.active_callbacks == 0:
                    break
                time.sleep(0.05)
        
        if self._debug:
            self._logger.info("[bag_recorder]: all writings finished")
            self._logger.info(f"[bag_recorder]: {self.recorder_node.subscriptions}")
        
        # for sub in self.subs:

        #     sub.destroy()
            
        #     if self._debug:
        #         self.recorder_node.destroy_subscription(sub)
        #         self._logger.info(f"[bag_recorder]: {sub.topic} destroyed")
        
        # self.writer.close()


    def callback(self, topic_name):
        def topic_callback(msg):

            if self._debug:
                self._logger.info(f"[bag_recorder] {topic_name}-------------")
                self._logger.info(f"got msg: {msg}")
                self._logger.info(f"active callbacks (before i start): {self.active_callbacks}")

            if not self.bag_is_open :
                return
            
            with self.lock:
                self.active_callbacks += 1
            try:

                if self._debug:
                    self._logger.info(f"active callbacks (before i start): {self.active_callbacks}")
                
                self.writer.write(
                    topic_name,
                    serialize_message(msg),
                    self.recorder_node.get_clock().now().nanoseconds)
            finally:
                with self.lock:
                    self.active_callbacks -= 1

            if self._debug:
                self._logger.info(f"[bag_recorder] -------------")
            
        return topic_callback