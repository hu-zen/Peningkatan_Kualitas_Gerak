#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

def joy_callback(joy_msg):
    linear_speed = joy_msg.axes[1]  # Assuming linear speed is on the y-axis of the joystick
    angular_speed = joy_msg.axes[3]  # Assuming angular speed is on the 4th axis (e.g., right stick left-right)
    
    # Convert linear_speed and angular_speed to left and right motor speeds
    left_speed = int((linear_speed + angular_speed) * 100)
    right_speed = int((linear_speed - angular_speed) * 100)
    
    # Constrain motor speeds to the range -500 to 500
    left_speed = max(min(left_speed, 500), -500)
    right_speed = max(min(right_speed, 500), -500)

    # Create a Twist message for cmd_vel
    cmd_vel_msg = Twist()
    cmd_vel_msg.linear.x = (left_speed + right_speed) / 200.0  # Convert back to m/s from cm/s
    cmd_vel_msg.angular.z = (right_speed - left_speed) / 200.0  # Convert back to rad/s from deg/s

    # Publish the cmd_vel message
    cmd_vel_pub.publish(cmd_vel_msg)

if __name__ == '__main__':
    rospy.init_node('joy_to_cmd_vel_node')
    rospy.loginfo("Joy to cmd_vel node started")

    # Create a publisher for cmd_vel
    cmd_vel_pub = rospy.Publisher('cmd_vel', Twist, queue_size=10)

    # Subscribe to the joy topic
    joy_sub = rospy.Subscriber('joy', Joy, joy_callback)

    # Spin until shutdown
    rospy.spin()
