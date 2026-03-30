#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
import tf
import math
import numpy as np

class PoseFilter:
    def __init__(self):
        rospy.init_node('pose_filter')

        # Subscribe dari ekf (pose hasil gabungan sensor)
        self.sub = rospy.Subscriber('/odom_data_quat', Odometry, self.odom_callback)
        self.pub = rospy.Publisher('/filtered_pose', PoseWithCovarianceStamped, queue_size=10)

        # Buffer posisi sebelumnya untuk smoothing
        self.last_position = None
        self.alpha = rospy.get_param('~alpha', 0.7)   # smoothing factor (0.0 = no smooth, 1.0 = freeze)
        self.last_yaw = None

        rospy.loginfo("Pose Filter aktif dengan alpha=%.2f", self.alpha)
        rospy.spin()

    def odom_callback(self, msg):
        # Ambil posisi dan orientasi sekarang
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        ori = msg.pose.pose.orientation

        _, _, yaw = tf.transformations.euler_from_quaternion([ori.x, ori.y, ori.z, ori.w])

        # Jika ada data sebelumnya, lakukan smoothing
        if self.last_position is not None:
            x = self.alpha * self.last_position[0] + (1 - self.alpha) * x
            y = self.alpha * self.last_position[1] + (1 - self.alpha) * y

            # smoothing sudut juga
            if self.last_yaw is not None:
                dyaw = math.atan2(math.sin(yaw - self.last_yaw), math.cos(yaw - self.last_yaw))
                yaw = self.last_yaw + (1 - self.alpha) * dyaw

        # Simpan nilai terakhir
        self.last_position = (x, y)
        self.last_yaw = yaw

        # Konversi balik ke quaternion
        quat = tf.transformations.quaternion_from_euler(0, 0, yaw)

        # Publikasi pose yang sudah difilter
        filtered_pose = PoseWithCovarianceStamped()
        filtered_pose.header = msg.header
        filtered_pose.header.frame_id = "map"
        filtered_pose.pose.pose.position.x = x
        filtered_pose.pose.pose.position.y = y
        filtered_pose.pose.pose.position.z = 0
        filtered_pose.pose.pose.orientation.x = quat[0]
        filtered_pose.pose.pose.orientation.y = quat[1]
        filtered_pose.pose.pose.orientation.z = quat[2]
        filtered_pose.pose.pose.orientation.w = quat[3]

        # Copy covariance (bisa disesuaikan untuk filtering yang lebih agresif)
        filtered_pose.pose.covariance = list(msg.pose.covariance)

        self.pub.publish(filtered_pose)

if __name__ == '__main__':
    try:
        PoseFilter()
    except rospy.ROSInterruptException:
        pass

