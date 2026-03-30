#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
import serial

class ROBOTHardwareInterface:
    def __init__(self):
        self.joint_names = ['left_wheel_joint', 'right_wheel_joint']
        self.joint_positions = [0.0, 0.0]
        self.joint_velocities = [0.0, 0.0]
        self.joint_efforts = [0.0, 0.0]
        self.joint_velocity_commands = [0.0, 0.0]
        self.left_motor_pos = 0
        self.right_motor_pos = 0
        self.left_prev_cmd = 0
        self.right_prev_cmd = 0
        self.serial = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.1)

    def init(self):
        rospy.init_node('robot_hardware_interface')

        self.joint_state_pub = rospy.Publisher('joint_states', JointState, queue_size=10)
        self.left_velocity_sub = rospy.Subscriber('left_wheel_joint_velocity_controller/command', Float64, self.left_velocity_callback)
        self.right_velocity_sub = rospy.Subscriber('right_wheel_joint_velocity_controller/command', Float64, self.right_velocity_callback)

    def left_velocity_callback(self, msg):
        self.joint_velocity_commands[0] = msg.data

    def right_velocity_callback(self, msg):
        self.joint_velocity_commands[1] = msg.data

    def read(self):
        data = self.serial.readline().decode('utf-8').strip()
        if data:
            left_encoder_value, right_encoder_value = map(int, data.split(','))
            self.joint_position[0] = left_encoder_value
            self.joint_position[1] = right_encoder_value
        else:
            print("Invalid data received from Arduino")


    def write(self):
        left_motor_velocity = int(self.joint_velocity_commands[0])
        right_motor_velocity = int(self.joint_velocity_commands[1])

        if self.left_prev_cmd != left_motor_velocity or self.right_prev_cmd != right_motor_velocity:
            command = f'{left_motor_velocity},{right_motor_velocity}\n'
            self.serial.write(command.encode())

            self.left_prev_cmd = left_motor_velocity
            self.right_prev_cmd = right_motor_velocity

    def update(self):
        joint_state = JointState()
        joint_state.header.stamp = rospy.Time.now()
        joint_state.name = self.joint_names
        joint_state.position = self.joint_positions
        joint_state.velocity = self.joint_velocities
        joint_state.effort = self.joint_efforts

        self.joint_state_pub.publish(joint_state)

        self.read()
        self.write()

    def run(self):
        rate = rospy.Rate(10)  # 10 Hz

        while not rospy.is_shutdown():
            self.update()
            rate.sleep()

if __name__ == '__main__':
    robot_hw = ROBOTHardwareInterface()
    robot_hw.init()
    robot_hw.run()
