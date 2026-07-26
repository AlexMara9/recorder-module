from abc import ABC, abstractmethod
from enum import IntEnum
from rclpy.node import Node

class AsState(IntEnum):
    IDLE = 0
    CHECKING = 1
    READY = 2
    DRIVE = 3
    FINISH = 4
    EMERGENCY = 5

class IModule(ABC):
    def __init__(self, debug: bool, start_state: AsState, config: dict, node: Node) -> None:
        super().__init__()
        self._debug = debug
        self._config = config
        self._init_on_state =AsState(config['init_on_state'])
        self._start_on_state = AsState(config['start_on_state'])
        self._stop_on_state = AsState(config['stop_on_state'])
        self._node = node
        self._current_state = None
        self._start_state = start_state
        
    @abstractmethod
    def _module_init(self) -> None:
        """Initialize the module."""    # not a class constructor
        pass
    
    @abstractmethod
    def _module_start(self) -> None:
        """Start the module. Called when the AS enters the start_on_state."""
        pass
    
    @abstractmethod
    def _module_stop(self) -> None:
        """Stop the module. Called when the AS enters the stop_on_state."""
        pass

    def _jump_start(self) -> None:
        while self._current_state != self._start_state:
            if self._current_state is not None and self._current_state >= self._start_state:
                return
            self.on_state_change(self._current_state + 1 if self._current_state is not None else AsState.IDLE)

    def _next_state(self, state) -> IntEnum:
        return self._current_state + 1 if self._current_state is not None else AsState.IDLE
    
    def _next_state_is_correct(self, state) -> bool:
        return state == self._next_state(state)
    
    def _module_manager(self, state) -> None:
        if self._init_on_state == state:
            self._module_init()
        if self._start_on_state == state:
            self._module_start()
        if self._stop_on_state == state:
            self._module_stop()
    
    def on_state_change(self, state) -> None:
        match state:
            case AsState.IDLE:
                if not self._next_state_is_correct(state): return
                self._current_state = state
                self._module_manager(state)

            case AsState.CHECKING:
                if not self._next_state_is_correct(state): return
                self._current_state = state
                self._module_manager(state)

            case AsState.READY:
                if not self._next_state_is_correct(state): return
                self._current_state = state
                self._module_manager(state)

            case AsState.DRIVE:
                if not self._next_state_is_correct(state): return
                self._current_state = state
                self._module_manager(state)

            case AsState.FINISH:
                if not self._next_state_is_correct(state): return
                self._current_state = state
                self._module_manager(state)

            case AsState.EMERGENCY:
                self._current_state = state
                self._module_stop()
            
            case _:
                pass