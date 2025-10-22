import os

# 모든 경로의 기준 (현재 파일 위치)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data_dialog_only.json")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
