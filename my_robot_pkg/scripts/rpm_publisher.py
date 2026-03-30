#!/usr/bin/env python3

import rospy
from std_msgs.msg import Int16, Float32
import time

# --- Konstanta Fisik Robot (Salin dari skrip asli Anda) ---
TICKS_PER_REVOLUTION = 76.433121 
WHEEL_RADIUS = 0.15
#--------------------------------------------------------------------

# Variabel global untuk kalkulasi
last_time_right = None
last_ticks_right = 0
last_time_left = None
last_ticks_left = 0

# --- Variabel untuk Filter Penghalus ---
# Faktor penghalusan (alpha). Semakin kecil, semakin halus. (0.0 - 1.0)
smoothing_factor = 0.2 
smoothed_rpm_right = 0.0
smoothed_rpm_left = 0.0
# ----------------------------------------

# Publisher akan mem-publish data yang sudah dihaluskan
rpm_right_pub = rospy.Publisher('/rpm/right_wheel_smoothed', Float32, queue_size=10)
rpm_left_pub = rospy.Publisher('/rpm/left_wheel_smoothed', Float32, queue_size=10)

def right_ticks_callback(msg):
    global last_time_right, last_ticks_right, smoothed_rpm_right

    current_time = time.time()
    current_ticks = msg.data

    if last_time_right is not None:
        delta_time = current_time - last_time_right
        delta_ticks = current_ticks - last_ticks_right

        if delta_time > 0:
            raw_rpm = (delta_ticks / TICKS_PER_REVOLUTION) / (delta_time / 60.0)
            smoothed_rpm_right = (smoothing_factor * raw_rpm) + ((1 - smoothing_factor) * smoothed_rpm_right)
            rpm_right_pub.publish(smoothed_rpm_right)
            
    last_time_right = current_time
    last_ticks_right = current_ticks

def left_ticks_callback(msg):
    global last_time_left, last_ticks_left, smoothed_rpm_left

    current_time = time.time()
    current_ticks = msg.data

    if last_time_left is not None:
        delta_time = current_time - last_time_left
        delta_ticks = current_ticks - last_ticks_left

        if delta_time > 0:
            raw_rpm = (delta_ticks / TICKS_PER_REVOLUTION) / (delta_time / 60.0)
            smoothed_rpm_left = (smoothing_factor * raw_rpm) + ((1 - smoothing_factor) * smoothed_rpm_left)
            rpm_left_pub.publish(smoothed_rpm_left)

    last_time_left = current_time
    last_ticks_left = current_ticks

if __name__ == '__main__':
    rospy.init_node('rpm_publisher_node')
    rospy.Subscriber('right_ticks', Int16, right_ticks_callback)
    rospy.Subscriber('left_ticks', Int16, left_ticks_callback)
    rospy.loginfo("RPM Publisher Node with Smoothing Filter is running...")
    rospy.spin()
