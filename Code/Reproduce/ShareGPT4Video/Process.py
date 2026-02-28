import cv2
import os
import base64
import json
from decord import VideoReader, cpu

from utils.ResultManager import ResultManager
from .KeyFrame import KeyFrame
from utils.GPTModel import GPT4o

class ProcessShareGPT4Video:
    def __init__(self, video_file: str, result_file: str, gpt_model):
        self.video_file = video_file
        self.result = ResultManager(result_file, "ShareGPT4Video pipeline")
        self.gpt_model = gpt_model
        self.cnt_prompt_tokens = 0
        self.cnt_completion_tokens = 0
        if self.result.has("#prompt_tokens"):
            self.cnt_prompt_tokens = self.result.get("#prompt_tokens")
            self.cnt_completion_tokens = self.result.get("#completion_tokens")

    def load_video_base64(self):
        video = VideoReader(self.video_file, ctx=cpu(0), num_threads=1)
        self.fps = video.get_avg_fps()
        base64Frames = []
        MAX_SIZE = 4 * 1024 * 1024  # 4MB in bytes
        
        for frame_idx in self.keyframe_idx:
            frame = video[frame_idx]
            frame_bgr = cv2.cvtColor(frame.asnumpy(), cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode(".png", frame_bgr)
            buffer = base64.b64encode(buffer).decode("utf-8")
            
            while len(buffer.encode('utf-8')) > MAX_SIZE:
                width = int(frame_bgr.shape[1] * 0.9)
                height = int(frame_bgr.shape[0] * 0.9)
                frame_bgr = cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_AREA)
                _, buffer = cv2.imencode(".png", frame_bgr)
                buffer = base64.b64encode(buffer).decode("utf-8")
            
            base64Frames.append(buffer)
        return base64Frames
    
    def save_tokens(self):
        self.result.set('#prompt_tokens', self.cnt_prompt_tokens + self.gpt_model.prompt_tokens)
        self.result.set('#completion_tokens', self.cnt_completion_tokens + self.gpt_model.completion_tokens)
    
    def step1(self):
        sys_prompt = """\
# Character
You are an excellent video frame analyst. Utilizing your incredible attention to detail, you provide clear, sequential descriptions for video frames. You excel in identifying and conveying changes in actions, behaviors, environment, states and attributes of objects, and camera movements between adjacent video frames.

# Skills
## Skill 1: Describing Object Actions and Behaviors
- Describe the action or behavior of objects within the frame.
- Notice and describe changes in the actions or behaviors between frames.

## Skill 2: Describing Environment and Background Variations
- Elaborate on environment and background alterations seen between frames.

## Skill 3: Describing Object Appearances
- Describe the appearance of objects within the frame.
- Depict variations in the states and attributes of objects between frames.

## Skill 4: Describing Camera Movements
- Perceive the camera's movements, such as panning or zooming.
- Convey these camera movements and describe how they impact the footage displayed.

# Constraints
- State facts objectively without using any rhetorical devices such as metaphors or personification.
- Stick to a narrative format for descriptions, avoiding list-like itemizations.
- Exclude sounds-related aspects, given the unavailability of audio signals.
- Descriptions should be fluent and precise, avoiding analyzing and waxing lyrical.
- Descriptions need to be concise, describing only the information that can be determined, without analysis or speculation.
- If there is only one inputted frame, that is, the first frame, describe the image details directly and do not concern yourself with connections between other frames.
- Do not mention the frame number and timestamp of the current frame.

# Structured Input
Video frame <idx_n-1> at <timestamp_n-1> Second(s) <frame_n-1><diff_caption_n-1>
Video frame <idx_n> at <timestamp_n> Second(s) <frame_n>
"""
        if not self.result.has("diff_caption"):
            diff_caption = []
        else:
            diff_caption = self.result.get("diff_caption")
        for i in range(len(diff_caption), len(self.frames)):
            print(f"------ Getting diff caption {i} --------")
            content = []
            if i != 0:
                content.append({"type": "text", "text": f"Video frame {i-1} at {(self.keyframe_idx[i-1]/self.fps):.1f} Second(s)"})
                print(content)
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.frames[i-1]}"}})
                content.append({"type": "text", "text": diff_caption[i-1]})
            content.append({"type": "text", "text": f"Video frame {i} at {(self.keyframe_idx[i]/self.fps):.1f} Second(s)"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.frames[i]}"}})
            messages = [
                {
                    "role": "system",
                    "content": sys_prompt
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            response = self.gpt_model.send_stable_request(messages)
            diff_caption.append(response)
            self.result.set("diff_caption", diff_caption)
            self.save_tokens()
    def step2(self):
        sys_prompt = """\
# Character
I will provide you with the descriptions of each of multiple consecutive frames in a video, each containing the
content of the current frame and how the current frame has changed relative to the previous frame. Your task is to generate description for the entire video based on the descriptions of all frames.

# Skills
- Summarize sequentially, maintaining coherence between frames and the integrity of the timeline.

# Constraints
- Don't analyze, subjective interpretations, aesthetic rhetoric, etc., just objective statements.
- Only consider information that can be confidently derived from the descriptions of each frame.
- Do not extrapolate or imagine, remove uncertain information.
- No mention of specific frames index or timestamps.

# Structured Input
<timestamp_1><caption_1><timestamp_2><caption_2>...<timestamp_n><caption_n>
"""
        diff_caption = self.result.get("diff_caption")
        content = []
        for i in range(len(self.frames)):
            content.append({"type": "text", "text": f"{((self.keyframe_idx[i-1])/self.fps):.1f} "})
            content.append({"type": "text", "text": diff_caption[i]})
        messages = [
            {
                "role": "system",
                "content": sys_prompt
            },
            {
                "role": "user",
                "content": content
            }
        ]
        response = self.gpt_model.send_stable_request(messages)
        self.result.set("caption", response)
        self.save_tokens()
        
    def __call__(self):
        if self.result.has("caption"):
            # print(self.result.get('caption'))
            print("Cached")
            return
        if self.result.has("keyframe_idx"):
            self.keyframe_idx = self.result.get("keyframe_idx")
        else:
            key_frame = KeyFrame()
            self.keyframe_idx = key_frame.extract_keyframe(self.video_file)
            self.result.set("keyframe_idx", self.keyframe_idx)
            self.result.set("#sample_frames", len(self.keyframe_idx))

        self.frames = self.load_video_base64()
        self.step1()
        self.step2()
