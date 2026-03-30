#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import rospkg
import glob
import yaml
import threading
import math

# Import Pustaka ROS
try:
    import rospy
    import tf
    from tf.transformations import euler_from_quaternion
    # Import Pesan Penting untuk Navigasi
    from geometry_msgs.msg import Twist, PoseStamped 
except ImportError:
    print("PERINGATAN: Pustaka ROS tidak lengkap. Fitur real-time non-aktif.")
    rospy = None
    tf = None

class RosPoseListener(threading.Thread):
    def __init__(self):
        super(RosPoseListener, self).__init__()
        self.daemon = True
        self.listener = None
        self.robot_pose = None
        self._stop_event = threading.Event()
        self._run_event = threading.Event()

    def run(self):
        if not rospy or not tf: return
        if not rospy.core.is_initialized():
            rospy.init_node('kivy_ros_manager', anonymous=True, disable_signals=True)
        
        self.listener = tf.TransformListener()
        rate = rospy.Rate(10.0)

        while not self._stop_event.is_set():
            self._run_event.wait()
            if self._stop_event.is_set(): break
            try:
                (trans, rot) = self.listener.lookupTransform('/map', '/base_link', rospy.Time(0))
                _, _, yaw = euler_from_quaternion(rot)
                self.robot_pose = {'x': trans[0], 'y': trans[1], 'yaw': yaw}
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                self.robot_pose = None
                continue
            finally:
                rate.sleep()

    def start_listening(self):
        self._run_event.set()

    def stop_listening(self):
        self._run_event.clear()
        self.robot_pose = None

    def stop_thread(self):
        self._stop_event.set()
        self._run_event.set()

    def get_pose(self):
        return self.robot_pose

