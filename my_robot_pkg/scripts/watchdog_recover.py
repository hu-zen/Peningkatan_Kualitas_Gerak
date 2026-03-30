#!/usr/bin/env python3
import rospy
import time
from std_srvs.srv import Empty
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry

last_scan_time = 0
last_odom_time = 0
SCAN_TIMEOUT = 3.0
ODOM_TIMEOUT = 3.0
RESET_COOLDOWN = 5.0
last_reset_time = 0

def scan_cb(msg):
    global last_scan_time
    last_scan_time = time.time()

def odom_cb(msg):
    global last_odom_time
    last_odom_time = time.time()

if __name__ == "__main__":
    rospy.init_node("watchdog_recovery", anonymous=False)
    rospy.Subscriber("/scan", LaserScan, scan_cb)
    rospy.Subscriber("/odom", Odometry, odom_cb)

    rospy.loginfo("watchdog_recovery: waiting for /request_nomap_reset service (gmapping)...")
    try:
        rospy.wait_for_service("/request_nomap_reset", timeout=10)
        reset_map = rospy.ServiceProxy("/request_nomap_reset", Empty)
    except Exception as e:
        rospy.logwarn("watchdog_recovery: reset service not available: %s", e)
        reset_map = None

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        now = time.time()
        scan_ok = (now - last_scan_time) < SCAN_TIMEOUT
        odom_ok = (now - last_odom_time) < ODOM_TIMEOUT
        if not scan_ok or not odom_ok:
            if reset_map and (now - last_reset_time > RESET_COOLDOWN):
                rospy.logwarn("watchdog_recovery: no /scan or /odom >3s, requesting gmapping reset...")
                try:
                    reset_map()
                    rospy.loginfo("watchdog_recovery: gmapping reset requested.")
                    last_reset_time = now
                except Exception as e:
                    rospy.logerr("watchdog_recovery: reset failed: %s", e)
        rate.sleep()
