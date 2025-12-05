from PyQt5.QtCore import QThread, pyqtSignal



class VideoSilerThread(QThread):
    """Version checker"""

    finished = pyqtSignal(str, bool)  # result, is_error

    def __init__(self, slicer, video_path, selected_idxs, parent=None):
        super().__init__(parent)
        self.slicer = slicer
        self.video_path = video_path
        self.selected_idxs = selected_idxs

    def run(self):
        result, is_error = self.slicer.export_videos(self.video_path, self.selected_idxs)
        self.finished.emit(result, is_error)
        
