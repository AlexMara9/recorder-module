import time
from typing import List, Tuple
import rclpy

class TopicsDiscovery:
    @staticmethod
    def get_all_topics() -> List[Tuple[str, List[str]]]:
        if not rclpy.ok():
            rclpy.init()
        
        discovery_node = rclpy.create_node("discovery_node")

        time.sleep(0.5)

        #rclpy.Node.get_topic_names_and_types()

        topics = discovery_node.get_topic_names_and_types()

        discovery_node.destroy_node()
        return topics