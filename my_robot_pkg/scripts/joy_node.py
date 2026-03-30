import rospy
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

def joy_callback(data):
    speed = data.axes[1] * 255 # sumbu y joystick digunakan untuk mengontrol kecepatan
    direction = data.axes[0] * 2.0 # sumbu x joystick digunakan untuk mengontrol arah

    cmd_vel_msg = Twist()
    cmd_vel_msg.linear.x = speed
    cmd_vel_msg.angular.z = direction

    pub.publish(cmd_vel_msg)

def main():
    rospy.init_node('joystick_controller')

    global pub
    pub = rospy.Publisher('cmd_vel', Twist, queue_size=10)

    rospy.Subscriber('joy', Joy, joy_callback)

    rospy.spin()

if __name__ == '__main__':
    main()
