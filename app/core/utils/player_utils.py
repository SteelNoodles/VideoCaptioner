"""
工具函数模块

提供视频处理相关的通用工具函数，包括时间格式化、FFmpeg检查、目录管理等。
"""
import os
import subprocess
import sys


def format_time(ms):
    """将毫秒转换为HH:MM:SS或MM:SS格式的时间字符串
    
    Args:
        ms (int): 毫秒时间值
        
    Returns:
        str: 格式化后的时间字符串，如 "01:23:45" 或 "23:45"
    """
    if ms < 0: 
        ms = 0
    seconds = (ms // 1000) % 60
    minutes = (ms // 60000) % 60
    hours = (ms // 3600000)
    
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes:02}:{seconds:02}"


def check_ffmpeg_available():
    """检查FFmpeg是否可用
    
    Returns:
        bool: 如果FFmpeg可用返回True，否则返回False
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建
    
    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_output_folder(video_path):
    """获取输出文件夹路径
    
    Args:
        video_path (str): 输入视频文件路径
        
    Returns:
        str: 输出文件夹路径，格式为 "视频文件名_slices"
    """
    base_dir = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(base_dir, f"{base_name}_slices")


def setup_vlc_environment():
    """设置VLC环境（Windows下添加DLL路径）
    
    在Windows系统中，尝试将VLC的默认安装路径添加到DLL搜索路径，
    以确保VLC库能够正确加载。
    """
    if sys.platform == "win32":
        try:
            # 尝试添加VLC的默认安装路径
            vlc_path = r"C:\Program Files\VideoLAN\VLC"
            if os.path.exists(vlc_path):
                os.add_dll_directory(vlc_path)
        except Exception as e:
            print(f"设置VLC环境失败: {e}")