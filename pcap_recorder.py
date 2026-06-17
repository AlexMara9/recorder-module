from datetime import datetime
import glob
import os
import subprocess
import threading

from rclpy.node import Node

from modules.imodule import IModule

from .yaml_paths import YamlPaths
import yaml
#TODO add missing log text before tcpdump console output or disable it
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
        with open(yaml_paths.pcap_yaml_path, 'r') as f:
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
        if "TIMESTAMP" in self.uri:
            self.timestamp = datetime.now().strftime(self.timestamp_format)
            self.uri=self.uri.replace("TIMESTAMP",self.timestamp)

        # ask for permissions
        #subprocess.run(['sudo','-v'])

        # create dir
        os.makedirs(self.pcap_dir,exist_ok=True)


    def _module_start(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: START")

        #self.process = subprocess.Popen(['sudo','tcpdump','-w',self.uri])
        self.process = subprocess.Popen(['tcpdump-recorder','-w',self.uri])

        # monitor tcpdump execution
        self.monitor_thread = threading.Thread(target=self.monitor_callback,daemon=True)
        self.monitor_thread.start()


    def _module_stop(self) -> None:
        if self._debug:
            self._logger.info("[pcap_recorder]: stop")
        
        self.module_stop = True

        # stop pcap recording
        if hasattr(self,"process") and self.process.poll() is None:
            pid = self.process.pid
            
            #subprocess.run(['sudo', 'kill', str(pid)])
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
            self._logger.error(f"tcpdump stopped unexpectedly with return code: {return_code}")