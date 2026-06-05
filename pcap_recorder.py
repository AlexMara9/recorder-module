# from modules.bag_recorder_module import IModule, AsState
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
from scapy.all import sniff, get_if_list, PcapWriter

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
        
        self.recorder_node=recorder_node


    def _module_init(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: INIT")
#       ===== PCAP INIT =====
        self.pcap_dir = "./pcap/"
        self.pcap_name = "test.pcap"
        packet = Ether() / IP(dst="1.2.3.4") / UDP(dport=123)
        self.writer = PcapWriter("capture.pcap", append=False, sync=True)
        
        self.topics.parse(self.bag_topics, self.all_topics)    

        # set pcap uri
        if "/" in self.pcap_name:
            self.pcap_name = self.pcap_name.split("/")[-1]
            self._logger.error(f"[pcap_recorder]: invalid bag name, '/' not permited, saving as'{self.pcap_name}'")
        self.uri = self.pcap_dir + self.pcap_name
        
        # set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_pcap_id();


        if self._debug:
                self._logger.info("[pcap_recorder]: topic creation...")  


    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: START")
        


    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: stop")

        # self.writer.close()
        # if hasattr(self, 'writer'):
        #     del self.writer


    def callback(self):
        def handle_packet(pkt):

            if self._debug:
                self._logger.info("[pcap_recorder]-------------")
                self._logger.info(f"packet summary: {pkt.summary()}")
                
            self.writer.write(pkt)

            if self._debug:
                self._logger.info(f"[pcap_recorder] -------------")
            
        return handle_packet
    
    def get_pcap_id(self):
        found_bags = glob.glob(f"{self.pcap_dir}*__*")
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
