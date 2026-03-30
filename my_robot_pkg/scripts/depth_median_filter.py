#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

class DepthMedianFilterSafe:
    def __init__(self):
        rospy.init_node('depth_median_filter', anonymous=False)
        self.bridge = CvBridge()
        self.buf = []
        self.bufsize = rospy.get_param('~buffer_size', 3)
        self.in_topic = rospy.get_param('~in_topic', '/camera/depth_registered/image_raw')
        self.out_topic = rospy.get_param('~out_topic', '/camera/depth_registered/image_filtered')
        self.pub = rospy.Publisher(self.out_topic, Image, queue_size=1)
        rospy.Subscriber(self.in_topic, Image, self.cb, queue_size=1, buff_size=2**24)
        rospy.loginfo("depth_median_filter: %s -> %s (buf=%d)", self.in_topic, self.out_topic, self.bufsize)

    def cb(self, msg):
        try:
            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
        except CvBridgeError as e:
            rospy.logerr("depth_median_filter: cv_bridge error: %s", e)
            return

        # replace zeros with nan for median operation
        depth = depth.astype(np.float32)
        depth[depth <= 0.0] = np.nan

        self.buf.append(depth)
        if len(self.buf) > self.bufsize:
            self.buf.pop(0)

        stacked = np.stack(self.buf, axis=0)
        med = np.nanmedian(stacked, axis=0).astype(np.float32)

        # replace any remaining NaN with +inf so depth->laserscan treats them as out of range
        nan_mask = np.isnan(med)
        if np.any(nan_mask):
            med[nan_mask] = np.inf

        out = self.bridge.cv2_to_imgmsg(med, encoding='32FC1')
        out.header = msg.header  # preserve stamp from latest incoming
        self.pub.publish(out)

if __name__ == "__main__":
    try:
        DepthMedianFilterSafe()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
