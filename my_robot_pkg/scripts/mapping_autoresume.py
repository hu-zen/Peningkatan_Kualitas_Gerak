#!/usr/bin/env python3
import rospy
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
import time
import math

class MappingAutoResume:
    def __init__(self):
        rospy.init_node("mapping_autoresume", anonymous=False)

        # Subscribes
        rospy.Subscriber("/odom_data_quat", Odometry, self.odom_cb)

        # Internal state
        self.last_pose = None
        self.last_active = time.time()
        self.freeze_secs = rospy.get_param("~freeze_secs", 3.0)
        self.resume_secs = rospy.get_param("~resume_secs", 15.0)
        self.freeze_reported = False

        # Publikasi sinyal status (optional)
        self.status_pub = rospy.Publisher("/mapping_autoresume/status", Bool, queue_size=1)

        rospy.loginfo("mapping_autoresume aktif (freeze=%.1fs, resume=%.1fs)",
                      self.freeze_secs, self.resume_secs)

    def odom_cb(self, msg):
        """Pantau perubahan pose; jika terlalu lama tidak berubah, anggap freeze."""
        now = time.time()
        pos = msg.pose.pose.position

        if self.last_pose is None:
            self.last_pose = pos
            return

        dist = math.sqrt(
            (pos.x - self.last_pose.x)**2 +
            (pos.y - self.last_pose.y)**2
        )

        if dist > 0.015:  # dianggap bergerak
            self.last_active = now
            if self.freeze_reported:
                rospy.loginfo("Mapping resumed — sensor kembali aktif.")
                self.status_pub.publish(True)
                self.freeze_reported = False

        idle = now - self.last_active

        # Jika diam terlalu lama → tampilkan pesan peringatan
        if idle > self.freeze_secs and not self.freeze_reported:
            rospy.logwarn("Mapping tampak berhenti (diam %.1fs). "
                          "Silakan sejajarkan ulang sensor.", idle)
            self.status_pub.publish(False)
            self.freeze_reported = True

        # Jika freeze sudah lama → coba lanjut otomatis
        if self.freeze_reported and idle > (self.freeze_secs + self.resume_secs):
            rospy.loginfo("Menunggu sensor stabil... jika sudah sejajar, mapping akan lanjut.")
            self.freeze_reported = False
            self.last_active = now  # reset timer agar lanjut normal

        self.last_pose = pos


if __name__ == "__main__":
    try:
        MappingAutoResume()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

