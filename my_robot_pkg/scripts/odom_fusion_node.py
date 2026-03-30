#!/usr/bin/env python3

import rospy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose, Twist
from sensor_msgs.msg import Imu
import tf2_ros
import tf_conversions

class OdomFusionNode:
    def __init__(self):
        rospy.init_node('odom_fusion_node')

        # Subscriber untuk data Odom dari encoder
        self.encoder_sub = rospy.Subscriber('encoder_odom', Odometry, self.encoder_callback)

        # Subscriber untuk data Odom dari Kinect/RTAB-Map
        self.kinect_sub = rospy.Subscriber('kinect_odom', Odometry, self.kinect_callback)

        # Publisher untuk data Odom yang digabungkan
        self.fused_odom_pub = rospy.Publisher('odom', Odometry, queue_size=10)

        # Inisialisasi variabel untuk menyimpan data Odom dari encoder dan Kinect
        self.encoder_odom = None
        self.kinect_odom = None

        # Inisialisasi transform broadcaster untuk frame "odom_combined" ke "base_link"
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()

    def encoder_callback(self, data):
        self.encoder_odom = data

    def kinect_callback(self, data):
        self.kinect_odom = data

    def fuse_odom(self):
        rate = rospy.Rate(10)  # Frekuensi publish

        while not rospy.is_shutdown():
            if self.encoder_odom is not None and self.kinect_odom is not None:
                fused_odom = Odometry()

                # Menggabungkan data posisi dan orientasi dari encoder dan Kinect
                fused_odom.pose.pose.position = self.encoder_odom.pose.pose.position
                fused_odom.pose.pose.orientation = self.kinect_odom.pose.pose.orientation

                # Menggabungkan data kecepatan linear dan sudut dari encoder dan Kinect
                fused_odom.twist.twist.linear = self.encoder_odom.twist.twist.linear
                fused_odom.twist.twist.angular = self.kinect_odom.twist.twist.angular

                # Mengatur frame dan waktu dari data Odom yang digabungkan
                fused_odom.header.frame_id = "odom_combined"
                fused_odom.header.stamp = rospy.Time.now()

                # Menerbitkan data Odom yang digabungkan
                self.fused_odom_pub.publish(fused_odom)

                # Mengirim transformasi dari "odom_combined" ke "base_link"
                transform = tf2_ros.TransformStamped()
                transform.header.stamp = rospy.Time.now()
                transform.header.frame_id = "odom_combined"
                transform.child_frame_id = "base_link"
                transform.transform.translation.x = fused_odom.pose.pose.position.x
                transform.transform.translation.y = fused_odom.pose.pose.position.y
                transform.transform.translation.z = fused_odom.pose.pose.position.z
                transform.transform.rotation = fused_odom.pose.pose.orientation
                self.tf_broadcaster.sendTransform(transform)

            rate.sleep()

if __name__ == '__main__':
    try:
        odom_fusion_node = OdomFusionNode()
        odom_fusion_node.fuse_odom()
    except rospy.ROSInterruptException:
        pass
