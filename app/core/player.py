import vlc
import os
import sys
import time
import subprocess
from app.core.utils.player_utils import check_ffmpeg_available, ensure_directory_exists, get_output_folder, format_time

from PyQt5.QtCore import QObject, QVersionNumber, pyqtSignal


class PlayerSignals(QObject):
    media_end = pyqtSignal()

class VideoPlayer:
    """PyQt5 + VLC 稳定播放器"""

    def __init__(self):
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()
        self.media = None
        self.duration = 0
        self.video_path = ""

    def set_vlc_widget(self, widget):
        """设置 PyQt5 显示窗口"""
        # widget.winId())在不同平台上的类型不同
        handle = int(widget.winId())
        
        if sys.platform.startswith("linux"):
            self.media_player.set_xwindow(handle)
        elif sys.platform.startswith("win"):
            self.media_player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(int(widget.winId()))

    def open_video(self, path, widget):
        if not os.path.exists(path):
            return False, "视频文件不存在"

        self.video_path = path
        self.media = self.instance.media_new(path)
        self.media_player.set_media(self.media)
        self.set_vlc_widget(widget)

        self.media_player.play()

        # ★★ 关键：等待 VLC 解析媒体头，获取 duration
        for i in range(20):  # 最多等 0.4 秒
            dur = self.media_player.get_length()
            if dur > 0:
                self.duration = dur
                break
            time.sleep(0.02)

        print("Video duration:", self.duration)

        return True, ""

    def play_pause(self):
        """播放 / 暂停"""
        try:
            if self.media_player.is_playing():
                self.media_player.pause()
            else:
                # 修复：若处于 Ended 状态，必须重新加载媒体
                state = self.media_player.get_state()
                if state == vlc.State.Ended:
                    self._reset_ended_state()

                self.media_player.play()

            return True, ""
        except Exception as e:
            return False, str(e)

    def _reset_ended_state(self):
        """
        若 VLC 到达末尾（Ended），必须重新装载媒体，否则无法 seek。
        """
        print("检测到 Ended 状态，重新加载媒体使其可 seek")
        self.media_player.stop()
        self.media_player.set_media(self.media)
        self.media_player.play()
        self.media_player.pause()

    def set_position(self, position):
        try:
            if self.duration == 0:
                self.update_duration()

            position = max(0, min(position, self.duration))

            state = self.media_player.get_state()

            # 关键：Opening/Buffering 也不能 seek
            if state in (vlc.State.Opening, vlc.State.Buffering, vlc.State.NothingSpecial):
                return False, "播放器尚未准备好，稍后再试"

            if state in (vlc.State.Ended, vlc.State.Stopped):
                self._reset_ended_state()

            self.media_player.set_time(position)
            return True, ""

        except Exception as e:
            return False, str(e)

    def is_playing(self):
        """是否正在播放"""
        return self.media_player.is_playing()

    def get_position(self):
        """获取当前播放位置（毫秒）"""
        return self.media_player.get_time()

    def update_duration(self):
        """获取视频时长（毫秒）"""
        dur = self.media_player.get_length()
        if dur > 0:
            self.duration = dur
        return self.duration

    def set_speed(self, speed):
        """设置播放速度（例如 1.0, 1.25, 0.5）"""
        try:
            s = float(speed)
            self.media_player.set_rate(s)
        except:
            pass
        
    def add_slave(self, sub_path):
        if sub_path:
            self.media_player.add_slave(vlc.MediaSlaveType.subtitle, sub_path, True)
            
    def video_get_spu_description(self):
        return self.media_player.video_get_spu_description()
    
    def video_get_spu(self):
        return self.media_player.video_get_spu()
    
    def video_set_spu(self, track_id):
        return self.media_player.video_set_spu(track_id)

class VideoSlicer:
    """视频切片核心功能"""
    def __init__(self):
        self.segments = []         # 切片：[(start, end), ...]
        self.current_start = None  # 当前切片临时起点

    def mark_in(self, current_time):
        """标记切片起点或终点"""
        if self.current_start is None:
            # 标记起点
            self.current_start = current_time
            return f"已记录起点 {format_time(current_time)}，下次点击为终点", False
        else:
            # 标记终点并创建切片
            start = self.current_start
            end = current_time
            if end <= start:
                return "错误：终点必须晚于起点！", True

            self.segments.append((start, end))
            self.current_start = None
            return f"切片 {len(self.segments)} 已添加：{format_time(start)} → {format_time(end)}", False

    def get_segments(self):
        """获取所有切片"""
        return self.segments

    def export_videos(self, video_path, selected_indices):
        """导出选中的切片"""
        if not selected_indices:
            return "未选中任何切片", True

        # 检查FFmpeg
        if not check_ffmpeg_available():
            return "未检测到FFmpeg。请安装并配置好PATH。", True

        # 检查视频文件
        if not os.path.exists(video_path):
            return "视频文件不存在", True

        # 创建输出文件夹
        output_folder = get_output_folder(video_path)
        try:
            ensure_directory_exists(output_folder)
        except Exception as e:
            return f"创建输出文件夹失败: {str(e)}", True

        success_count = 0
        total_count = len(selected_indices)
        error_messages = []

        for serial, idx in enumerate(selected_indices, 1):
            if 0 <= idx < len(self.segments):
                start_ms, end_ms = self.segments[idx]
                start_sec = start_ms / 1000.0
                duration_sec = (end_ms - start_ms) / 1000.0

                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_filename = os.path.join(output_folder, f"{base_name}_clip_{serial}.mp4")

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_sec),
                    "-t", str(duration_sec),
                    "-i", video_path,
                    "-c", "copy",
                    output_filename
                ]

                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                    success_count += 1
                except subprocess.CalledProcessError as e:
                    error_msg = f"切片 {idx+1} 导出失败: FFmpeg错误"
                    error_messages.append(error_msg)
                except subprocess.TimeoutExpired:
                    error_msg = f"切片 {idx+1} 导出失败: 超时"
                    error_messages.append(error_msg)
                except Exception as e:
                    error_msg = f"切片 {idx+1} 导出失败: {str(e)}"
                    error_messages.append(error_msg)

        result_msg = f"成功导出 {success_count}/{total_count} 个切片！\n保存位置: {output_folder}"
        if error_messages:
            result_msg += "\n\n导出失败的切片：\n" + "\n".join(error_messages)

        return result_msg, False