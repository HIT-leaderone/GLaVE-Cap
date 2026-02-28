import cv2
import os
import base64
import json
from decord import VideoReader, cpu

from utils.ResultManager import ResultManager

class ProcessLVD2M:
    def __init__(self, video_file: str, result_file: str, gpt_model):
        self.video_file = video_file
        self.result = ResultManager(result_file, "LVD-2M pipeline")
        self.gpt_model = gpt_model
        self.cnt_prompt_tokens = 0
        self.cnt_completion_tokens = 0
        if self.result.has("#prompt_tokens"):
            self.cnt_prompt_tokens = self.result.get("#prompt_tokens")
            self.cnt_completion_tokens = self.result.get("#completion_tokens")
        if not self.result.has("step1"):
            self.result.set("step1", [])
        if not self.result.has("step2"):
            self.result.set("step2", [])

    
    def load_video_base64(self):
        video = VideoReader(self.video_file, ctx=cpu(0), num_threads=1)
        original_fps = round(video.get_avg_fps())
        frames_per_30s = original_fps * 30
        sample_positions = [int(frames_per_30s * p / 12) for p in [1, 3, 5, 7, 9, 11]]

        base64Frames = []
        MAX_SIZE = 4 * 1024 * 1024  # 4MB in bytes
        
        for start in range(0, len(video), frames_per_30s):
            for pos in sample_positions:
                frame_idx = start + pos
                if frame_idx >= len(video):
                    break
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
        step1 = self.result.get("step1")
        start_frame = 6 * len(step1)
        for i in range(start_frame, len(self.frames), 6):
            l = i
            r = min(i + 6, len(self.frames))
            content = []
            content.append(({"type": "text", "text": f"""\
6 images are given containing of equally spaced frames sampled from a video. They're arranged in a temporal order.
Your task is to describe the overall content and context of the video based on the image.
Make sure your description adheres to the guidelines below:
1. Don't describe the content frame-by-frame. Don't use words like 'in the first frame'. Instead, provide
an overview of the video that captures details of the main actions, settings, and characters.
2. You should highlight details of any significant events, characters, backgrounds or objects that appear
throughout the video.
3. In your description, remember to carefully check the camera perspective, view, movements and
changes in shooting angles in the sequence of video frames.
"""}))
            for j in range(l, r):
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.frames[j]}"}})
            
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]
            response = self.gpt_model.send_stable_request(messages)
            print(response)
            step1.append(response)
            self.result.set("step1", step1)
            self.save_tokens()

    def step2(self):
        step1 = self.result.get('step1')
        step2 = self.result.get('step2')
        start = len(step2)
        for i in range(start, len(step1)):
            content = []
            content.append(({"type": "text", "text": f"""\
I need assistance rewriting captions for a video. The new caption should replicate the style typically used in
text prompts for video generation.
And your task is to craft a caption that is clear, concise, and factual, following the guidelines below:
1. Describe only what can be directly observed in the video, using straightforward and objective language. In
your caption, avoid subjective interpretations or emotional language.
2. Your new caption should provide an overview of the video that captures the main actions, background,
visual style, and characters.
3. Organize your caption in a way that effectively and succinctly conveys the storyline or main events of the
video.
4. Ensure your caption includes details about the setting, characters and key actions of the video.
5. Don't include any information about the exact number of frames in the video.
6. Do not describe each frame individually. Do not reply with words like 'the first/second/... frame'.
Start your revised caption with the prefix “CAPTION:” and make sure it adheres to the above guidelines.
Here is the raw caption you need to rewrite:
{step1[i]}
"""}))
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]
            response = self.gpt_model.send_stable_request(messages)
            print(response)
            step2.append(response)
            self.result.set("step2", step2)
            self.save_tokens()

    def step3(self):
        step2 = self.result.get('step2')
        content = []
        tmp = """\
I need assistance composing and rewriting captions for a video. The new caption should replicate the style
typically used in text prompts for video generation.
And your task is to craft a caption that is clear, concise, and factual, according to given list of cpations.
The list of captions are in a chronological order, describing the content of consecutive video clips from the
same video.
When writing the caption, you should follow the guidelines below:
1. Describe only what can be directly observed in the video, using straightforward, concise and objective
language. In your caption, avoid subjective interpretations or emotional language.
2. Your new caption should provide an overview of the video that captures the main actions, background,
visual style, and characters.
3. Organize your caption in a way that effectively and succinctly conveys the storyline or main events of the
video.
4. Ensure your caption concisely includes the details about the setting, characters and key actions of the video.
5. Don't include any information about the exact number of frames or clips in the video.
6. Do not describe each frame individually. Do not reply with words like 'the first/second/... frame'.
Start your revised caption with the prefix “CAPTION:” and make sure it adheres to the above guidelines.
Here is the list of descriptions of video clips:
"""
        for cap in step2:
            tmp += cap + " "
        content.append(({"type": "text", "text": tmp}))
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        response = self.gpt_model.send_stable_request(messages)
        print(response)
        self.result.set("caption", response)
        self.save_tokens()

    def __call__(self):
        if self.result.has("caption"):
            # print(self.result.get('caption'))
            print("Cached")
            return
        self.frames = self.load_video_base64()
        self.result.set("#sample_frames", len(self.frames))
        self.step1()
        self.step2()
        self.step3()
