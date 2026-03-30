#!/usr/bin/env python3

import rospy
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion
from math import sin, cos, pi
from tf.transformations import quaternion_from_euler

class RobotControlNode:
    def __init__(self):
        rospy.init_node('robot_control_node')

        # Mendapatkan resolusi encoder dari konfigurasi robot
        self.encoder_resolution = 36  # Ganti dengan resolusi encoder yang sesuai

        # Mendapatkan radius roda dan panjang wheelbase dari konfigurasi robot
        self.wheel_radius = 0.15  # Ganti dengan radius roda yang sesuai
        self.wheelbase_length = 0.41  # Ganti dengan panjang wheelbase yang sesuai

        # Deklarasi variabel-variabel global untuk menyimpan posisi dan orientasi robot
        self.last_time = rospy.Time.now()
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # Mendefinisikan publisher untuk menggerakkan joint kanan dan kiri
        self.joint_publisher_right = rospy.Publisher('/robot/left_wheel_joint_controller/command', Float64, queue_size=10)
        self.joint_publisher_left = rospy.Publisher('/robot/right_wheel_joint_controller/command', Float64, queue_size=10)

        # Mendefinisikan publisher untuk odometry
        self.odom_publisher = rospy.Publisher('/odom', Odometry, queue_size=10)

        # Mendefinisikan subscriber untuk menerima data posisi roda kanan dan kiri
        rospy.Subscriber('right_ticks', Float64, self.callback_right)
        rospy.Subscriber('left_ticks', Float64, self.callback_left)

    def callback_right(self, data):
        # Mendapatkan data posisi dari topic right_ticks
        right_pos = float(data.data)

        # Menghitung perubahan posisi dan orientasi berdasarkan data encoder
        current_time = rospy.Time.now()
        dt = (current_time - self.last_time).to_sec()

        delta_right = (right_pos / self.encoder_resolution) * (2 * pi * self.wheel_radius)
        delta_theta = (delta_right / self.wheelbase_length) * dt

        delta_x = delta_right * cos(self.theta)
        delta_y = delta_right * sin(self.theta)

        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta

        self.last_time = current_time

        # Menggerakkan joint kanan menggunakan data posisi yang dihitung
        self.joint_publisher_right.publish(delta_right)

        # Publish pesan odometri
        self.publish_odometry()

    def callback_left(self, data):
        # Mendapatkan data posisi dari topic left_ticks
        left_pos = float(data.data)

        # Menghitung perubahan posisi dan orientasi berdasarkan data encoder
        current_time = rospy.Time.now()
        dt = (current_time - self.last_time).to_sec()

        delta_left = (left_pos / self.encoder_resolution) * (2 * pi * self.wheel_radius)
        delta_theta = (delta_left / self.wheelbase_length) * dt

        delta_x = delta_left * cos(self.theta)
        delta_y = delta_left * sin(self.theta)

        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta

        self.last_time = current_time

        # Menggerakkan joint kiri menggunakan data posisi yang dihitung
        self.joint_publisher_left.publish(delta_left)

        # Publish pesan odometri
        self.publish_odometry()

    def publish_odometry(self):
        odom = Odometry()
        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        # Set posisi
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0

        # Set orientasi menggunakan kuaternion
        q = quaternion_from_euler(0.0, 0.0, self.theta)
        odom.pose.pose.orientation = Quaternion(*q)

        # Set kecepatan linear
        odom.twist.twist.linear.x = (self.x - odom.pose.pose.position.x) / (odom.header.stamp - self.last_time).to_sec()
        odom.twist.twist.linear.y = (self.y - odom.pose.pose.position.y) / (odom.header.stamp - self.last_time).to_sec()
        odom.twist.twist.angular.z = (self.theta - odom.pose.pose.orientation.z) / (odom.header.stamp - self.last_time).to_sec()

        # Publish pesan odometri
        self.odom_publisher.publish(odom)

if __name__ == '__main__':
    try:
        robot_control_node = RobotControlNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
