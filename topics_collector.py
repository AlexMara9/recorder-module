from typing import Any, List, Tuple, Dict
from rosidl_runtime_py.utilities import get_message

class TopicsCollector():
    topics_enciclopedia: Dict[str, str]

    def __init__(self) -> None:
        pass

    # This function parses all the topics' types given all the topics' names and structure them inside an enciclopedia, meaning a dictionary 
    # <topic_name, topic_type>
    # Once known as "eat_and_digest()". RIP :(
    def parse(self, topics_names: List[str], topic_names_and_types: List[Tuple[str, List[str]]]) -> None:
        self.topics_names = topics_names
        self.topic_names_and_types = topic_names_and_types

        self.topics_enciclopedia: Dict[str, str]

        for topic_name in self.topics_names:
            topic_tuple = list(filter(lambda t: t[0] == topic_name, self.topic_names_and_types))[0]

            self.topics_enciclopedia[topic_name] = topic_tuple[1][0]
        
    def extract_topic_type_as_string(self, topic_name) -> str:
        return self.topics_enciclopedia[topic_name]

    def extract_topic_type_as_class(self, topic_name) -> Any:
        return get_message(self.topics_enciclopedia[topic_name])