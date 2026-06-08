# from modules.bag_recorder_module import IModule, AsState
from datetime import datetime
import glob
import os
import threading
import time
from typing import List

from rclpy.node import Node, Subscription
from rclpy.serialization import serialize_message
from rclpy.qos import QoSPresetProfiles

from modules.imodule import IModule
import rosbag2_py

from .topics_collector import TopicsCollector
from .yaml_paths import YamlPaths
import yaml

class bag_recorder(IModule):
    def __init__(
                self,
                recorder_node: Node,
                debug: bool, config: dict, logger=None, create_timer=None, start_state=None, create_publisher=None
                ) -> None:
        
        super().__init__(
            debug = debug, config = config, logger=logger, create_timer=create_timer, start_state=start_state, create_publisher=create_publisher
            )
        
        self.recorder_node=recorder_node


    def _module_init(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: INIT")
        
        # TODO: check file and required params existence 
        yaml_paths = YamlPaths()
        with open(yaml_paths.bag_yaml_path, 'r') as f:
            yaml_data = yaml.load(f, Loader=yaml.FullLoader)

#       ===== BAG INIT =====      
        self.bag_dir = yaml_data['bag_dir'] #"./bags/"
        self.bag_name = yaml_data['bag_name']
        self.bag_topics = str(yaml_data['topics']).split(' ')#["/canbus/imu/data","/debug/clutch"]
        self.timestamp_format=yaml_data['date_format']#"%Y%m%d_%H%M%S"
        self.use_id = bool(yaml_data['enable_ids']) #false
        # self.bag_topics = ["/test","/test2"]
        
        self.all_topics = Node.get_topic_names_and_types(self.recorder_node)
        self.writer = rosbag2_py.SequentialWriter()
        self.topics: TopicsCollector = TopicsCollector()
        self.subs: List[Subscription] = []
        
        self.timestamp : datetime

        if self._debug:
            self._logger.info(f"[bag_recorder]: all topics |{self.all_topics}|")
            self._logger.info(f"[bag_recorder]: bag topics |{self.bag_topics}|")
        
        self.topics.parse(self.bag_topics, self.all_topics)    

        # set bag uri
        if "/" in self.bag_name:
            self.bag_name = self.bag_name.split("/")[-1]
            self._logger.error(f"[bag_recorder]: invalid bag name, '/' not permited, saving as'{self.bag_name}'")
        self.uri = self.bag_dir + self.bag_name
        
        # set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_bag_id();
        
        # set timestamp
        if "TIMESTAMP" in self.bag_name:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.uri = self.uri.replace("TIMESTAMP",self.timestamp)

        if self._debug:
            self._logger.info(f"[bag_recorder]: bag uri: {self.uri}")

        storage_options = rosbag2_py.StorageOptions(
            uri=self.uri,
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

        if self._debug:
            self._logger.info("[bag_recorder]: all writings finished")
            self._logger.info(f"[bag_recorder]: {self.recorder_node.subscriptions}")
        
        for sub in self.subs:

            sub.destroy()
            
            if self._debug:
                self.recorder_node.destroy_subscription(sub)
                self._logger.info(f"[bag_recorder]: {sub.topic} destroyed")
        
        # self.writer.close()
        if hasattr(self, 'writer'):
            del self.writer


    def callback(self, topic_name):
        def topic_callback(msg):

            if self._debug:
                self._logger.info(f"[bag_recorder] {topic_name}-------------")
                self._logger.info(f"got msg: {msg}")
                
            self.writer.write(
                topic_name,
                serialize_message(msg),
                self.recorder_node.get_clock().now().nanoseconds)

            if self._debug:
                self._logger.info(f"[bag_recorder] -------------")
            
        return topic_callback
    
    def get_bag_id(self):
        found_bags = glob.glob(f"{self.bag_dir}*__*")
        max_bag_id = 0
        for bag in found_bags:
            if os.path.isdir(bag):
                try:
                    bag_id = int(bag.split("_")[-1])
                    if bag_id > max_bag_id:
                        max_bag_id = bag_id
                except (ValueError):
                    pass
        return str(max_bag_id+1)
