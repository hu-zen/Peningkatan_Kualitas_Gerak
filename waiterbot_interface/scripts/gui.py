#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemanddock')
if Config.has_section('input'):
    for key, value in Config.items('input'):
        Config.remove_option('input', key)
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import mainthread, Clock
from functools import partial
from kivy.uix.image import Image
from kivy.uix.behaviors import TouchRippleBehavior, ButtonBehavior
from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.widget import Widget 
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Line

import yaml
import math
import os
import subprocess
import threading
from manager import RosManager

class NavSelectionScreen(Screen):
    def on_enter(self):
        self.show_main_menu()

    def show_main_menu(self):
        grid = self.ids.nav_map_grid
        grid.clear_widgets()
        app = App.get_running_app()

        if 'scroll_container' in self.ids:
            self.ids.scroll_container.width = 0
            self.ids.scroll_container.opacity = 0
        if 'btn_scroll_up' in self.ids: self.ids.btn_scroll_up.disabled = True
        if 'btn_scroll_down' in self.ids: self.ids.btn_scroll_down.disabled = True

        BTN_WIDTH = '1300dp' 
        BTN_HEIGHT = '120dp'
        FONT_SIZE = '40sp'


        def create_menu_btn(text, color, action, align_mode, padding_val):
            btn = Button(
                text=text,
                size_hint=(None, None),
                width=BTN_WIDTH,
                height=BTN_HEIGHT,
                pos_hint={'center_x': 0.5},
                font_size=FONT_SIZE,
                background_color=color,
                
                # Pengaturan Teks
                halign=align_mode,
                valign='middle',
                padding_x=padding_val 
            )
            
            def update_text_size(instance, value):
                instance.text_size = (instance.width, None)
            
            btn.bind(size=update_text_size)
            btn.text_size = (530, None) 

            btn.bind(on_press=action)
            return btn

        PADDING_POINT = 1300

        # Point A
        grid.add_widget(create_menu_btn(
            "    POINT A | JAPAN CORNER", (0, 0.4, 1, 1), 
            partial(app.start_preset_navigation, 'A'),
            'left', PADDING_POINT
        ))

        # Point B
        grid.add_widget(create_menu_btn(
            "    POINT B | JURNAL TEPAT", (0, 0.4, 1, 1), 
            partial(app.start_preset_navigation, 'B'),
            'left', PADDING_POINT
        ))

        # Point C
        grid.add_widget(create_menu_btn(
            "    POINT C | WAREHOUSE", (0, 0.4, 1, 1), 
            partial(app.start_preset_navigation, 'C'),
            'left', PADDING_POINT
        ))

        
        # Region Map
        grid.add_widget(create_menu_btn(
            "REGION MAP", (0, 0.8, 0, 1), 
            partial(app.start_navigation_with_map, 'test1','None'),
            'center', 0
        ))

        # Others Map
        others_btn = create_menu_btn(
            "OTHERS MAP", (0.8, 0.5, 0, 1), 
            self.go_to_others_map_with_audio,
            'center', 0
        )
        grid.add_widget(others_btn)

    def go_to_others_map_with_audio(self, instance=None):
        app = App.get_running_app()
        app.play_audio('others_map.mp3')
        Clock.schedule_once(lambda dt: self.show_others_map(), 0.2)

    def show_others_map(self, instance=None):
        grid = self.ids.nav_map_grid
        grid.clear_widgets()
        app = App.get_running_app()
        
        if 'scroll_container' in self.ids:
            self.ids.scroll_container.width = 100 
            self.ids.scroll_container.opacity = 1
        if 'btn_scroll_up' in self.ids: self.ids.btn_scroll_up.disabled = False
        if 'btn_scroll_down' in self.ids: self.ids.btn_scroll_down.disabled = False
        


        maps_folder = os.path.expanduser("~/catkin_ws/src/autonomus_mobile_robot/maps")
        map_names = []

        if os.path.exists(maps_folder):
            try:
                files = os.listdir(maps_folder)
                map_names = [f.replace('.yaml', '') for f in files if f.endswith('.yaml')]
                map_names.sort()
            except Exception as e:
                print(f"Error reading maps: {e}")
        else:
            print(f"WARNING: Folder {maps_folder} tidak ditemukan.")

        if not map_names:
            grid.add_widget(Label(text="Tidak ada peta ditemukan.", color=(0,0,0,1)))
            return
            
        for name in map_names:
            btn = Button(
                text=name, 
                size_hint_y=None, height='120dp', 
                font_size='40sp'
            )
            btn.bind(on_press=partial(app.start_navigation_with_map, name))
            grid.add_widget(btn)

