#!/usr/bin/env python

import rospy
import serial
from geometry_msgs.msg import Twist

def cmd_vel_callback(data):
    speed = int(data.linear.x) # kecepatan yang diterima dari topik
    direction = int(data.angular.z) # arah yang diterima dari topik

    # kirim data ke Arduino melalui serial
    ser.write(str(speed).encode())
    ser.write(b',')
    ser.write(str(direction).encode())
    ser.write(b'\n')

def main():
    rospy.init_node('motor_controller')

    # buka koneksi serial ke Arduino
    global ser
    ser = serial.Serial('/dev/ttyACM0', 9600)

    rospy.Subscriber('cmd_vel', Twist, cmd_vel_callback)

    rospy.spin()

if __name__ == '__main__':
    main()

