# from modules.bag_recorder_module import IModule, AsState
from rclpy.node import Node
from rclpy.serialization import serialize_message
from std_msgs.msg import String

from rclpy.node import Node
from modules.imodule import IModule
import rosbag2_py

from topics_discovery import TopicsDiscovery
from rosidl_runtime_py.utilities import get_message

class bag_recorder(IModule):
    def __init__(
                self,
                recorder_node: Node, recorder_node_name: String, bag_name: String, bag_topics: list[String], 
                debug: bool, config: dict, logger=None, create_timer=None, start_state=None, create_publisher=None
                ) -> None:
        
        super().__init__(
            debug = debug, config = config, logger=logger, create_timer=create_timer, start_state=start_state, create_publisher=create_publisher
            )
        
        self.bag_name = bag_name
        self.bag_topics = bag_topics
        self.all_topics = TopicsDiscovery.get_all_topics()
        self.recorder_node=recorder_node
        self.recorder_node.__init__(recorder_node_name)

    def _module_init(self) -> None:
        # super().__init__('simple_bag_recorder')

        self.writer = rosbag2_py.SequentialWriter()

        storage_options = rosbag2_py.StorageOptions(
            uri=self.bag_name,
            storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.writer.open(storage_options, converter_options)
        for topic in self.bag_topics:
            self.writer.create_topic(rosbag2_py.TopicMetadata(
                name=topic,
                type=self.all_topics[topic][0],
                serialization_format='cdr',
                offered_qos_profile='10'
            ))
        
    
    def _module_start(self) -> None:  
        for topic in self.bag_topics:
            self.recorder_node.create_subscription(
                msg_type=get_message(self.all_topics[topic][0]),
                topic=topic,
                qos_profile=10,
                callback=self.topic_callback
            )

    def _module_stop(self) -> None:
        self.recorder_node.destroy_subscription(self.recorder_node.subscription)

    def topic_callback(self, msg):
        self.writer.write(serialize_message(msg))

