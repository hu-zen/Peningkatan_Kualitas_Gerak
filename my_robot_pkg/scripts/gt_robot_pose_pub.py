#!/usr/bin/env python3

import rospy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose

def odom_callback(odom_msg):
    # Dapatkan data pose dari pesan odometri
    pose_data = odom_msg.pose.pose

    # Publish data pose ke topik lain
    pose_pub.publish(pose_data)

rospy.init_node('pose_publisher_node', anonymous=True)
pose_pub = rospy.Publisher('robot_pose', Pose, queue_size=10)
odom_sub = rospy.Subscriber('/rtabmap/odom', Odometry, odom_callback)

rospy.spin()


