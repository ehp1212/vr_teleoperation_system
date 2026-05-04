# robot_infrastructure.launch.py

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():

    # Path to the URDF file based on your project structure
    # humanoid_digital_twin/assets/robot_car/urdf/robot_car.urdf
    home_dir = os.path.expanduser('~')
    urdf_path = os.path.join(
        home_dir,
        'personal_project',
        'humanoid_digital_twin',
        'assets',
        'robot_car',
        'urdf',
        'robot_car.urdf'
    )

    # ROS 2 package share directories
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # Simulation time should be True for Isaac Sim
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # A. Robot State Publisher: publishes static TFs from URDF
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': use_sim_time
        }]
    )

    # B. SLAM Toolbox: online async mapping
    #
    # Important:
    # Default slam_toolbox often uses base_footprint.
    # Your Nav2 / Isaac setup appears to use base_link, so override it here.
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,

            # Frame names
            'map_frame': 'map',
            'odom_frame': 'odom',
            'base_frame': 'base_link',

            # LaserScan topic from Isaac Sim RTX LiDAR
            'scan_topic': '/scan',

            # Mapping mode
            'mode': 'mapping',

            # Common safe defaults
            'resolution': 0.05,
            'max_laser_range': 20.0,
            'minimum_time_interval': 0.5,
            'transform_timeout': 0.2,
            'tf_buffer_duration': 30.0,
            'stack_size_to_use': 40000000,
            'publish_period': 0.05,
            'map_update_interval': 2.0,
        }]
    )

    # C. Nav2: navigation stack
    #
    # navigation_launch.py excludes AMCL and map_server.
    # This is appropriate when slam_toolbox is publishing map -> odom.
    nav2_navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time from Isaac Sim /clock'
        ),

        robot_state_publisher,
        slam_toolbox_node,
        nav2_navigation_launch
    ])