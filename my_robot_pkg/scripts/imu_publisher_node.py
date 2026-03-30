#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Imu

import serial

# Inisialisasi node ROS
rospy.init_node('imu_publisher')

# Buat objek Serial untuk komunikasi dengan Arduino
ser = serial.Serial('/dev/ttyUSB0', 9600)

# Buat publisher untuk topik sensor IMU
imu_pub = rospy.Publisher('imu', Imu, queue_size=10)

# Buat objek pesan Imu
imu_msg = Imu()

# Loop utama
while not rospy.is_shutdown():
    # Baca data dari komunikasi serial
    line = ser.readline().strip()

    # Parse data menjadi nilai akselerasi dan kecepatan sudut
    data = line.split(',')
    ax, ay, az, gx, gy, gz = map(int, data)

    # Set nilai akselerasi dalam pesan Imu
    imu_msg.linear_acceleration.x = ax
    imu_msg.linear_acceleration.y = ay
    imu_msg.linear_acceleration.z = az

    # Set nilai kecepatan sudut dalam pesan Imu
    imu_msg.angular_velocity.x = gx
    imu_msg.angular_velocity.y = gy
    imu_msg.angular_velocity.z = gz

    # Publish pesan Imu
    imu_pub.publish(imu_msg)

# Tutup komunikasi serial
ser.close()
