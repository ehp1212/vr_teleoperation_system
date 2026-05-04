import threading
import rclpy
from rclpy.executors import MultiThreadedExecutor
from enum import Enum, auto

from .ros.tele_op_node import TeleopNode
from .semantic_frontier_explorer import SemanticFrontierExplorer

class RobotState(Enum):
    IDLE = auto()
    MANUAL = auto()
    FRONTIER = auto()

class RobotStateOrchestrator:
    """
    Main manager for handling the robot's states and mode transitions.
    """
    def __init__(self, semantic_map_manager):
        # 1. State Definition
        self.current_mode = RobotState.IDLE
        
        # 2. Inject Memory & Reasoner
        self.map_manager = semantic_map_manager
        
        # 3. Initialize ROS 2 Frontier Node
        # Passing the manager and reasoner for decoupled logic
        
        rclpy.init()
        self.teleop_node = TeleopNode()
        self.frontier_node = SemanticFrontierExplorer(semantic_map_manager)

        self.executor = MultiThreadedExecutor()

        self.executor.add_node(self.teleop_node)
        self.executor.add_node(self.frontier_node)
        
        self.ros_thread = threading.Thread(target=self._run_ros_executor, daemon=True)
        self.ros_thread.start()

    def _run_ros_executor(self):
        """
        Runs the ROS 2 event loop in a background thread.
        This ensures ROS doesn't block the main WebRTC/Perception loop.
        """
        try:
            self.executor.spin()
        finally:
            self.executor.shutdown()
            self.teleop_node.destroy_node()
            self.frontier_node.destroy_node()

    def set_mode(self, new_mode: RobotState):
        """
        State Machine Transition Logic.
        Triggered by UI commands via WebRTC DataChannel.
        """
        if self.current_mode == new_mode:
            return

        print(f"[Orchestrator] Transitioning state: {self.current_mode} -> {new_mode}")
        
        # Clean up previous state
        if self.current_mode is RobotState.FRONTIER:
            self.frontier_node.stop_exploration()

        # Initialize new state
        self.current_mode = new_mode
        if new_mode is RobotState.FRONTIER:
            self.frontier_node.start_exploration()
        elif new_mode == RobotState.MANUAL:
            # In manual mode, ensure Nav2 is not overriding commands
            self.frontier_node.cancel_all_goals()

    def get_system_status(self):
        """
        Returns the current state for UI feedback.
        """
        return {
            "mode": self.current_mode,
            # "map_objects_count": len(self.map_manager.get_clean_map()),
            "ros_active": rclpy.ok()
        }