class ImageButton(ButtonBehavior, Image):
    pass

class MapImage(TouchRippleBehavior, Image):
    marker = ObjectProperty(None, allownone=True)
    locked = BooleanProperty(False)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.locked:
                return False 

            if self.marker and self.marker.parent:
                self.remove_widget(self.marker)

            new_marker = Label(text='X', font_size='30sp', color=(1, 0, 0, 1), bold=True)
            new_marker.center = touch.pos
            self.add_widget(new_marker)
            self.marker = new_marker
            
            self.save_map_coords_to_marker(touch, new_marker)
            App.get_running_app().calculate_ros_goal(touch, self)
            return super().on_touch_down(touch)
        return False

    def save_map_coords_to_marker(self, touch, marker_widget):
        app = App.get_running_app()
        if not app.manager.map_metadata: return

        meta = app.manager.map_metadata
        resolution = meta['resolution']
        origin_x = meta['origin'][0]
        origin_y = meta['origin'][1]
        
        norm_w, norm_h = self.texture.size
        widget_w, widget_h = self.size
        if norm_w == 0 or norm_h == 0: return

        img_ratio = norm_w / norm_h
        widget_ratio = widget_w / widget_h
        
        if widget_ratio > img_ratio:
            scale = widget_h / norm_h
            offset_x = (widget_w - norm_w * scale) / 2.0
            offset_y = 0.0
        else:
            scale = widget_w / norm_w
            offset_x = 0.0
            offset_y = (widget_h - norm_h * scale) / 2.0
            
        touch_on_image_x = touch.pos[0] - self.x - offset_x
        touch_on_image_y = touch.pos[1] - self.y - offset_y
        
        pixel_x = touch_on_image_x / scale
        pixel_y = touch_on_image_y / scale
        
        map_x = (pixel_x * resolution) + origin_x
        map_y = (pixel_y * resolution) + origin_y
        
        marker_widget.map_coords = (map_x, map_y)

class RobotMarker(Image):
    angle = NumericProperty(0)

class HomeScreen(Screen):
    pass

