# from modules.bag_recorder_module import IModule, AsState
from typing import List

from rclpy.node import Node
from rclpy.serialization import serialize_message
from std_msgs.msg import String

from rclpy.node import Node
from modules.imodule import IModule
import rosbag2_py

from modules.topics_discovery import TopicsDiscovery
from rosidl_runtime_py.utilities import get_message

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
        self.all_topics = Node.get_topic_names_and_types(recorder_node)
        self.recorder_node=recorder_node

    def _module_init(self) -> None:
        # super().__init__('simple_bag_recorder')

        self.writer = rosbag2_py.SequentialWriter()

        storage_options = rosbag2_py.StorageOptions(
            uri=self.bag_name,
            storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.writer.open(storage_options, converter_options)
        
        for topic in self.bag_topics:
            topic_type = list(filter(lambda t: t[0] == topic, self.all_topics))[0][1][0]
            self.writer.create_topic(rosbag2_py.TopicMetadata(
                name=topic,
                type=topic_type,
                serialization_format='cdr',
                offered_qos_profile='10'
            ))
        
    
    def _module_start(self) -> None:  
        for topic in self.bag_topics:
        # refactor please
        # self._logger.info(f"[bag_recorder] {list(filter(lambda t: t[0] == topic, self.all_topics))[0][1][0]}")
            topic_type = list(filter(lambda t: t[0] == topic, self.all_topics))[0][1][0]
        
            self.recorder_node.create_subscription(
                msg_type=get_message(topic_type),
                topic=topic,
                qos_profile=10,
                callback=self.topic_callback
            )
        
        
        # self._logger.info("[bag_recorder] module start")
        # self._logger.info(f"[bag_recorder] {self.bag_topics}")
        # self._logger.info(f"[bag_recorder] {type(self.bag_topics)}")
        # self._logger.info(f"[bag_recorder] {self.all_topics}")
        # self._logger.info(f"[bag_recorder] {type(self.all_topics)}")

        

    def _module_stop(self) -> None:
        self.writer.close()
        self.recorder_node.destroy_subscription(self.recorder_node.subscription)

    def topic_callback(self, msg):
        self.writer.write(serialize_message(msg))

