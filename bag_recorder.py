# from modules.bag_recorder_module import IModule, AsState
from datetime import datetime
import glob
import os
import subprocess
import threading
import shlex

from rclpy.node import Node

from modules.imodule import IModule

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
        
        yaml_paths = YamlPaths()

        if not os.path.exists(yaml_paths.bag_yaml_path):
            self._logger.error(f"[bag_recorder]: bag's yaml path doesn't exist. Path: {yaml_paths.bag_yaml_path}")

            return
        
        with open(yaml_paths.bag_yaml_path, 'r') as f:
            yaml_data = yaml.load(f, Loader=yaml.FullLoader)

        if not self.yaml_integrity_check(yaml_data):
            return

#       ===== BAG INIT =====      
        self.bag_dir = "" if yaml_data['bag_dir'] is None else str(yaml_data['bag_dir']) #"./bags/"
        self.bag_name = "" if yaml_data['bag_name'] is None else str(yaml_data['bag_name'])
        self.bag_topics = "" if yaml_data['topics'] is None else str(yaml_data['topics'])#["/canbus/imu/data","/debug/clutch"]
        self.bag_args = "" if yaml_data['bag_args'] is None else str(yaml_data['bag_args'])
        self.use_id = False if yaml_data['enable_ids'] is None else bool(yaml_data['enable_ids']) #false
        if 'date_format' in yaml_data and yaml_data['date_format'] is not None:
            self.timestamp_format=yaml_data['date_format']#"%Y%m%d_%H%M%S"

        #self.all_topics = Node.get_topic_names_and_types(self.recorder_node)
        
        self.timestamp : datetime
        self.module_stop = False

        #if self._debug:
        #    self._logger.info(f"[bag_recorder]: all topics |{self.all_topics}|")
        #    self._logger.info(f"[bag_recorder]: bag topics |{self.bag_topics}|")
        

        # set bag uri
        if self.bag_dir[-1] != "/":
            self.bag_dir = self.bag_dir+"/"
            self._logger.warning(f"[bag_recorder]: invalid bag dir, must end with '/', saving as'{self.bag_dir}'")
        self.uri = self.bag_dir + self.bag_name
        
        if "/" in self.bag_name:
            self.bag_name = self.bag_name.split("/")[-1]
            self._logger.error(f"[bag_recorder]: invalid bag name, '/' not permited, saving as'{self.bag_name}'")
        self.uri = self.bag_dir + self.bag_name
        
        # set id
        if self.use_id:
            self.uri = self.uri + "__" + self.get_bag_id()
        
        # set timestamp
        if "TIMESTAMP" in self.uri and 'date_format' in yaml_data and yaml_data['date_format'] is not None:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.uri = self.uri.replace("TIMESTAMP",self.timestamp)

        if self._debug:
            self._logger.info(f"[bag_recorder]: bag uri: {self.uri}")

        os.makedirs(self.bag_dir, exist_ok=True)



    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[bag_recorder]: START")

        cmd = f"ros2 bag record {self.bag_args} -o {self.uri} {self.bag_topics}"
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

    def yaml_integrity_check(self, yaml_data) -> bool:
        if 'bag_dir' not in yaml_data:
            self._logger.error(f"[bag_recorder]: bag's dir record isn't present inside bag's yaml. Unable to continue")
            return False
        
        if 'bag_args' not in yaml_data:
            self._logger.error(f"[bag_recorder]: bag's args record isn't present inside bag's yaml. Unable to continue")
            return False
    
        if 'topics' not in yaml_data:
            self._logger.error(f"[bag_recorder]: bag's topics record isn't present inside bag's yaml. Unable to continue")
            return False

        if 'bag_name' not in yaml_data:
            self._logger.error(f"[bag_recorder]: bag's name record isn't present inside bag's yaml. Unable to continue")
            return False
        
        if 'enable_ids' not in yaml_data:
            self._logger.error(f"[bag_recorder]: enable_ids record isn't present inside bag's yaml. Unable to continue")
            return False
        
        return True