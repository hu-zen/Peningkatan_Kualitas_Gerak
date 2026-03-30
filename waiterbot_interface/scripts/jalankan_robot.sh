#!/bin/bash


export ROS_MASTER_URI=http://localhost:11311
export ROS_HOSTNAME=localhost


source /opt/ros/noetic/setup.bash 

source /home/iascr/ros_catkin_ws/devel/setup.bash

source /home/iascr/Ybot_ws/devel/setup.bash

source /home/iascr/catkin_ws/devel/setup.bash


cd /home/iascr/catkin_ws/src/waiterbot_interface/scripts/

echo "Environment loaded. Current directory: $(pwd)"
echo "Starting GUI..."

python3 gui.py
