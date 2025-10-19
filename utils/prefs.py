"""
간단한 JSON 기반 환경설정 저장/로드 유틸리티.
앱 재시작 시 마지막 선택값 복원을 위해 사용.
"""
import json
import os
import threading
from typing import Any, Dict, Optional


# Thread-safe file operations
_file_lock = threading.RLock()

def _get_prefs_path() -> str:
    """사용자 홈 디렉터리 하위에 숨김 폴더를 만들고 그 안에 prefs.json 저장."""
    home = os.path.expanduser("~")
    app_dir = os.path.join(home, ".midi_mixer_control")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "prefs.json")


def load_prefs() -> Dict[str, Any]:
    """환경설정 로드. 파일 없거나 손상 시 빈 dict 반환."""
    with _file_lock:
        path = _get_prefs_path()
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return {}
        except Exception:
            # 손상/파싱 오류 시 안전하게 초기화
            return {}


def save_prefs(prefs: Dict[str, Any]) -> bool:
    """환경설정 저장. 성공 시 True."""
    with _file_lock:
        path = _get_prefs_path()
        try:
            # Create backup of existing file
            backup_path = path + ".backup"
            if os.path.exists(path):
                try:
                    os.rename(path, backup_path)
                except OSError:
                    pass  # Ignore backup creation errors
            
            # Write new file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
            
            # Remove backup if successful
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except OSError:
                    pass  # Ignore backup removal errors
            
            return True
        except Exception:
            # Restore backup if write failed
            backup_path = path + ".backup"
            if os.path.exists(backup_path):
                try:
                    os.rename(backup_path, path)
                except OSError:
                    pass  # Ignore restore errors
            return False


