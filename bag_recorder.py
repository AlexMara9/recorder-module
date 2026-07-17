# from modules.bag_recorder_module import IModule, AsState
from datetime import datetime
import glob
import os
import subprocess
import threading
import shlex

from rclpy.node import Node

from modules.imodule import IModule

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
        self.config=config


    def _module_init(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: INIT")
        
        config = self.config

#       ===== BAG INIT =====
        
        # init variables
        self.bag_dir = self.if_exists_return_value('bag_dir', config, "./bag/")
        self.bag_name = self.if_exists_return_value('bag_name', config, "./bag/")
        self.timestamp_format = self.if_exists_return_value('date_format', config, "%Y%m%d_%H%M%S")
        self.use_id = self.if_exists_return_value('enable_ids', config, False)
        self.qos_path = self.if_exists_return_value('qos_profile_path', config, "")
        self.qos_profile = "" if self.qos_path == "" else "--qos-profile-overrides-path " + str(self.qos_path)
        self.bag_args = self.if_exists_return_value('bag_args', config, "")
        self.bag_topics = self.if_exists_return_value('topics', config, "")

        # set state
        self.module_stop = False

        # set bag uri
        #  check if bag_dir ends with /
        if self.bag_dir[-1] != "/":
            self.bag_dir = self.bag_dir+"/"
            self._logger.warning(f"[bag_recorder]: invalid bag dir, must end with '/', saving as'{self.bag_dir}'")
        self.uri = self.bag_dir + self.bag_name
        #  check if bag_name ends with /
        if "/" in self.bag_name:
            self.bag_name = self.bag_name.split("/")[-1]
            self._logger.warning(f"[bag_recorder]: invalid bag name, '/' not permited, saving as'{self.bag_name}'")
        
        self.uri = self.bag_dir + self.bag_name
        
        #  set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_bag_id()
        
        #  set timestamp
        if "TIMESTAMP" in self.uri:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.uri = self.uri.replace("TIMESTAMP",self.timestamp)

        # create dirs
        os.makedirs(self.bag_dir, exist_ok=True)

        if self._debug:
            self._logger.info(f"[bag_recorder]: bag uri: {self.uri}")



    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: START")

        cmd = f"ros2 bag record {self.bag_args} {self.qos_profile} -o {self.uri} {self.bag_topics}"
        args = shlex.split(cmd)
        self.process = subprocess.Popen(args, stderr=open(self.uri + '.log', 'wb'), text=True)

        if self._debug:
            self._logger.info("[bag_recorder]: subprocess created")
        
        self.monitor_thread = threading.Thread(target=self.monitor_callback,daemon=True)
        self.monitor_thread.start()


    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: stop")

        self.module_stop = True

        # stop pcap recording
        if hasattr(self,"process") and self.process.poll() is None:
            pid = self.process.pid
            
            #subprocess.run(['sudo', 'kill', str(pid)])
            subprocess.run(['kill', str(pid)])
            self.process.wait()
    
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

    def monitor_callback(self):
        return_code = self.process.wait()
        if not self.module_stop:
            self._logger.error(f"ros2 bag record stopped unexpectedly with return code: {return_code}")

    def if_exists_return_value(self, key, config, default):
        if key in config:
            return config[key]
        else:
            self._logger.warning(f"[bag_recorder]: value for key:{key} not found, using default value:{default}")
            return default