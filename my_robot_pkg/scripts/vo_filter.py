#!/usr/bin/env python3
import rospy
from nav_msgs.msg import Odometry
import math

def is_finite(x):
    return not (math.isinf(x) or math.isnan(x))

class VOFilterNode:
    def __init__(self):
        rospy.init_node('vo_filter', anonymous=False)
        self.max_age = rospy.get_param('~max_age', 0.15)
        self.max_pos = rospy.get_param('~max_pos', 100.0)
        in_topic = rospy.get_param('~vo_in', '/vo')
        out_topic = rospy.get_param('~vo_out', '/vo_filtered')

        self.pub = rospy.Publisher(out_topic, Odometry, queue_size=5)
        self.sub = rospy.Subscriber(in_topic, Odometry, self.cb)
        self.dropped = 0
        rospy.loginfo("vo_filter: forwarding %s -> %s (max_age=%.3f)", in_topic, out_topic, self.max_age)
        
    def cb(self, msg):
        now = rospy.Time.now()
        age = (now - msg.header.stamp).to_sec()
        if age > self.max_age:
            self.dropped += 1
            rospy.logwarn_throttle(5, "vo_filter: dropping stale vo (age=%.3f) total_dropped=%d", age, self.dropped)
            return

        p = msg.pose.pose.position
        o = msg.pose.pose.orientation
        if not (is_finite(p.x) and is_finite(p.y) and is_finite(p.z) and
                is_finite(o.x) and is_finite(o.y) and is_finite(o.z) and is_finite(o.w)):
            self.dropped += 1
            rospy.logwarn_throttle(5, "vo_filter: dropping vo with NaN/Inf pose total_dropped=%d", self.dropped)
            return

        if abs(p.x) > self.max_pos or abs(p.y) > self.max_pos or abs(p.z) > self.max_pos:
            self.dropped += 1
            rospy.logwarn_throttle(5, "vo_filter: dropping vo with huge pos (%.3f,%.3f,%.3f)", p.x, p.y, p.z)
            return

        msg.header.stamp = rospy.Time.now()
        self.pub.publish(msg)

if __name__ == '__main__':
    try:
        VOFilterNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
