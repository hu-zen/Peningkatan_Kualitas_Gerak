#!/usr/bin/env python3

import rospy
import tf
import math
from tf.transformations import quaternion_from_euler
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Vector3
from sensor_msgs.msg import JointState
from std_msgs.msg import Int32

class OdometryPublisher:
    def __init__(self):
        rospy.init_node('odometry_publisher')

        self.odom_pub = rospy.Publisher('odom', Odometry, queue_size=50)
        self.odom_broadcaster = tf.TransformBroadcaster()
        self.joint_state_pub = rospy.Publisher('joint_states', JointState, queue_size=50)

        self.x = 0.0
        self.y = 0.0
        self.th = 0.0

        self.vx = 0.0
        self.vy = 0.0
        self.vth = 0.0

        self.current_time = rospy.Time.now()
        self.last_time = rospy.Time.now()

        # Joint states
        self.right_ticks = 0
        self.left_ticks = 0
        self.ticks_per_revolution = 36
        self.wheel_diameter = 0.15
        self.wheel_separation = 0.41

        rospy.Subscriber('right_ticks', Int32, self.right_ticks_callback)
        rospy.Subscriber('left_ticks', Int32, self.left_ticks_callback)

        self.rate = rospy.Rate(1.0)

        while not rospy.is_shutdown():
            self.current_time = rospy.Time.now()

            # Compute odometry in a typical way given the velocities of the robot
            dt = (self.current_time - self.last_time).to_sec()
            delta_x = (self.vx * math.cos(self.th) - self.vy * math.sin(self.th)) * dt
            delta_y = (self.vx * math.sin(self.th) + self.vy * math.cos(self.th)) * dt
            delta_th = self.vth * dt

            self.x += delta_x
            self.y += delta_y
            self.th += delta_th

            # Publish transform over tf
            self.odom_broadcaster.sendTransform(
                (self.x, self.y, 0),
                quaternion_from_euler(0, 0, self.th),
                self.current_time,
                "base_link",
                "odom"
            )

            # Publish odometry message over ROS
            self.publish_odometry()

            # Publish joint state
            self.publish_joint_state()

            self.last_time = self.current_time
            self.rate.sleep()

    def right_ticks_callback(self, data):
        self.right_ticks = data.data
        self.update_velocity()

    def left_ticks_callback(self, data):
        self.left_ticks = data.data
        self.update_velocity()

    def update_velocity(self):
        # Calculate linear and angular velocities based on wheel ticks
        linear_vel = ((2 * math.pi * self.wheel_diameter) * (self.right_ticks + self.left_ticks)) / (2 * self.ticks_per_revolution)
        angular_vel = (linear_vel * self.wheel_separation) / self.wheel_diameter

        # Check if the robot is moving or stopped
        if linear_vel == 0.0 and angular_vel == 0.0:
            self.vx = 0.0
            self.vy = 0.0
            self.vth = 0.0
        else:
            self.vx = linear_vel
            self.vy = 0.0
            self.vth = angular_vel

    def publish_odometry(self):
        odom = Odometry()
        odom.header.stamp = self.current_time
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        # Set the position
        odom.pose.pose.position = Point(self.x, self.y, 0.0)
        odom.pose.pose.orientation = Quaternion(*quaternion_from_euler(0, 0, self.th))

        # Set the velocity
        odom.twist.twist.linear = Vector3(self.vx, self.vy, 0.0)
        odom.twist.twist.angular = Vector3(0.0, 0.0, self.vth)

        # Publish the message
        self.odom_pub.publish(odom)

    def publish_joint_state(self):
        joint_state = JointState()
        joint_state.header.stamp = self.current_time
        joint_state.name = ["right_wheel_joint", "left_wheel_joint"]
        
        # Calculate wheel displacement based on ticks and wheel parameters
        right_wheel_displacement = (2 * math.pi * self.right_ticks) / self.ticks_per_revolution
        left_wheel_displacement = (2 * math.pi * self.left_ticks) / self.ticks_per_revolution
        
        # Calculate joint positions based on wheel displacement and wheel separation
        right_joint_position = right_wheel_displacement / self.wheel_diameter
        left_joint_position = left_wheel_displacement / self.wheel_diameter

        joint_state.position = [right_joint_position, left_joint_position]

        # Publish the message
        self.joint_state_pub.publish(joint_state)

if __name__ == '__main__':
    try:
        OdometryPublisher()
    except rospy.ROSInterruptException:
        pass
