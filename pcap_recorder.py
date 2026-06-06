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
from scapy.all import PcapWriter, sniff

from .topics_collector import TopicsCollector
from .yaml_paths import YamlPaths
import yaml

class pcap_recorder(IModule):
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

        # TODO: check file and required params existence 
        yaml_paths = YamlPaths()
        with open(yaml_paths.bag_yaml_path, 'r') as f:
            yaml_data = yaml.load(f, Loader=yaml.FullLoader)

#       ===== PCAP INIT =====
        self.pcap_dir = yaml_data['pcap_dir']#"./pcap/"
        self.pcap_name = yaml_data['pcap_name']#"test.pcap"
        self.timestamp_format=yaml_data['date_format']#"%Y%m%d_%H%M%S"
        self.use_id=bool(yaml_data['enable_ids'])
        self.timestamp: datetime
        self.module_stop = False

        # set pcap uri
        if "/" in self.pcap_name:
            self.pcap_name = self.pcap_name.split("/")[-1]
            self._logger.error(f"[pcap_recorder]: invalid pcap name, '/' not permited, saving as'{self.pcap_name}'")
        self.uri = self.pcap_dir + self.pcap_name
        
        # set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_pcap_id();
        
        # set timestamp
        if "TIMESTAMP" in self.pcap_name:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.pcap_name.replace("TIMESTAMP",self.timestamp)

        self.writer = PcapWriter(self.pcap_name, append=False, sync=True)

        if self._debug:
            self._logger.info("[pcap_recorder]: topic creation...")  


    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: START")

        sniff(iface=None, prn=self.write_pcap)
        


    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: stop")
        
        self.module_stop = True

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
        found_pcaps = glob.glob(f"{self.pcap_dir}*__*")
        max_pcap_id = 0
        for pcap in found_pcaps:
            if os.path.isdir(pcap):
                try:
                    pcap_id = int(pcap.split("_")[-1])
                    if pcap_id > max_pcap_id:
                        max_pcap_id = pcap_id
                except (ValueError):
                    pass
        return str(max_pcap_id+1)

    def write_pcap(self, packet):
        self.writer.write(packet)

        if self.module_stop:
            self.writer.close()
            return True
        
        return False

