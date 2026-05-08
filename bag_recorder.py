# from modules.bag_recorder_module import IModule, AsState
import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message
import sensor_msgs
from std_msgs.msg import String

from rclpy.node import Node
from modules.imodule import IModule, AsState
import rosbag2_py
class bag_recorder(IModule):
    def __init__(self, debug: bool, config: dict, recorder_node: Node, recorder_node_name: String, logger=None, create_timer=None, start_state=None, create_publisher=None) -> None:
        
        super().__init__(debug = debug, config = config, logger=logger, create_timer=create_timer, start_state=start_state, create_publisher=create_publisher)
        
        self.recorder_node=recorder_node
        self.recorder_node.__init__(recorder_node_name)

    def _module_init(self) -> None:
        # super().__init__('simple_bag_recorder')
        self.writer = rosbag2_py.SequentialWriter()

        storage_options = rosbag2_py.StorageOptions(
            uri='my_bag',
            storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.writer.open(storage_options, converter_options)

        topic_info = rosbag2_py.TopicMetadata(
            name='/imu/data',
            type='sensor/msg/Imu',
            serialization_format='cdr')
        self.writer.create_topic(topic_info)
        
    
    def _module_start(self) -> None:
        
        self.recorder_node.subscription = self.recorder_node.create_subscription(
            sensor_msgs.msg.Imu,
            '/imu/data',
            self.topic_callback,
            10)
        self.subscription

    def topic_callback(self, msg):
        self.writer.write(
            '/imu/data',
            serialize_message(msg),
            self.get_clock().now().nanoseconds)
    
    def _module_stop(self) -> None:
        """Stop the module. Called when the AS enters the stop_on_state."""
        pass

