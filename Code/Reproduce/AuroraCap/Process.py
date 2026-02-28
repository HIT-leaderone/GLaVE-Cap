import cv2
import os
import base64
import json
import math
import ast
from decord import VideoReader, cpu

from utils.ResultManager import ResultManager

class ProcessAuroraCap:
    def __init__(self, video_file: str, result_file: str, gpt_model):
        self.video_file = video_file
        self.result = ResultManager(result_file, "AuroraCap pipeline")
        self.gpt_model = gpt_model

    def parse(self, response):
        response = response[response.find('{'):response.rfind('}')+1]
        try:
            data = ast.literal_eval(response)  # 安全地解析字符串为字典
            if isinstance(data, dict):
                for key in ['short caption', 'background caption', 'main object caption', 'camera caption', 'reference caption']:
                    if key not in data:
                        raise ValueError(f"No {key}")
                return data
            else:
                raise ValueError("解析后的数据不是字典")
        except (SyntaxError, ValueError) as e:
            print(f"解析失败: {e}")
        return None
    def parse2(self, response):
        response = response[response.find('{'):response.rfind('}')+1]
        try:
            data = ast.literal_eval(response)  # 安全地解析字符串为字典
            if isinstance(data, dict):
                for key in ['detailed dense caption']:
                    if key not in data:
                        raise ValueError(f"No {key}")
                return data
            else:
                raise ValueError("解析后的数据不是字典")
        except (SyntaxError, ValueError) as e:
            print(f"解析失败: {e}")
        return None
    def load_video_base64(self):
        video = VideoReader(self.video_file, ctx=cpu(0), num_threads=1)
        self.fps = video.get_avg_fps()
        base64Frames = []
        MAX_SIZE = 2 * 1024 * 1024  # 2MB in bytes
        cnt_frames = 32
        if len(video) / self.fps < cnt_frames:
            cnt_frames = int(math.floor(len(video) / self.fps))
        self.result.set("#sample_frames", cnt_frames)
        sample_positions = [int(math.floor((len(video)-1) * (p / (cnt_frames-1)))) for p in range(cnt_frames)]
        # print(sample_positions)
        for frame_idx in sample_positions:
            frame = video[frame_idx]
            frame_bgr = cv2.cvtColor(frame.asnumpy(), cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode(".jpg", frame_bgr)
            buffer = base64.b64encode(buffer).decode("utf-8")
            
            while len(buffer.encode('utf-8')) > MAX_SIZE:
                width = int(frame_bgr.shape[1] * 0.9)
                height = int(frame_bgr.shape[0] * 0.9)
                frame_bgr = cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_AREA)
                _, buffer = cv2.imencode(".jpg", frame_bgr)
                buffer = base64.b64encode(buffer).decode("utf-8")
            
            base64Frames.append(buffer)
        return base64Frames

    def get_caption(self):
        sys_prompt = """\
You are describing the video. Please provide detailed captions of the video from different aspects.\
"""
        content = []
        content.append({"type": "text", "text": """\
Please provide detailed and comprehensive captions for the following content: 1. Short Caption: Summarize the video in one detailed sentence, capturing key actions and the overall mood. 2. Background Caption: Provide a detailed description of the background, including objects, location, weather, time, and any dynamic elements such as movements in the environment. 3. Main Object Caption: Give a thorough description of the main subject's actions, attributes, interactions, and movements throughout the video frames, including changes in posture, expression, or speed. 4. Camera Caption: Describe the camera work in detail, including shot types, angles, movements, transitions, and any special effects used to enhance the video. 5. Reference Caption: Generate a detailed dense caption for the video that is at least 300 words long. The caption should capture all visible actions, environmental details, and the overall emotional atmosphere in depth. Describe in detail the interactions between the main subjects and their environment, including subtle nuances of their movements or expressions. Elaborate on the sounds, textures, and other sensory experiences depicted in the video. Discuss the camera techniques used extensively, including shot types, angles, movements, and transitions. Highlight the mood and tone of the video throughout, creating a rich narrative that connects viewers emotionally to the scene. Include comprehensive descriptions of background elements that add context and depth, such as weather conditions, time of day, and cultural or historical settings. Make sure to provide a vivid portrayal that is engaging, informative, and rich enough for AI to re-generate the video content. No need to provide summary content. Do not describe each frame individually. Avoid using phrases like 'first frame'. The description should be rich enough for AI to re-generate the video. Please generate the response as a Python dictionary string with keys like 'short caption'. DO NOT PROVIDE ANY OTHER OUTPUT TEXT OR XPLANATION. Only provide the Python dictionary string.
These are the frames from the video:\
"""})
        for i in range(len(self.frames)):
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
        for retry in range(10):
            response = self.gpt_model.send_stable_request(messages)
            print(response)
            res_dict = self.parse(response)
            if res_dict != None:
                break
            print(f"Retry: {retry}")

        self.result.set("intermediate_caption", response)
        messages.append({
            "role": "assistant",
            "content": response
        })
        query2 = "The video has been describe from the following aspects:"
        query2 += "1. short caption:" + res_dict['short caption']
        query2 += ", 2. background caption: " + res_dict['background caption']
        query2 += ", 3. main object caption: " + res_dict['main object caption']
        query2 += ", 4. camera caption: " + res_dict['camera caption']
        query2 += ", 5.Reference Caption: " + res_dict['reference caption']
        query2 += """\
Please generate a detailed dense caption for the video that is pretty long. You should expand the reference caption upon the information provided in the short caption, background caption, main object caption, and camera caption. Ensure that the detailed caption does not introduce any new entities or relationships that were not mentioned in the previous captions. Make sure to provide a vivid portrayal that is engaging, informative, and rich enough for AI to re-generate the video content. Avoid using phrases like 'first frame', 'short caption', 'background caption', 'main object caption', and 'camera caption'. The description should be rich enough for AI to re-generate the video. The key in python dictionary should be 'detailed dense caption'\
"""
        messages.append({
            "role": "user",
            "content": query2
        })
        for retry in range(10):
            response = self.gpt_model.send_stable_request(messages)
            print(response)
            res_dict2 = self.parse2(response)
            if res_dict2 != None:
                break
            print(f"Retry: {retry}")
        print(res_dict2['detailed dense caption'])
        self.result.set("caption", res_dict2['detailed dense caption'])

    def __call__(self):
        if self.result.has("caption"):
            # print(self.result.get('caption'))
            print("Cached")
            return
        # Get basic info
        self.frames = self.load_video_base64()
        self.get_caption()
        self.result.set('#prompt_tokens', self.gpt_model.prompt_tokens)
        self.result.set('#completion_tokens', self.gpt_model.completion_tokens)
