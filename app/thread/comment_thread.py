import os
from pathlib import Path
from typing import List, Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from app.core.utils.logger import setup_logger

# 检查yt_dlp模块是否安装
try:
    import yt_dlp
except ImportError:
    logger.error("yt_dlp模块未安装")
    yt_dlp = None

# 配置日志
logger = setup_logger("comment_thread")


def parse_votes(votes):
    """
    解析点赞数字符串，支持多种格式：
    - 普通数字: "9748", "500"
    - K格式: "1.2K", "5k"
    - 千位分隔符: "9,748", "1,234.5K"
    - 带单位: "9748赞", "5K votes"
    
    Args:
        votes: 点赞数字符串或数值
        
    Returns:
        解析后的整数点赞数
    """
    try:
        if isinstance(votes, str):
            votes = votes.strip()
            
            # 处理包含K/k的情况（如5K、1.5K）
            if 'K' in votes or 'k' in votes:
                # 提取数字部分（支持小数点和千位分隔符）
                match = __import__('re').search(r'([\d,]+(?:\.\d+)?)[Kk]', votes)
                if match:
                    num_str = match.group(1)
                    # 移除千位分隔符
                    num_str = num_str.replace(',', '')
                    # 转换为整数（乘以1000）
                    return int(float(num_str) * 1000)
                else:
                    return 0
            else:
                # 提取所有数字部分（包括小数点和千位分隔符）
                match = __import__('re').search(r'([\d,]+(?:\.\d+)?)', votes)
                if match:
                    num_str = match.group(1)
                    # 移除千位分隔符
                    num_str = num_str.replace(',', '')
                    # 转换为整数
                    return int(float(num_str))
                else:
                    return 0
        else:
            # 如果不是字符串，直接尝试转换为整数
            return int(votes)
    except (ValueError, AttributeError, TypeError):
        return 0


class CommentThread(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, youtube_url: str):
        super().__init__()
        self.youtube_url: str = youtube_url

    def run(self):
        try:
            if not yt_dlp:
                raise Exception("yt_dlp模块未安装")

            self.progress.emit(0, "正在准备下载评论...")
            
            comments = []
            logger.info(f"开始从 YouTube 下载评论: {self.youtube_url}")
            
            # 配置 yt-dlp 选项
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writecomments': True,
                'skip_download': True,
                'extract_flat': True,
            }
            
            # 使用 yt-dlp 下载评论
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.progress.emit(30, "正在分析视频信息...")
                info_dict = ydl.extract_info(self.youtube_url, download=False)
                
                # 提取评论
                if 'comments' in info_dict:
                    self.progress.emit(60, "正在下载评论...")
                    for comment in info_dict['comments']:
                        comments.append({
                            'text': comment.get('text', ''),
                            'votes': parse_votes(comment.get('like_count', '0'))
                        })
            
            self.progress.emit(100, f"成功下载 {len(comments)} 条评论")
            logger.info(f"成功下载 {len(comments)} 条评论")
            self.finished.emit(comments)

        except Exception as e:
            logger.error(f"下载 YouTube 评论失败: {e}")
            self.error.emit(str(e))
            self.progress.emit(100, "评论下载失败")

    def stop(self):
        """停止评论下载"""
        try:
            self.terminate()
            # 等待最多3秒
            if not self.wait(3000):
                logger.warning("评论下载线程未能在3秒内正常停止")
            
            self.progress.emit(100, "已终止")

        except Exception as e:
            logger.error(f"停止评论下载线程时出错：{str(e)}")
            self.progress.emit(100, "终止时发生错误")
