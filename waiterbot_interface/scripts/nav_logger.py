#!/usr/bin/env python3
import rospy
import tf
import csv
import os
import math
import time
from geometry_msgs.msg import PoseStamped
from datetime import datetime

class NavigationLogger:
    def __init__(self):
        rospy.init_node('skripsi_data_logger', anonymous=True)
        self.tf_listener = tf.TransformListener()
        rospy.Subscriber('/move_base_simple/goal', PoseStamped, self.goal_callback)
        
        self.current_goal = None
        self.goal_received_flag = False
        
        self.save_dir = os.path.expanduser("~/data_skripsi")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        
        self.main_loop()

    def goal_callback(self, msg):
        self.current_goal = (msg.pose.position.x, msg.pose.position.y)
        self.goal_received_flag = True

    def get_robot_pose(self):
        try:
            (trans, rot) = self.tf_listener.lookupTransform('/map', '/base_link', rospy.Time(0))
            return trans[0], trans[1]
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            return None, None

    def main_loop(self):
        while not rospy.is_shutdown():
            os.system('clear')
            print("="*50)
            print("   LOGGER 1: DATA POSISI & AKURASI")
            print(f"   Folder: {self.save_dir}")
            print("="*50)

            raw_name = input("\n[1/3] Masukkan Nama Percobaan (misal: uji_1) : ").strip()
            if not raw_name:
                raw_name = f"data_{datetime.now().strftime('%H%M%S')}"
            
            # --- PERUBAHAN: Tambah Suffix _POSISI ---
            filename = f"{raw_name}_POSISI.csv"
            # ----------------------------------------
            
            full_path = os.path.join(self.save_dir, filename)

            print(f"\n[2/3] Output diset ke: {filename}")
            print("      MENUNGGU NAVIGASI DARI GUI...")
            
            self.goal_received_flag = False 
            while not self.goal_received_flag and not rospy.is_shutdown():
                time.sleep(0.1)

            if rospy.is_shutdown(): break

            print(f"\n[3/3] MULAI MEREKAM POSISI...")
            self.record_session(full_path)
            
            print("\n" + "-"*50)
            print("   SELESAI.")
            print("-"*50)
            input("   Tekan [Enter] untuk lanjut...")

    def record_session(self, filepath):
        try:
            with open(filepath, mode='w') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["Waktu_Detik", "Posisi_X", "Posisi_Y", "Target_X", "Target_Y", "Error_Jarak_Meter"])
                
                start_time = time.time()
                rate = rospy.Rate(2) 

                while not rospy.is_shutdown():
                    x, y = self.get_robot_pose()
                    if x is not None and y is not None:
                        goal_x, goal_y = self.current_goal
                        error_distance = math.hypot(goal_x - x, goal_y - y)
                        elapsed_time = time.time() - start_time
                        
                        csv_writer.writerow([
                            f"{elapsed_time:.2f}", f"{x:.4f}", f"{y:.4f}",
                            f"{goal_x:.4f}", f"{goal_y:.4f}", f"{error_distance:.4f}"
                        ])
                        csv_file.flush()
                        print(f"\r      [POSISI] Waktu: {elapsed_time:.1f}s | Error: {error_distance:.3f}m ", end="")

                        if error_distance < 0.20:
                            print(f"\n      [STOP] Sampai di Target.")
                            break
                    rate.sleep()
        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == '__main__':
    try:
        NavigationLogger()
    except rospy.ROSInterruptException:
        pass
