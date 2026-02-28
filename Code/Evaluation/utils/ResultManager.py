import json
import os
import threading

class ResultManager:
    def __init__(self, result_file, comment=""):
        self.result_file = result_file
        self.metadata = {"comment": comment}
        self.lock = threading.Lock()
        self.result = self._load_result()
        if self.result["metadata"]["comment"] != comment:
            print("[Warning] Comment mismatch! We recommend double check output path config.")

    def _load_result(self):
        if os.path.exists(self.result_file):
            try:
                with open(self.result_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                return {"metadata": self.metadata}
        return {"metadata": self.metadata}
    def _save_result(self):
        with self.lock:
            with open(self.result_file, "w", encoding='utf-8') as f:
                json.dump(self.result, f, indent=4, ensure_ascii=False)

    def get(self, key):
        return self.result.get(key)

    def set(self, key, data):
        self.result[key] = data
        self._save_result()
    def has(self, key):
        return key in self.result
    