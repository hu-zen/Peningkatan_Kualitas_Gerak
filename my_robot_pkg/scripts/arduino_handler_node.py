#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist
import serial
import math
import time

# Konfigurasi port Serial
ser = serial.Serial('/dev/ttyACM0', 57600)
ser.reset_input_buffer()

# Konfigurasi topik Twist
def callback(data):
    # Mendapatkan nilai linear dan angular velocity dari Twist
    lin_vel = data.linear.x
    ang_vel = data.angular.z

    # Menghitung nilai PWM untuk motor kanan dan kiri
    pwm_left = int(lin_vel*(500))  # Dikalikan 100 agar rentangnya menjadi 0-255
    pwm_right = int(lin_vel*(500))  # Dikalikan 100 agar rentangnya menjadi 0-255

    # Menghitung arah motor kanan dan kiri


    if ang_vel == 0:
        if lin_vel > 0:
            direction_left = 0  # Maju
            direction_right = 0  # Maju
        else:
            direction_left = 1  # Maju
            direction_right = 1  # Maju
    elif ang_vel > 0:
        direction_left = 1  # Mundur
        direction_right = 0  # Maju
        pwm_left = int(-ang_vel*(500))
        pwm_right = int(ang_vel*(500))
    else:
        direction_left = 0  # Maju
        direction_right = 1  # Mundur
        pwm_left = int(-ang_vel*(500))
        pwm_right = int(ang_vel*(500))

    # Mengirimkan nilai PWM dan arah ke Arduino melalui Serial
    ser.write(str(pwm_left).encode() + b',' + str(direction_left).encode() + b',' + str(pwm_right).encode() + b',' + str(direction_right).encode() + b'\n')
    # Mencetak nilai PWM dan arah
    rospy.loginfo("PWM Left: {}, Direction Left: {}, PWM Right: {}, Direction Right: {}".format(pwm_left, direction_left, pwm_right, direction_right))

def listener():
    # Inisialisasi node ROS
    rospy.init_node('motor_control', anonymous=True)

    # Subscribe ke topik Twist
    rospy.Subscriber("/cmd_vel", Twist, callback)

    # Menjaga program tetap berjalan
    rospy.spin()

if __name__ == '__main__':
    listener()
