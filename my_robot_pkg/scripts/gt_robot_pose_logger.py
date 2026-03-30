#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Pose
from tf.transformations import euler_from_quaternion
import matplotlib.pyplot as plt
import csv

# Inisialisasi variabel untuk menyimpan data
positions_x = []
positions_y = []
orientations_roll = []
orientations_pitch = []
orientations_yaw = []
timestamps = []

# Fungsi callback untuk merekam data
def log_data_callback(data):
    position_x = data.position.x
    position_y = data.position.y
    positions_x.append(position_x)
    positions_y.append(position_y)

    orientation_quaternion = [data.orientation.x, data.orientation.y, data.orientation.z, data.orientation.w]
    roll, pitch, yaw = euler_from_quaternion(orientation_quaternion)
    orientations_roll.append(roll)
    orientations_pitch.append(pitch)
    orientations_yaw.append(yaw)
    
    timestamp = rospy.Time.now()
    timestamps.append(timestamp.to_sec())  # Konversi timestamp ke detik

# Fungsi untuk menyimpan data ke dalam file CSV
def save_to_csv():
    csv_path = '/home/iascr/data/log.csv'
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Position X', 'Position Y', 'Roll', 'Pitch', 'Yaw'])
        for i in range(len(timestamps)):
            writer.writerow([timestamps[i], positions_x[i], positions_y[i], orientations_roll[i], orientations_pitch[i], orientations_yaw[i]])
    print("Data disimpan dalam log.csv")

# Fungsi untuk menyimpan visualisasi sebagai gambar
def save_visualization():
    png_path = '/home/iascr/data/trajectory.png'
    plt.figure()
    plt.plot(positions_x, positions_y, label='Trajectory')
    plt.xlabel('Position X')
    plt.ylabel('Position Y')
    plt.title('Robot Trajectory')
    plt.legend()
    plt.grid()
    plt.savefig(png_path)
    print("Visualisasi disimpan sebagai trajectory.png")

def main():
    rospy.init_node('data_logger', anonymous=True)

    # Pengaturan subscriber ke topik robot_pose
    rospy.Subscriber('/robot_pose', Pose, log_data_callback)

    # Menunggu beberapa saat hingga cukup data terkumpul
    rospy.sleep(5.0)

    # Simpan data dan visualisasi saat node dihentikan
    rospy.on_shutdown(save_to_csv)
    rospy.on_shutdown(save_visualization)

    rospy.spin()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
