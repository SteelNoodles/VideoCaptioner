from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QHBoxLayout, QPushButton, QStyle, QComboBox, \
    QListWidget, QFileDialog
from PyQt5.QtCore import Qt, QPoint, QStandardPaths
from qfluentwidgets import PushButton, PrimaryPushButton, ComboBox, BodyLabel, ListWidget, CommandBar, Action, FluentIcon
from qfluentwidgets import FluentIcon as FIF
from app.core.entities import (
    SupportedAudioFormats,
    SupportedVideoFormats,
    TranscribeModelEnum,
    TranscribeTask,
    VideoInfo,
)

import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QStyle, QListWidgetItem
from PyQt5.QtCore import QTimer, Qt
from app.view.player_components import VideoSlicerUI
from app.core.player import VideoPlayer, VideoSlicer
from app.core.utils.player_utils import setup_vlc_environment, format_time
from app.thread.video_silce_thread import VideoSilerThread


class HoverSlider(QSlider):
    """自定义带悬停气泡的滑块组件"""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # tooltip_label无父对象, 浮动于桌面
        self.tooltip_label = QLabel(None, flags=Qt.ToolTip)
        self.tooltip_label.setStyleSheet(
            "color: white; background: rgba(0,0,0,200);"
            "border-radius: 4px; padding:2px 10px; font-size: 13px;"
        )
        self.tooltip_label.hide()
        self.setMouseTracking(True)
        self.duration = 0
        self.format_time = lambda ms: ms
        self.last_show_pos = None

    def set_duration(self, duration):
        """设置视频总时长"""
        self.duration = duration

    def mouseMoveEvent(self, event):
        """鼠标移动时显示悬浮时间"""
        super().mouseMoveEvent(event)
        if not self.duration:
            self.tooltip_label.hide()
            return
        x = event.pos().x()
        slider_width = self.width()
        relpos = x / slider_width
        relpos = max(0, min(1, relpos))
        ms = int(relpos * self.duration)
        text = self.format_time(ms) if callable(self.format_time) else str(ms)

        # 计算Tooltip的位置（全局）
        global_p = self.mapToGlobal(QPoint(x, 0))
        label_width = self.tooltip_label.fontMetrics().boundingRect(text).width() + 18
        label_height = 28
        popup_x = global_p.x() - label_width // 2
        popup_y = global_p.y() - label_height - 10

        self.tooltip_label.setText(text)
        self.tooltip_label.resize(label_width, label_height)
        self.tooltip_label.move(popup_x, popup_y)
        self.tooltip_label.show()

    def leaveEvent(self, event):
        """鼠标离开时隐藏悬浮提示"""
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标点击时设置滑块位置"""
        super().mousePressEvent(event)
        # 计算点击位置对应的滑块值
        if self.orientation() == Qt.Horizontal:
            pos = event.pos().x()
            slider_width = self.width()
        else:
            pos = event.pos().y()
            slider_width = self.height()

        relpos = pos / slider_width
        relpos = max(0, min(1, relpos))
        value = self.minimum() + int(relpos * (self.maximum() - self.minimum()))

        # 设置滑块位置
        self.setValue(value)


class VideoSliceInterface(QWidget):
    # def __init__(self, parent=None):
    #     super().__init__(parent)

    #     # 设置对象名称和样式
    #     self.setObjectName("VideoSliceInterface")
    #     self.setStyleSheet(
    #         """
    #         VideoSliceInterface{background: white}
    #     """
    #     )

    #     self.init_ui()

    # def init_ui(self):
    #     """初始化界面布局"""
    #     main_layout = QVBoxLayout()
    #     self.setLayout(main_layout)

    #     # (1) 视频画面
    #     self.video_widget = QWidget(self)
    #     self.video_widget.setMinimumHeight(380)
    #     main_layout.addWidget(self.video_widget, stretch=6)

    #     # (2) 进度条（带悬浮时间气泡）
    #     self.slider = HoverSlider(Qt.Horizontal, self)
    #     main_layout.addWidget(self.slider)

    #     # (3) 下排：分为 "播放控制+倍速" 和 "切片标记与导出" 两组
    #     lower_layout = QHBoxLayout()

    #     # 控制区
    #     control_layout = CommandBar(self)
    #     control_layout.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # type: ignore
    #     control_layout.setFixedHeight(40)
    #     self.play_btn = PushButton()
    #     self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
    #     control_layout.addWidget(self.play_btn)        
    #     self.open_file_action = Action(FluentIcon.FOLDER, self.tr("打开视频"))
    #     self.open_file_action.triggered.connect(self._on_file_select)
        
    #     control_layout.addAction(self.open_file_action)

    #     # 倍速
    #     self.speed_box = ComboBox()
    #     self.speed_box.addItems(['0.5x', '1.0x', '1.25x', '1.5x', '2.0x'])
    #     self.speed_box.setCurrentText('1.0x')
    #     self.speed_box.setMaximumWidth(72)
    #     control_layout.addWidget(BodyLabel("倍速:"))
    #     control_layout.addWidget(self.speed_box)
    #     control_layout.addSeparator()
    #     lower_layout.addWidget(control_layout, stretch=3)

    #     # 切片区
    #     tag_layout = QHBoxLayout()
    #     self.lbl_status = BodyLabel("状态: 等待操作")
    #     tag_layout.addWidget(self.lbl_status)
    #     self.btn_mark_in = PrimaryPushButton("标记时间戳(❤️/切片)")
    #     tag_layout.addWidget(self.btn_mark_in)

    #     self.btn_export = PrimaryPushButton(self.tr("导出选中切片"), self, icon=FIF.PLAY)
    #     # self.btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
    #     tag_layout.addWidget(self.btn_export)
    #     tag_layout.addStretch()
    #     lower_layout.addLayout(tag_layout, stretch=6)

    #     main_layout.addLayout(lower_layout)

    #     # (4) 切片列表（带勾选）
    #     self.segment_list = ListWidget()
    #     # self.segment_list.setStyleSheet()
    #     main_layout.addWidget(self.segment_list, stretch=2)
        
        
    # def _on_file_select(self):
    #     """文件选择处理"""
    #     desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
    #     file_dialog = QFileDialog()

    #     video_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedVideoFormats)
    #     audio_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedAudioFormats)
    #     filter_str = f"{self.tr('媒体文件')} ({video_formats} {audio_formats});;{self.tr('视频文件')} ({video_formats});;{self.tr('音频文件')} ({audio_formats})"

    #     file_path, _ = file_dialog.getOpenFileName(
    #         self, self.tr("选择媒体文件"), desktop_path, filter_str
    #     )
    #     if file_path:
    #         self.update_info(file_path)
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setWindowTitle("跨平台VLC倍速切片播放器")
        # self.resize(950, 700)
        
        # 设置对象名称和样式
        self.setObjectName("VideoSliceInterface")
        self.setStyleSheet(
            """
            VideoSliceInterface{background: white}
        """
        )

        # 初始化核心组件
        self.setup_components()
        self.setup_ui()
        self.setup_connections()
        self.setup_timer()

    def setup_components(self):
        """设置核心组件
        
        初始化视频播放器和切片器，配置VLC环境。
        """
        setup_vlc_environment()
        self.video_player = VideoPlayer()
        self.slicer = VideoSlicer()

    def setup_ui(self):
        """设置用户界面
        
        创建并配置主窗口的UI组件。
        """
        # self = VideoSlicerUI(self)
        # # self.setCentralWidget(self)
        # self.slider.format_time = format_time  # 注入格式化方法
        # """初始化界面布局"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # (1) 视频画面
        self.video_widget = QWidget(self)
        self.video_widget.setMinimumHeight(380)
        main_layout.addWidget(self.video_widget, stretch=6)

        # (2) 进度条（带悬浮时间气泡）
        self.slider = HoverSlider(Qt.Horizontal, self)
        main_layout.addWidget(self.slider)

        # (3) 下排：分为 "播放控制+倍速" 和 "切片标记与导出" 两组
        lower_layout = QHBoxLayout()

        # 控制区
        control_layout = CommandBar(self)
        control_layout.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # type: ignore
        control_layout.setFixedHeight(40)
        self.play_btn = PushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        control_layout.addWidget(self.play_btn)        
        self.open_file_action = Action(FluentIcon.FOLDER, self.tr("打开视频"))
        # self.open_file_action.triggered.connect(self._on_file_select)
        
        control_layout.addAction(self.open_file_action)

        # 倍速
        self.speed_box = ComboBox()
        self.speed_box.addItems(['0.5x', '1.0x', '1.25x', '1.5x', '2.0x'])
        self.speed_box.setCurrentText('1.0x')
        self.speed_box.setMaximumWidth(72)
        control_layout.addWidget(BodyLabel("倍速:"))
        control_layout.addWidget(self.speed_box)
        control_layout.addSeparator()
        lower_layout.addWidget(control_layout, stretch=3)

        # 切片区
        tag_layout = QHBoxLayout()
        self.lbl_status = BodyLabel("状态: 等待操作")
        tag_layout.addWidget(self.lbl_status)
        self.btn_mark_in = PrimaryPushButton("标记时间戳(❤️/切片)")
        tag_layout.addWidget(self.btn_mark_in)

        self.btn_export = PrimaryPushButton(self.tr("导出选中切片"), self, icon=FIF.PLAY)
        # self.btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        tag_layout.addWidget(self.btn_export)
        tag_layout.addStretch()
        lower_layout.addLayout(tag_layout, stretch=6)

        main_layout.addLayout(lower_layout)

        # (4) 切片列表（带勾选）
        self.segment_list = ListWidget()
        # self.segment_list.setStyleSheet()
        main_layout.addWidget(self.segment_list, stretch=2)

    def setup_connections(self):
        """建立信号与槽的连接
        
        将UI组件的信号连接到对应的处理函数。
        """
        # 文件和播放控制
        self.open_file_action.triggered.connect(self.open_file)
        self.play_btn.clicked.connect(self.play_pause_video)
        self.slider.sliderMoved.connect(self.set_position)
        self.slider.valueChanged.connect(self.set_position)
        
        # 倍速控制
        self.speed_box.currentTextChanged.connect(self.set_playback_speed)
        
        # 切片功能
        self.btn_mark_in.clicked.connect(self.mark_in)
        self.btn_export.clicked.connect(self.export_videos)

    def setup_timer(self):
        """设置定时器用于同步UI
        
        创建并启动定时器，定期更新播放进度和UI状态。
        """
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.sync_ui)
        self.timer.start()

    ######## 文件与视频控制 ########
    def open_file(self):
        """打开视频文件"""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilters(["Videos (*.mp4 *.avi *.mkv *.mov *.flv *.wmv)"])
        if file_dialog.exec_():
            files = file_dialog.selectedFiles()
            if files:
                self.video_path = files[0]
                success, error_msg = self.video_player.open_video(self.video_path, self.video_widget)
                if success:
                    self.lbl_status.setText(f"已加载: {os.path.basename(self.video_path)}")
                    self.slicer = VideoSlicer()  # 重置切片列表
                    self.segment_list.clear()
                    self.slider.setRange(0, 0)
                    self.slider.set_duration(0)
                    
                    # 延迟获取视频时长
                    QTimer.singleShot(500, self.try_update_duration)
                else:
                    QMessageBox.warning(self, "错误", error_msg)

    def try_update_duration(self):
        """尝试更新视频时长"""
        duration = self.video_player.update_duration()
        if duration > 0:
            self.slider.setRange(0, duration)
            self.slider.set_duration(duration)
        else:
            QTimer.singleShot(500, self.try_update_duration)

    def play_pause_video(self):
        """播放/暂停视频"""
        success, error_msg = self.video_player.play_pause()
        if not success:
            QMessageBox.warning(self, "错误", error_msg)

    def set_position(self, position):
        """设置播放位置"""
        success, error_msg = self.video_player.set_position(position)
        if not success and error_msg:
            QMessageBox.warning(self, "错误", error_msg)

    def sync_ui(self):
        """同步UI状态"""
        # 更新进度条
        pos = self.video_player.get_position()
        if pos == -1: pos = 0
        self.slider.blockSignals(True)
        self.slider.setValue(pos)
        self.slider.blockSignals(False)
        
        # 更新播放/暂停按钮
        if self.video_player.is_playing():
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # 更新视频时长
        if self.slider.duration == 0:
            duration = self.video_player.update_duration()
            if duration > 0:
                self.slider.setRange(0, duration)
                self.slider.set_duration(duration)

    ######## 倍速控制 ########
    def set_playback_speed(self, speed_str):
        """设置播放速度"""
        speed = self.video_player.set_playback_speed(speed_str)
        self.lbl_status.setText(f"当前播放速度：{speed}")

    ######## 切片与导出 ########
    def mark_in(self):
        """标记切片起点或终点"""
        current_time = self.video_player.get_position()
        status, is_error = self.slicer.mark_in(current_time)
        
        if is_error:
            QMessageBox.warning(self, "错误", status)
        else:
            self.lbl_status.setText(status)
            
            # 如果是创建了新切片，添加到列表
            if "已添加" in status:
                segment = self.slicer.segments[-1]
                start_str = format_time(segment[0])
                end_str = format_time(segment[1])
                item = QListWidgetItem(f"切片 {len(self.slicer.segments)}: {start_str} → {end_str}")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)  # 默认勾选
                self.segment_list.addItem(item)

    def export_videos(self):
        """导出选中的切片（子线程）"""
        if not hasattr(self, 'video_path') or not self.video_path:
            QMessageBox.warning(self, "错误", "请先打开视频文件。")
            return
        
        if not self.slicer.segments:
            QMessageBox.warning(self, "无内容", "没有任何可导出的切片。")
            return

        selected_idxs = []
        for idx in range(self.segment_list.count()):
            item = self.segment_list.item(idx)
            if item.checkState() == Qt.Checked:
                selected_idxs.append(idx)

        # 禁用导出按钮，防止重复点击
        self.btn_export.setEnabled(False)
        self.lbl_status.setText("正在导出切片，请稍候...")

        # 创建线程并启动
        self.worker = VideoSilerThread(self.slicer, self.video_path, selected_idxs)
        self.worker.finished.connect(self._on_export_finished)
        self.worker.start()

    def _on_export_finished(self, result, is_error):
        # 恢复导出按钮可用
        self.btn_export.setEnabled(True)
        self.lbl_status.setText("导出完成" if not is_error else "导出失败")
        if is_error:
            QMessageBox.critical(self, "错误", result)
        else:
            QMessageBox.information(self, "完成", result)
