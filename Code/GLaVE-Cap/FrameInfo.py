from dataclasses import dataclass

@dataclass
class FrameInfo:
    idx: str|int
    unmasked_base64: str
    masked_base64: str
    metadata: str
    different: str = ""
    attention: str = ""
    merged: str = ""

    def print(self):
        print(f"  frame_idx = {self.idx}")
        print(f"  different = {self.different}")
        print(f"  attention = {self.attention}")
        print(f"  merged    = {self.merged}")
        print(f"  metadata  = {self.metadata}")