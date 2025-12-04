import vlc
import os
import sys
import subprocess
from app.core.utils.player_utils import check_ffmpeg_available, ensure_directory_exists, get_output_folder, format_time


class VideoPlayer:
    """视频播放器核心功能"""
    def __init__(self):
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()
        self.media = None
        self.duration = 0
        self.video_path = ""

    def set_vlc_widget(self, widget):
        """设置视频播放窗口"""
        if sys.platform.startswith('linux'):
            self.media_player.set_xwindow(int(widget.winId()))
        elif sys.platform == "win32":
            self.media_player.set_hwnd(int(widget.winId()))
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(int(widget.winId()))

    def open_video(self, video_path, widget):
        """打开视频文件"""
        if not os.path.exists(video_path):
            return False, "视频文件不存在"
        
        try:
            self.video_path = video_path
            self.media = self.instance.media_new(self.video_path)
            self.media_player.set_media(self.media)
            self.set_vlc_widget(widget)
            self.media_player.play()
            return True, ""
        except Exception as e:
            return False, f"打开视频失败: {str(e)}"

    def play_pause(self):
        """播放/暂停视频"""
        try:
            if self.media_player.is_playing():
                self.media_player.pause()
            else:
                self.media_player.play()
            return True, ""
        except Exception as e:
            return False, f"播放控制失败: {str(e)}"

    def set_position(self, position):
        """设置播放位置"""
        try:
            if self.duration > 0:
                # 确保位置在有效范围内
                position = max(0, min(position, self.duration))
                self.media_player.set_time(position)
                return True, ""
            return False, "视频时长未知"
        except Exception as e:
            return False, f"设置播放位置失败: {str(e)}"

    def get_position(self):
        """获取当前播放位置"""
        return self.media_player.get_time()

    def is_playing(self):
        """检查是否正在播放"""
        return self.media_player.is_playing()

    def set_playback_speed(self, speed_str):
        """设置播放速度"""
        try:
            speed = float(speed_str.rstrip("x"))
        except Exception:
            speed = 1.0
        self.media_player.set_rate(speed)
        return speed_str

    def update_duration(self):
        """更新视频时长"""
        dur = self.media_player.get_length()
        if dur > 0:
            self.duration = dur
        return self.duration


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