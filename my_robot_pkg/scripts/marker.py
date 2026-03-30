#!/usr/bin/env python3

import rospy
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker
import geometry_msgs.msg
from tf.transformations import euler_from_quaternion

rospy.init_node('path_marker_publisher')

marker_pub = rospy.Publisher('path_marker', Marker, queue_size=10)

marker = Marker()
marker.header.frame_id = "odom"
marker.type = Marker.LINE_STRIP
marker.action = Marker.ADD
marker.scale.x = 0.1  # Lebar jalur
marker.color.a = 1.0
marker.color.r = 1.0
marker.color.g = 0.0
marker.color.b = 0.0

path_positions = []

def odometry_callback(msg):
    global path_positions
    position = msg.pose.pose.position
    point = geometry_msgs.msg.Point()
    point.x = position.x
    point.y = position.y
    point.z = position.z
    path_positions.append(point)

    marker.points = path_positions
    marker.header.stamp = rospy.Time.now()
    marker_pub.publish(marker)

odom_sub = rospy.Subscriber('/rtabmap/odom', Odometry, odometry_callback)

rospy.spin()
