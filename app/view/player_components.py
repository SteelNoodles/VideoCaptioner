from PyQt5.QtWidgets import (
    QSlider, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QComboBox, QStyle
)
from PyQt5.QtCore import Qt, QPoint


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


class VideoSlicerUI(QWidget):
    """视频切片器的主界面组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化界面布局"""
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
        control_layout = QHBoxLayout()
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        control_layout.addWidget(self.play_btn)
        self.open_btn = QPushButton("打开视频")
        control_layout.addWidget(self.open_btn)

        # 倍速
        self.speed_box = QComboBox()
        self.speed_box.addItems(['0.5x', '1.0x', '1.25x', '1.5x', '2.0x'])
        self.speed_box.setCurrentText('1.0x')
        self.speed_box.setMaximumWidth(72)
        control_layout.addWidget(QLabel("倍速:"))
        control_layout.addWidget(self.speed_box)
        control_layout.addStretch()
        lower_layout.addLayout(control_layout, stretch=3)

        # 切片区
        tag_layout = QHBoxLayout()
        self.lbl_status = QLabel("状态: 等待操作")
        tag_layout.addWidget(self.lbl_status)
        self.btn_mark_in = QPushButton("标记时间戳(❤️/切片)")
        tag_layout.addWidget(self.btn_mark_in)
        self.btn_export = QPushButton("导出选中切片")
        self.btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        tag_layout.addWidget(self.btn_export)
        tag_layout.addStretch()
        lower_layout.addLayout(tag_layout, stretch=6)

        main_layout.addLayout(lower_layout)

        # (4) 切片列表（带勾选）
        self.segment_list = QListWidget()
        main_layout.addWidget(self.segment_list, stretch=2)