class NavigationScreen(Screen):
    selected_goal_coords = None
    robot_marker = ObjectProperty(None, allownone=True)
    pending_preset_target = None
    use_image_marker = BooleanProperty(False) 
    path_line = None

    def on_enter(self):
        app = App.get_running_app()
        self.load_map_image(app.manager.current_map_name)
        
        map_viewer = self.ids.map_viewer
        if map_viewer.marker and map_viewer.marker.parent:
            map_viewer.remove_widget(map_viewer.marker)
            map_viewer.marker = None

        scatter = self.ids.scatter_map
        scatter.scale = 1.0
        scatter.pos = self.ids.map_container.pos 
        if not self.path_line:
            with scatter.canvas:
                Color(0, 1, 1, 1) # Warna Cyan (R, G, B, A)
                self.path_line = Line(points=[], width=2)
                
                
        if not self.robot_marker:
            source = 'robot_arrow.png' if os.path.exists('robot_arrow.png') else 'atlas://data/images/defaulttheme/checkbox_on'
            self.robot_marker = RobotMarker(source=source, size_hint=(None, None), size=(30, 30), allow_stretch=True, opacity=0)
            self.ids.scatter_map.add_widget(self.robot_marker)

        if self.pending_preset_target:
            Clock.schedule_once(lambda dt: self.setup_preset_mode(self.pending_preset_target), 0)
        else:
            self.setup_manual_mode()
        
        map_viewer.bind(size=self.update_marker_position, pos=self.update_marker_position)
        app.set_dpad_visibility(False)
        self.update_event = Clock.schedule_interval(self.update_robot_display, 0.1)

    def clear_path(self):
        if self.path_line:
            self.path_line.points = []

    def setup_manual_mode(self):
        self.ids.map_viewer.locked = False
        self.use_image_marker = False
        self.selected_goal_coords = None
        self.ids.navigate_button.disabled = True
        self.ids.navigation_status_label.text = "Status: Pilih titik di peta"

    def setup_preset_mode(self, target_data):
        x, y, name = target_data
        self.ids.map_viewer.locked = True
        self.use_image_marker = True
        
        self.selected_goal_coords = (x, y)
        self.ids.navigate_button.disabled = False
        self.ids.navigation_status_label.text = f"Tujuan: Point {name}\nTekan START untuk jalan."
        self.show_goal_marker(x, y)

    def on_leave(self):
        if hasattr(self, 'update_event'):
            self.update_event.cancel()
        if self.robot_marker:
            self.robot_marker.opacity = 0
        self.ids.map_viewer.unbind(size=self.update_marker_position, pos=self.update_marker_position)
        self.pending_preset_target = None
        self.clear_path()

    def update_marker_position(self, *args):
        map_viewer = self.ids.map_viewer
        if map_viewer.marker and hasattr(map_viewer.marker, 'map_coords'):
            map_x, map_y = map_viewer.marker.map_coords
            screen_pos = self.calculate_screen_pos(map_x, map_y)
            if screen_pos:
                map_viewer.marker.center = screen_pos

    def calculate_screen_pos(self, map_x, map_y):
        app = App.get_running_app()
        map_viewer = self.ids.map_viewer
        if not app.manager.map_metadata or not map_viewer.texture: return None

        meta = app.manager.map_metadata
        resolution = meta['resolution']
        origin_x = meta['origin'][0]
        origin_y = meta['origin'][1]
        
        pixel_x = (map_x - origin_x) / resolution
        pixel_y = (map_y - origin_y) / resolution
        
        norm_w, norm_h = map_viewer.texture.size
        widget_w, widget_h = map_viewer.size
        if norm_w == 0 or norm_h == 0: return None
        
        img_ratio = norm_w / norm_h
        widget_ratio = widget_w / widget_h
        
        if widget_ratio > img_ratio:
            scale = widget_h / norm_h
            offset_x = (widget_w - norm_w * scale) / 2.0
            offset_y = 0.0
        else:
            scale = widget_w / norm_w
            offset_x = 0.0
            offset_y = (widget_h - norm_h * scale) / 2.0
            
        screen_x = (pixel_x * scale) + offset_x + map_viewer.x
        screen_y = (pixel_y * scale) + offset_y + map_viewer.y
        return (screen_x, screen_y)

    def show_goal_marker(self, map_x, map_y):
        app = App.get_running_app()
        map_viewer = self.ids.map_viewer
        
        if (not map_viewer.texture or map_viewer.texture.size[0] <= 1 or not app.manager.map_metadata):
            Clock.schedule_once(lambda dt: self.show_goal_marker(map_x, map_y), 0.5)
            return

        if map_viewer.marker and map_viewer.marker.parent:
            map_viewer.remove_widget(map_viewer.marker)

        screen_pos = self.calculate_screen_pos(map_x, map_y)
        if not screen_pos: return

        if self.use_image_marker:
            source = 'goals.png' if os.path.exists('goals.png') else 'atlas://data/images/defaulttheme/filechooser_folder'
            new_marker = Image(source=source, size_hint=(None, None), size=('35dp', '35dp'), allow_stretch=True)
        else:
            new_marker = Label(text='X', font_size='30sp', color=(1, 0, 0, 1), bold=True)

        new_marker.center = screen_pos
        new_marker.map_coords = (map_x, map_y)
        map_viewer.add_widget(new_marker)
        map_viewer.marker = new_marker

    def load_map_image(self, map_name):
        if map_name:
            app = App.get_running_app()
            map_image_path = app.manager.get_map_image_path(map_name)
            if map_image_path:
                self.ids.map_viewer.source = map_image_path
                app.manager.load_map_metadata(map_name)
                self.ids.map_viewer.reload()

    @mainthread
    def update_robot_display(self, dt):
        app = App.get_running_app()
        pose = app.manager.get_robot_pose()
        if pose is None: return
        screen_pos = self.calculate_screen_pos(pose['x'], pose['y'])
        if screen_pos:
            self.robot_marker.opacity = 1
            self.robot_marker.center = screen_pos
            self.robot_marker.angle = math.degrees(pose['yaw'])
            if self.path_line:
                self.path_line.points += [screen_pos[0], screen_pos[1]]

