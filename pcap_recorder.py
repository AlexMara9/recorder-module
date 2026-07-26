from datetime import datetime
import glob
import os
import subprocess
import threading
import shlex
import re

from rclpy.node import Node

from modules.imodule import AsState, IModule


class pcap_recorder(IModule):
    def __init__(self, debug: bool, start_state: AsState, config: dict, node: Node) -> None:
        
        super().__init__(debug, start_state, config, node)
        
        self.logger_node: Node = node
        self.config=config


    def _module_init(self) -> None:
        if self._debug:
            self.logger_node.get_logger().info("[pcap_recorder]: INIT")

#       ===== PCAP INIT =====
        self.pcap_dir = self.if_exists_return_value('pcap_dir', self.config, "./pcap/")
        self.pcap_name = self.if_exists_return_value('pcap_name', self.config, "./pcap/")
        self.use_id = self.if_exists_return_value('enable_ids', self.config, False)
        self.pcap_args = self.if_exists_return_value('pcap_args', self.config, "")
        self.timestamp_format = self.if_exists_return_value('date_format', self.config, "%Y%m%d_%H%M%S")

        self.module_stop = False

        # check if args contains illegal arguments
        if " -w " in self.pcap_args:
            self.logger_node.get_logger().error("[pcap_recorder]: illegal arg in pcap_args. Specify pcap output filename inside pcap_name, not inside the pcap_args")

        # set pcap uri
        if self.pcap_dir[-1] != "/":
            self.pcap_dir = self.pcap_dir+"/"
            self.logger_node.get_logger().warning(f"[pcap_recorder]: invalid pcap dir, must end with '/', saving as'{self.pcap_dir}'")
        self.uri = self.pcap_dir + self.pcap_name
        
        if "/" in self.pcap_name:
            self.pcap_name = self.pcap_name.split("/")[-1]
            self.logger_node.get_logger().warning(f"[pcap_recorder]: invalid pcap name, '/' not permited, saving as'{self.pcap_name}'")
        self.uri = self.pcap_dir + self.pcap_name
        
        # set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_pcap_id()
        
        # set timestamp
        if "TIMESTAMP" in self.uri:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.uri=self.uri.replace("TIMESTAMP",self.timestamp)

        # create dir
        os.makedirs(self.pcap_dir,exist_ok=True)


    def _module_start(self) -> None:
        if self._debug:
            self.logger_node.get_logger().info("[pcap_recorder]: START")

        #self.process = subprocess.Popen(['sudo','tcpdump','-w',self.uri])
        cmd = f"tcpdump-recorder {self.pcap_args} -w {self.uri}"
        args = shlex.split(cmd)
        self.process = subprocess.Popen(args,stderr=open(self.uri + '.log', 'wb'),text=True)

        # monitor tcpdump execution
        self.monitor_thread = threading.Thread(target=self.monitor_callback,daemon=True)
        self.monitor_thread.start()


    def _module_stop(self) -> None:
        if self._debug:
            self.logger_node.get_logger().info("[pcap_recorder]: stop")
        
        self.module_stop = True

        # stop pcap recording
        if hasattr(self,"process") and self.process.poll() is None:
            pid = self.process.pid
            
            subprocess.run(['kill', str(pid)])
            self.process.wait()
    
    def get_pcap_id(self):
        found_pcaps = glob.glob(f"{self.pcap_dir}*__*")
        max_pcap_id = 0
        for pcap in found_pcaps:
            if os.path.isfile(pcap):
                try:
                    pcap_id = int(pcap.split("_")[-1])
                    if pcap_id > max_pcap_id:
                        max_pcap_id = pcap_id
                except (ValueError):
                    pass
        return str(max_pcap_id+1)

    def monitor_callback(self):
        return_code = self.process.wait()
        if not self.module_stop:
            self.logger_node.get_logger().error(f"tcpdump stopped unexpectedly with return code: {return_code}")

    def if_exists_return_value(self, key, config, default):
            if key in config:

                if config[key] is None:
                    self.logger_node.get_logger().warning(f"[pcap_recorder]: value for key:{key} found, but NoneType. Using default value:{default}")
                    return default
                return config[key]
            else:
                self.logger_node.get_logger().warning(f"[pcap_recorder]: value for key:{key} not found, using default value:{default}")
                return default