class RosManager:
    def __init__(self, status_callback):
        self.roscore_process = None
        self.controller_process = None
        self.mapping_process = None
        self.navigation_process = None

        self.is_controller_running = False
        self.is_mapping_running = False
        self.is_navigation_running = False
        
        self.status_callback = status_callback
        self.rospack = rospkg.RosPack()
        
        self.current_map_name = None
        self.map_metadata = None
        self.pose_listener = None
        
        self.cmd_vel_pub = None 
        self.goal_pub = None # Publisher untuk Goal Navigasi
        
        self.start_roscore_if_needed()
        self._init_ros_node()
        print("INFO: RosManager siap.")

    def start_roscore_if_needed(self):
        try:
            subprocess.check_output(["pidof", "roscore"])
        except subprocess.CalledProcessError:
            print("INFO: roscore belum berjalan, memulai di latar belakang...")
            try:
                self.roscore_process = subprocess.Popen("roscore", preexec_fn=os.setsid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(4)
            except Exception as e:
                print(f"FATAL: Gagal memulai roscore: {e}")

    def _init_ros_node(self):
        if not rospy: return
        try:
            if not rospy.core.is_initialized():
                rospy.init_node('kivy_ros_manager', anonymous=True, disable_signals=True)
            
            # Publisher Kecepatan
            self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
            
            # Publisher Goal (Navigasi)
            self.goal_pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=1)
            
            self.pose_listener = RosPoseListener()
            self.pose_listener.start()
            print("INFO: Node ROS, Cmd_vel & Goal Publisher siap.")
        except Exception as e:
            print(f"FATAL: Gagal inisialisasi ROS: {e}")
            self.pose_listener = None
            self.cmd_vel_pub = None
            self.goal_pub = None

    # --- FUNGSI NAVIGASI LANGSUNG (NATIVE ROS) ---
    def send_navigation_goal(self, x, y):
        """Mengirim koordinat tujuan langsung ke topic ROS /move_base_simple/goal"""
        if not self.goal_pub:
            print("ERROR: Publisher Goal belum siap (ROS Error)!")
            return False
            
        try:
            goal = PoseStamped()
            goal.header.frame_id = "map"
            goal.header.stamp = rospy.Time.now()
            
            # Set Posisi (Meter)
            goal.pose.position.x = float(x)
            goal.pose.position.y = float(y)
            goal.pose.position.z = 0.0
            
            # Set Orientasi (W=1.0 artinya netral/lurus)
            goal.pose.orientation.x = 0.0
            goal.pose.orientation.y = 0.0
            goal.pose.orientation.z = 0.0
            goal.pose.orientation.w = 1.0 
            
            self.goal_pub.publish(goal)
            print(f"SUKSES: Goal dikirim ke ROS -> X:{x}, Y:{y}")
            return True
        except Exception as e:
            print(f"ERROR saat kirim goal: {e}")
            return False

    def _stop_process_group(self, process, name):
        # PERBAIKAN INDENTATION DI SINI
        if process and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        return None
    
    def _send_stop_command(self):
        print("INFO: Mengirim perintah STOP.")
        if rospy and self.cmd_vel_pub:
            stop_msg = Twist()
            for _ in range(10):
                self.cmd_vel_pub.publish(stop_msg)
                time.sleep(0.01) 
        else:
            stop_cmd = 'rostopic pub -1 /cmd_vel geometry_msgs/Twist "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}"'
            subprocess.run(stop_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cancel_cmd = 'rostopic pub -1 /move_base/cancel actionlib_msgs/GoalID -- {}'
        subprocess.Popen(cancel_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- CONTROLLER ---
    def start_controller(self, launch_file="controller.launch"):
        if not self.is_controller_running:
            command = f"roslaunch my_robot_pkg {launch_file}"
            self.controller_process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_controller_running = True
            return "Status: AKTIF"
        return "Status: Sudah Aktif"

    def stop_controller(self):
        if self.is_controller_running:
            self.controller_process = self._stop_process_group(self.controller_process, "Controller")
            self.is_controller_running = False
            self._send_stop_command()
        return "Status: DIMATIKAN"

    # --- NAVIGATION ---
    def start_navigation(self, map_name):
        if not self.is_navigation_running:
            try:
                self.current_map_name = map_name
                pkg_path = self.rospack.get_path('autonomus_mobile_robot')
                map_file_path = os.path.join(pkg_path, 'maps', f"{map_name}.yaml")
                
                command = f"roslaunch autonomus_mobile_robot gui_navigation.launch map_file:={map_file_path}"
                self.navigation_process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
                self.is_navigation_running = True
                
                self.start_controller("controller.launch")
                
                if self.pose_listener:
                    time.sleep(5) 
                    self.pose_listener.start_listening()

                return f"Navigasi dengan peta\n'{map_name}' AKTIF"
            except Exception as e:
                print(f"FATAL: Gagal menjalankan navigasi: {e}")
                return f"GAGAL memulai navigasi!\nError: {e}"
        return "Status: Navigasi Sudah Aktif"
        
    def stop_navigation(self):
        if self.is_navigation_running:
            if self.pose_listener:
                self.pose_listener.stop_listening()
           
            self.stop_controller() 
            self.navigation_process = self._stop_process_group(self.navigation_process, "Navigation")
            self.is_navigation_running = False
            self._send_stop_command()
           
            self.current_map_name = None
            self.map_metadata = None
        return "Status: DIMATIKAN"

    # --- MAPPING ---
    def start_mapping(self, map_name):
        if not self.is_mapping_running:
            self.current_map_name = map_name
            command = "roslaunch autonomus_mobile_robot mapping.launch"
            try:
                self.mapping_process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
                self.is_mapping_running = True
                self.start_controller("mapping_controller.launch")
                return "Mode Pemetaan AKTIF.\nSilakan gerakkan robot."
            except Exception as e:
                print(f"FATAL: Gagal menjalankan mapping: {e}"); return f"GAGAL memulai mapping!\nError: {e}"
        return "Status: Mapping Sudah Aktif"

    def stop_mapping(self):
        if self.is_mapping_running:
            self._save_map_on_exit()
            self.stop_controller()
            self.mapping_process = self._stop_process_group(self.mapping_process, "Mapping")
            self.is_mapping_running = False
            self._send_stop_command()
            self.current_map_name = None
        return "Status: DIMATIKAN"
        
    def cancel_mapping(self):
        if self.is_mapping_running:
            self.stop_controller()
            self.mapping_process = self._stop_process_group(self.mapping_process, "Mapping")
            self.is_mapping_running = False
            self._send_stop_command()
            self.current_map_name = None
        return "Status: DIBATALKAN"

    # --- UTILS ---
    def _save_map_on_exit(self):
        if not self.current_map_name: return
        try:
            pkg_path = self.rospack.get_path('autonomus_mobile_robot')
            map_save_path = os.path.join(pkg_path, 'maps', self.current_map_name)
            command = f"rosrun map_server map_saver -f {map_save_path}"
            subprocess.run(command, shell=True, check=True, timeout=15, capture_output=True, text=True)
            print("INFO: Peta berhasil disimpan!")
        except Exception as e:
            print(f"ERROR: Gagal menyimpan peta saat keluar: {e}")

    def shutdown(self):
        print("INFO: Shutdown dipanggil...")
        if self.pose_listener:
            self.pose_listener.stop_thread()
            self.pose_listener.join()
        
        self.stop_mapping()
        self.stop_navigation()
        self.stop_controller() 
        self._send_stop_command()
        
        if self.roscore_process:
            self._stop_process_group(self.roscore_process, "roscore")
    
    def get_robot_pose(self):
        if self.pose_listener:
            return self.pose_listener.get_pose()
        return None

    def get_available_maps(self):
        try:
            pkg_path = self.rospack.get_path('autonomus_mobile_robot')
            maps_dir = os.path.join(pkg_path, 'maps')
            map_files = glob.glob(os.path.join(maps_dir, '*.yaml'))
            return [os.path.splitext(os.path.basename(f))[0] for f in map_files]
        except Exception:
            return []

    def get_map_image_path(self, map_name):
        try:
            pkg_path = self.rospack.get_path('autonomus_mobile_robot')
            TARGET_EXPERIMENT_MAP ='test1'
            if map_name == TARGET_EXPERIMENT_MAP:
                pgm_point_path = os.path.join(pkg_path, 'maps', f"{map_name}edited.pgm")
                if os.path.exists(pgm_point_path):
                   print (f"INFO: Memuat peta visualisasi pgm untuk {map_name}")
                   return pgm_point_path
    
            path = os.path.join(pkg_path, 'maps', f"{map_name}.pgm")
            return path if os.path.exists(path) else None
        except Exception as e: 
            print (f"Error getting map path: {e}")
            return None

    def load_map_metadata(self, map_name):
        try:
            pkg_path = self.rospack.get_path('autonomus_mobile_robot')
            with open(os.path.join(pkg_path, 'maps', f"{map_name}.yaml"), 'r') as f:
                self.map_metadata = yaml.safe_load(f)
        except Exception:
            self.map_metadata = None