class MainApp(App):
    PAN_STEP = 50 

    def build(self):
        self.manager = RosManager(status_callback=self.update_status_label)
        self.nav_goal_coords = None
        self.nav_status_event = None
        self.active_sound = None
        Window.fullscreen = 'auto'
        
        kv_design = """
<Screen>:
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
<Label>:
    color: 0, 0, 0, 1
<Button>:
    color: 1, 1, 1, 1
    background_color: 0.3, 0.3, 0.3, 1
    background_normal: '' 
<TextInput>:
    foreground_color: 0, 0, 0, 1 
    background_color: 0.9, 0.9, 0.9, 1 
<ImageButton>:
    background_color: 1, 1, 1, 0 
    background_normal: ''
    allow_stretch: True
    keep_ratio: True
    canvas.after:
        Color:
            rgba: 0, 0, 0, 0.3 if self.state == 'down' else 0
        Rectangle:
            pos: self.pos
            size: self.size
<MapControlButton@Button>:
    font_size: '30sp'
    size_hint: (1, 1)
    background_color: 0.2, 0.2, 0.2, 0.5 
<WindowToggleBtn@Button>:
    text: '[ ]'
    font_size: '20sp'
    bold: True
    size_hint: None, None
    size: '100dp', '100dp'
    background_color: 0.8, 0, 0, 0.5 
    pos_hint: {'top': 1, 'right': 1}
    on_press: app.toggle_window_mode()
<RobotMarker>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: self.angle
            origin: self.center
    canvas.after:
        PopMatrix
<MapImage>:

<HomeScreen>:
    FloatLayout:
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Image:
            source: 'home.png'
            size_hint: None, None
            width: root.width * 0.58
            height: root.height * 0.58
            pos_hint: {"center_x": 0.5, "center_y": 0.65}
            allow_stretch: True
            keep_ratio: True
        ImageButton:
            source: 'start.png'
            size_hint: None, None
            width: root.width * 0.5
            height: root.height * 0.5
            pos_hint: {"center_x": 0.5, "center_y": 0.20}
            on_press: app.enter_main_menu() 

<NavSelectionScreen>:
    FloatLayout:
        BoxLayout:
            orientation: 'vertical'
            padding: 20
            spacing: 10
            Image:
                source: 'Choose_your_mission.png' 
                size_hint_y: 0.2
                allow_stretch: True
                keep_ratio: True
            BoxLayout:
                orientation: 'horizontal'
                spacing: 10
                ScrollView:
                    id: map_scroll
                    BoxLayout:
                        id: nav_map_grid
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: 20
                        padding: 10
                BoxLayout:
                    id: scroll_container
                    orientation: 'vertical'
                    size_hint_x: None
                    width: '90dp'
                    spacing: 10
                    ImageButton:
                        id: btn_scroll_up
                        source: 'scroll_up.png'
                        on_press: app.scroll_map_list_up()
                    ImageButton:
                        id: btn_scroll_down
                        source: 'scroll_down.png'
                        on_press: app.scroll_map_list_down()
            ImageButton:
                source: 'go_back.png'
                size_hint_y: None
                height: '150dp'
                size_hint_x: 0.8
                pos_hint: {'center_x': 0.5}
                on_press: root.manager.current = 'main_menu'
        WindowToggleBtn:
         
<NavigationScreen>:
    name: 'navigation'
    FloatLayout:
        BoxLayout:
            orientation: 'vertical'
            padding: 10
            spacing: 10
            FloatLayout:
                id: map_container
                size_hint: 1, 1
                Scatter:
                    id: scatter_map
                    size_hint: (1, 1)
                    do_rotation: False
                    do_scale: True
                    do_translation: False 
                    scale_min: 1.0
                    scale_max: 8.0
                    auto_bring_to_front: False
                    MapImage:
                        id: map_viewer
                        source: ''
                        allow_stretch: True
                        keep_ratio: True
                        size_hint: (None, None)
                        size: self.parent.size 
                BoxLayout:
                    orientation: 'vertical'
                    size_hint: (None, None)
                    size: ('140dp', '170dp') 
                    pos_hint: {'x': 0.02, 'y': 0.02} 
                    spacing: 20
                    MapControlButton:
                        text: "+"
                        on_press: app.zoom_in()
                    MapControlButton:
                        text: "-"
                        on_press: app.zoom_out()
                ImageButton:
                    id: dpad_up
                    source: 'scroll_up.png'
                    size_hint: (None, None)
                    size: ('100dp', '100dp') 
                    pos_hint: {'center_x': 0.5, 'top': 0.98} 
                    on_press: app.pan_map_up()
                ImageButton:
                    id: dpad_down
                    source: 'scroll_down.png'
                    size_hint: (None, None)
                    size: ('100dp', '100dp') 
                    pos_hint: {'center_x': 0.5, 'y': 0.12} 
                    on_press: app.pan_map_down()
                ImageButton:
                    id: dpad_left
                    source: 'scroll_left.png'
                    size_hint: (None, None)
                    size: ('100dp', '100dp') 
                    pos_hint: {'x': 0.02, 'center_y': 0.5} 
                    on_press: app.pan_map_left()
                ImageButton:
                    id: dpad_right
                    source: 'scroll_right.png'
                    size_hint: (None, None)
                    size: ('100dp', '100dp') 
                    pos_hint: {'right': 0.98, 'center_y': 0.5} 
                    on_press: app.pan_map_right()
            BoxLayout:
                size_hint_y: None
                height: '60dp'
                orientation: 'horizontal'
                spacing: 10
                Label:
                    id: navigation_status_label
                    text: 'Status: Pilih titik di peta'
                    font_size: '18sp'
                ImageButton:
                    id: navigate_button
                    source: 'start_navigation.png'
                    size_hint_y: None
                    height: '110dp'
                    size_hint_x: 1
                    pos_hint: {'center_x': 0.5}
                    disabled: True
                    on_press: app.confirm_navigation_goal()
                ImageButton:
                    source: 'go_back.png'
                    size_hint_y: None
                    height: '110dp'
                    size_hint_x: 1
                    pos_hint: {'center_x': 0.5}
                    on_press: app.exit_navigation_mode()
        WindowToggleBtn:

ScreenManager:
    id: sm
    HomeScreen:
        name: 'home' 
    Screen:
        name: 'main_menu'
        FloatLayout:
            BoxLayout:
                orientation: 'vertical'
                padding: [20, 20, 20, 20] 
                spacing: 20
                Image:
                    source:'waiter_bot_control_center.png'
                    size_hint_y: None
                    height:'275dp'
                    allow_stretch: True
                    keep_ratio: True
                ImageButton:
                    source: 'control_robot.png'
                    size_hint_y: None
                    height: '220dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    on_press: app.go_to_controller_mode()
                ImageButton:
                    source: 'make_a_map.png'
                    size_hint_y: None
                    height: '220dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    # FIX: Panggil fungsi python agar audio jalan
                    on_press: app.go_to_pre_mapping_mode() 
                ImageButton:
                    source: 'do_navigation.png'
                    size_hint_y: None
                    height: '220dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    # FIX: Panggil fungsi python agar audio jalan
                    on_press: app.go_to_nav_selection_mode()
            WindowToggleBtn:
    Screen:
        name: 'pre_mapping'
        FloatLayout:
            BoxLayout:
                orientation: 'vertical'
                padding: [40, 5, 40, 40]
                spacing: 15 
                Image:
                    source: 'name_your_map.png'
                    size_hint_y: None
                    height: '340dp'
                    allow_stretch: True
                    keep_ratio: True
                TextInput:
                    id: map_name_input
                    hint_text: 'Contoh: peta_lantai_1'
                    font_size: '50sp'
                    multiline: False
                    size_hint_y: None
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    height: '120dp'
                    padding_y: [30, 0]
                Widget:
                    size_hint_y: None
                    height: '40dp'
                ImageButton:
                    source: 'start_mapping.png'
                    size_hint_y: None
                    height: '220dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    on_press: app.go_to_mapping_mode(map_name_input.text)
                    disabled: not map_name_input.text
                Widget:
                    size_hint_y: None
                    height: '20dp'
                ImageButton:
                    source: 'go_back.png'
                    size_hint_y: None
                    height: '150dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    on_press: sm.current = 'main_menu'
            WindowToggleBtn:

    Screen:
        name: 'controller'
        FloatLayout:
            BoxLayout:
                orientation: 'vertical'
                padding: 40
                spacing: 85
                Image:
                    source:'use_controller_move_the_robot.png'
                    size_hint_y: None
                    height:'550dp'
                    allow_stretch: True
                    keep_ratio: True
                ImageButton:
                    source: 'go_back.png'
                    size_hint_y: None
                    height: '150dp'
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}
                    on_press: app.exit_controller_mode()
            WindowToggleBtn:

    Screen:
        name: 'mapping'
        FloatLayout:
            BoxLayout:
                orientation: 'vertical'
                padding: 40
                spacing: 20
                Image:
                    source: 'mapping_on_progress.png'
                    allow_stretch: True
                    keep_ratio: True
                    size_hint_y: 0.8
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: 20
                    size_hint_y: None
                    height: '120dp' 
                    ImageButton:
                        source: 'done_save_map.png' 
                        size_hint_y: None 
                        height: '150dp'
                        allow_stretch: True
                        keep_ratio: True
                        on_press: app.exit_mapping_mode()
                    ImageButton:
                        source: 'cancel.png' 
                        size_hint_y: None 
                        height: '150dp'    
                        allow_stretch: True
                        keep_ratio: True
                        on_press: app.cancel_mapping_mode()
            WindowToggleBtn:

    NavSelectionScreen:
        name: 'nav_selection'
    NavigationScreen:
        name: 'navigation'
"""
        return Builder.load_string(kv_design)

    def toggle_window_mode(self):
        if Window.fullscreen == 'auto':
            Window.fullscreen = False
            Window.maximize()
        else:
            Window.fullscreen = 'auto'

    def _get_map_scatter(self):
        try:
            return self.root.get_screen('navigation').ids.scatter_map
        except Exception:
            return None

    def set_dpad_visibility(self, is_visible):
        try:
            root_screen = self.root.get_screen('navigation')
            opacity_val = 1.0 if is_visible else 0.0
            disabled_val = not is_visible
            
            root_screen.ids.dpad_up.opacity = opacity_val
            root_screen.ids.dpad_down.opacity = opacity_val
            root_screen.ids.dpad_left.opacity = opacity_val
            root_screen.ids.dpad_right.opacity = opacity_val
            
            root_screen.ids.dpad_up.disabled = disabled_val
            root_screen.ids.dpad_down.disabled = disabled_val
            root_screen.ids.dpad_left.disabled = disabled_val
            root_screen.ids.dpad_right.disabled = disabled_val
        except Exception as e:
            print(f"Error setting D-Pad visibility: {e}")

    def zoom_in(self):
        scatter = self._get_map_scatter()
        if scatter:
            scatter.scale = min(scatter.scale * 1.2, scatter.scale_max)
            self.set_dpad_visibility(True)

    def zoom_out(self):
        scatter = self._get_map_scatter()
        if scatter:
            scatter.scale = max(scatter.scale / 1.2, scatter.scale_min)
            if scatter.scale <= 1.0:
                scatter.scale = 1.0 
                self.set_dpad_visibility(False)
                root_screen = self.root.get_screen('navigation')
                scatter.pos = root_screen.ids.map_container.pos
         
    def pan_map_up(self):
        scatter = self._get_map_scatter()
        if scatter: scatter.y -= self.PAN_STEP

    def pan_map_down(self):
        scatter = self._get_map_scatter()
        if scatter: scatter.y += self.PAN_STEP

    def pan_map_left(self):
        scatter = self._get_map_scatter()
        if scatter: scatter.x += self.PAN_STEP

    def pan_map_right(self):
        scatter = self._get_map_scatter()
        if scatter: scatter.x -= self.PAN_STEP

    def scroll_map_list_up(self):
        try:
            scroll = self.root.get_screen('nav_selection').ids.map_scroll
            new_scroll = min(1.0, scroll.scroll_y + 0.1)
            scroll.scroll_y = new_scroll
        except Exception: pass

    def scroll_map_list_down(self):
        try:
            scroll = self.root.get_screen('nav_selection').ids.map_scroll
            new_scroll = max(0.0, scroll.scroll_y - 0.1)
            scroll.scroll_y = new_scroll
        except Exception: pass
    
    def calculate_ros_goal(self, touch, image_widget):
        screen = self.root.get_screen('navigation')
        if not image_widget.texture or not self.manager.map_metadata: return
        meta = self.manager.map_metadata
        resolution = meta['resolution']
        origin_x = meta['origin'][0]
        origin_y = meta['origin'][1]
        
        norm_w, norm_h = image_widget.texture.size
        widget_w, widget_h = image_widget.size
        if norm_w == 0 or norm_h == 0: return

        img_ratio = norm_w / norm_h
        widget_ratio = widget_w / widget_h
        
        if widget_ratio > img_ratio:
            scale = widget_h / norm_h
            offset_x = (widget_w - norm_w * scale) / 2.0
            offset_y = 0.0
        else:
            scale = widget_w / norm_w
            offset_x = 0.0
            offset_y = (widget_h - norm_h * scale) / 2.0
        
        if scale == 0: return
        touch_on_image_x = touch.pos[0] - image_widget.x - offset_x
        touch_on_image_y = touch.pos[1] - image_widget.y - offset_y
        
        pixel_x = touch_on_image_x / scale
        pixel_y = touch_on_image_y / scale
        
        map_x = (pixel_x * resolution) + origin_x
        map_y = (pixel_y * resolution) + origin_y
        
        screen.selected_goal_coords = (map_x, map_y)
        screen.ids.navigate_button.disabled = False
        screen.ids.navigation_status_label.text = f"Goal: ({map_x:.2f}, {map_y:.2f})"

    def confirm_navigation_goal(self):
        screen = self.root.get_screen('navigation')
        screen.clear_path()
        self.play_audio('start_navigation.mp3')
        if screen.selected_goal_coords:
            map_x, map_y = screen.selected_goal_coords
            
            success = self.manager.send_navigation_goal(map_x, map_y)
            
            if success:
                print(f"INFO: Perintah GOAL ({map_x:.2f}, {map_y:.2f}) Terkirim!")
                screen.ids.navigation_status_label.text = "Status: Robot Bergerak..."
                self.nav_goal_coords = (map_x, map_y)
                if self.nav_status_event:
                    self.nav_status_event.cancel()
                self.nav_status_event = Clock.schedule_interval(self.check_navigation_status, 0.5)
                screen.ids.navigate_button.disabled = True
            else:
                screen.ids.navigation_status_label.text = "Status: Gagal Kirim Goal"
    
    def check_navigation_status(self, dt):
        if not self.nav_goal_coords: return False 
        current_pose = self.manager.get_robot_pose()
        if current_pose:
            dx = current_pose['x'] - self.nav_goal_coords[0]
            dy = current_pose['y'] - self.nav_goal_coords[1]
            distance = math.hypot(dx, dy)
            if distance < 0.20: 
                print(f"TARGET TERCAPAI (Jarak {distance:.2f}m). Stop.")
                self.finish_navigation_success()
                return False 
        return True 

    def finish_navigation_success(self):
        try:
            screen = self.root.get_screen('navigation')
            map_viewer = screen.ids.map_viewer
            if map_viewer.marker:
                map_viewer.remove_widget(map_viewer.marker)
                map_viewer.marker = None
        except Exception: pass

        if hasattr(self.manager, '_send_stop_command'):
            self.manager._send_stop_command()

        screen = self.root.get_screen('navigation')
        screen.ids.navigation_status_label.text = "Status: Target Tercapai!"
        screen.ids.navigate_button.disabled = True
        self.nav_goal_coords = None
        
    def play_audio(self, file_name):
        """Memainkan audio dengan pengecekan aman agar tidak crash."""
        try:
            if os.path.exists(file_name):
                if self.active_sound:
                    self.active_sound.stop()
                
                self.active_sound = SoundLoader.load(file_name)
                
                if self.active_sound:
                    self.active_sound.play()
                else:
                    print(f"WARNING: SoundLoader gagal memuat '{file_name}'.")
            else:
                print(f"WARNING: File audio '{file_name}' TIDAK DITEMUKAN. Abaikan.")
        except Exception as e:
            print(f"ERROR Audio (Ignored): {e}")
            
    def go_to_controller_mode(self):
        self.play_audio('control_robot.mp3')
        status = self.manager.start_controller()
        self.update_status_label('controller', 'controller_status_label', status)
        self.root.current = 'controller'
        
    def enter_main_menu(self):
        self.play_audio('start.mp3')
        self.root.current = 'main_menu'

    def go_to_pre_mapping_mode(self):
        self.play_audio('make_a_map.mp3')
        Clock.schedule_once(lambda dt: setattr(self.root, 'current', 'pre_mapping'), 0.2)

    def go_to_nav_selection_mode(self):
        self.play_audio('do_navigation.mp3')
        Clock.schedule_once(lambda dt: setattr(self.root, 'current', 'nav_selection'), 0.2)

    def exit_controller_mode(self):
        self.manager.stop_controller()
        self.root.current = 'main_menu'

    def go_to_mapping_mode(self, map_name):
        if not map_name.strip(): return
        status = self.manager.start_mapping(map_name)
        self.root.current = 'mapping'
        Clock.schedule_once(lambda dt: self.update_mapping_labels(status, map_name), 0.1)
        self.play_audio('start_mapping.mp3')

    def update_mapping_labels(self, status, map_name):
        screen = self.root.get_screen('mapping')
        if 'mapping_status_label' in screen.ids: screen.ids.mapping_status_label.text = status
        if 'current_map_name_label' in screen.ids: screen.ids.current_map_name_label.text = f"Memetakan: {map_name}"
    
    def exit_mapping_mode(self):
        self.update_status_label('mapping', 'mapping_status_label', 'Menyimpan peta...')
        Clock.schedule_once(self._start_stop_mapping_thread, 0.1)
        self.play_audio('done_save_map.mp3')

    def _start_stop_mapping_thread(self, dt):
        threading.Thread(target=self._thread_safe_stop_mapping, daemon=True).start()

    def _thread_safe_stop_mapping(self):
        self.manager.stop_mapping()
        Clock.schedule_once(self._go_to_main_menu)

    def cancel_mapping_mode(self):
        self.update_status_label('mapping', 'mapping_status_label', 'Membatalkan...')
        Clock.schedule_once(self._start_cancel_mapping_thread, 0.1)

    def _start_cancel_mapping_thread(self, dt):
        threading.Thread(target=self._thread_safe_cancel_mapping, daemon=True).start()

    def _thread_safe_cancel_mapping(self):
        self.manager.cancel_mapping()
        Clock.schedule_once(self._go_to_main_menu)
         
    @mainthread
    def _go_to_main_menu(self, *args):
        self.root.current = 'main_menu'

    def exit_navigation_mode(self):
        if self.nav_status_event:
            self.nav_status_event.cancel()
            self.nav_status_event = None
        self.manager.stop_navigation()
        self.root.current = 'main_menu'

    def on_stop(self):
        self.manager.shutdown()

    @mainthread
    def update_status_label(self, screen_name, label_id, new_text):
        if self.root:
            try:
                screen = self.root.get_screen(screen_name)
                if screen and label_id in screen.ids:
                    screen.ids[label_id].text = new_text
            except Exception: pass

    def start_navigation_with_map(self, map_name, *args):
        self.play_audio('making_navigation.mp3') 
        Clock.schedule_once(lambda dt: self._proceed_start_nav(map_name), 0.2)

    def _proceed_start_nav(self, map_name):
        self.manager.start_navigation(map_name)
        self.root.current = 'navigation'
        
        screen = self.root.get_screen('navigation')
        screen.ids.map_viewer.locked = False
        screen.selected_goal_coords = None
        screen.ids.navigate_button.disabled = True
        screen.ids.navigation_status_label.text = "Status: Pilih titik di peta"

    def start_preset_navigation(self, point_name, *args):
        target_x, target_y = 0.0, 0.0
        
        if point_name == 'A':
            target_x, target_y = -14.75, 6.24
            self.play_audio('point_a.mp3')
        elif point_name == 'B':
            target_x, target_y = -27.49, 7.03
            self.play_audio('point_b.mp3')
        elif point_name == 'C':
            target_x, target_y = -30.93, 3.02
            self.play_audio('point_c.mp3')

        print(f"INFO: Preset Point {point_name} dipilih ({target_x}, {target_y})")
        
        self.manager.start_navigation('test1')
        screen = self.root.get_screen('navigation')
        screen.pending_preset_target = (target_x, target_y, point_name)
        screen.use_image_marker = True 
        self.root.current = 'navigation'

if __name__ == '__main__':
    MainApp().run()
