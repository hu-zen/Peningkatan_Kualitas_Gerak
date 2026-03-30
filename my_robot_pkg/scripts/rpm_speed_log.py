#!/usr/bin/env python3

import rospy
from std_msgs.msg import Int16
from geometry_msgs.msg import Twist
import csv
import os
import signal
import sys

# Informasi robot
diameter_roda = 0.15  # Diameter roda dalam meter
pulse_per_rev = 36  # Pulse per Rev

# Inisialisasi variabel untuk menghitung ticks
right_ticks = 0
left_ticks = 0
prev_right_ticks = 0
prev_left_ticks = 0

# Inisialisasi waktu sebelumnya
start_time = None

# List untuk menyimpan data yang akan disimpan di file CSV
data_to_save = []

# Nama file CSV default
csv_file_name = "robot_data.csv"

# Fungsi untuk menghitung RPM
def calculate_rpm(ticks, prev_ticks, time_elapsed):
    delta_ticks = ticks - prev_ticks
    return (delta_ticks / pulse_per_rev) / (time_elapsed / 60.0)

# Fungsi callback untuk topik right_ticks
def right_ticks_callback(data):
    global right_ticks, prev_right_ticks, start_time
    right_ticks = data.data
    if start_time is None:
        start_time = rospy.get_time()
    time_elapsed = rospy.get_time() - start_time
    if time_elapsed > 0:
        right_rpm = calculate_rpm(right_ticks, prev_right_ticks, time_elapsed)
        prev_right_ticks = right_ticks
        rospy.loginfo("RPM Right Wheel: %f", right_rpm)

# Fungsi callback untuk topik left_ticks
def left_ticks_callback(data):
    global left_ticks, prev_left_ticks, start_time
    left_ticks = data.data
    if start_time is None:
        start_time = rospy.get_time()
    time_elapsed = rospy.get_time() - start_time
    if time_elapsed > 0:
        left_rpm = calculate_rpm(left_ticks, prev_left_ticks, time_elapsed)
        prev_left_ticks = left_ticks
        rospy.loginfo("RPM Left Wheel: %f", left_rpm)

# Fungsi callback untuk topik cmd_vel
def cmd_vel_callback(data):
    global start_time, linear_speed, angular_speed
    linear_speed = data.linear.x
    angular_speed = data.angular.z
    if start_time is None:
        start_time = rospy.get_time()
    time_elapsed = rospy.get_time() - start_time
    if time_elapsed > 0:
        data_to_save.append({
            'Time (s)': time_elapsed,
            'RPM Left Wheel': calculate_rpm(left_ticks, prev_left_ticks, time_elapsed),
            'RPM Right Wheel': calculate_rpm(right_ticks, prev_right_ticks, time_elapsed),
            'Linear Speed (m/s)': linear_speed,
            'Angular Speed (rad/s)': angular_speed
        })

# Fungsi untuk menyimpan data ke dalam file CSV
def save_to_csv():
    global data_to_save, csv_file_name
    with open(csv_file_name, mode='w') as csv_file:
        fieldnames = ['Time (s)', 'RPM Left Wheel', 'RPM Right Wheel', 'Linear Speed (m/s)', 'Angular Speed (rad/s)']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(data_to_save)
    rospy.loginfo(f"Saved data to {csv_file_name}")

# Tangani sinyal SIGINT (Ctrl+C) untuk menyimpan data dan mengizinkan pengguna memasukkan nama file CSV
def signal_handler(sig, frame):
    global csv_file_name, data_to_save
    if len(data_to_save) > 0:
        save_to_csv()
        data_to_save = []  # Bersihkan data yang telah disimpan
    rospy.loginfo("Program terminated. CSV saved.")
    # Meminta pengguna untuk memasukkan nama file CSV yang diinginkan
    csv_file_name = input("Enter CSV file name (e.g., robot_data.csv): ")
    sys.exit(0)

# Atur handler sinyal SIGINT
signal.signal(signal.SIGINT, signal_handler)

# Fungsi utama
if __name__ == '__main__':
    rospy.init_node('wheel_speed_node', anonymous=True)
    rospy.Subscriber("right_ticks", Int16, right_ticks_callback)
    rospy.Subscriber("left_ticks", Int16, left_ticks_callback)
    rospy.Subscriber("cmd_vel", Twist, cmd_vel_callback)

    rate = rospy.Rate(1)  # Frekuensi pembaruan 1 Hz (1 detik)
    
    while not rospy.is_shutdown():
        if start_time is None:
            rospy.loginfo("Waiting for data on topics...")
        else:
            time_elapsed = rospy.get_time() - start_time

            if time_elapsed > 0:
                data_to_save.append({
                    'Time (s)': time_elapsed,
                    'RPM Left Wheel': calculate_rpm(left_ticks, prev_left_ticks, time_elapsed),
                    'RPM Right Wheel': calculate_rpm(right_ticks, prev_right_ticks, time_elapsed),
                    'Linear Speed (m/s)': linear_speed,
                    'Angular Speed (rad/s)': angular_speed
                })

        rate.sleep()

    rospy.loginfo("Program terminated. CSV saved.")
