import ast
import datetime
import json
import os
import sys
import time
import base64
import yaml
from FrameInfo import FrameInfo
from ProcessFrame import ProcessFrame 
from Summary import Summary
from Question import Question
from gpt_model import GPT4o
from Overview import Overview

class ProcessVideo:
    def __init__(self, unmasked_frames_dir, masked_frames_dir, metadata, output_path, video_path, frame_data):
        print(f"unmasked_frames_dir = {unmasked_frames_dir}")
        print(f"masked_frames_dir   = {masked_frames_dir}")
        print(f"output_path         = {output_path}")
        print(f"video_path          = {video_path}")
        # Read Frames
        self.output_path = output_path
        def read_frames(frames_dir):
            frames_name = [
                p for p in os.listdir(frames_dir)
                if os.path.splitext(p)[-1] in [".jpg", ".jpeg", ".JPG", ".JPEG", ".png"]
            ]
            frames_name.sort(key=lambda p: int(os.path.splitext(p)[0]))
            frames = []
            for frame_name in frames_name:
                frame_path = os.path.join(frames_dir, frame_name)
                image_file = open(frame_path, "rb") 
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                frames.append(base64_image)
            return frames
        unmasked_frames = read_frames(unmasked_frames_dir)
        masked_frames = read_frames(masked_frames_dir)
        if len(unmasked_frames) != len(metadata) or len(masked_frames) != len(metadata):
            raise Exception(f"#unmasked_frames({len(unmasked_frames)}), #masked_frames({len(masked_frames)}), #metadata({len(metadata)}) mismatch.")
        # Init Result
        try:
            with open(f'{output_path}.json', 'r') as f:
                self.result = json.load(f)
        except:
           self.result = {}
           self.result["different"] = [""]*len(unmasked_frames)
           self.result["attention"] = [""]*len(unmasked_frames)
           self.result["merged"] = [""]*len(unmasked_frames)
        # Init Frames
        self.frames = []
        for i in range(len(unmasked_frames)):
            tmp = FrameInfo(i, unmasked_frames[i], masked_frames[i], json.dumps(metadata[i]))
            tmp.different = self.result["different"][i]
            tmp.attention = self.result["attention"][i]
            tmp.merged = self.result["merged"][i]
            self.frames.append(tmp)
        self.gpt_model = GPT4o()
        self.video_path = video_path
        self.frame_data = frame_data
    
    def save_result(self):
        with open(f"{self.output_path}.json", 'w', encoding='utf-8') as f:
            json.dump(self.result, f)

    def __call__(self):
        # Get overview
        if "overview_caption" not in self.result or self.result["overview_caption"] == "":
            overview = Overview(self.gpt_model, self.frames)
            overview_caption = overview()
            self.result["overview_caption"] = overview_caption
            self.save_result()

        # Get different/attention/merge
        for i in range(len(self.frames)):
            print("="*40, f"Process Frame {i}", "="*40)
            processor = ProcessFrame(self.frames[i], self.frames[i-1] if i!=0 else None, self.gpt_model, i, self.result["overview_caption"])
            self.frames[i] = processor()
            self.result["different"][i] = self.frames[i].different
            self.result["attention"][i] = self.frames[i].attention
            self.result["merged"][i] = self.frames[i].merged
            self.save_result()
        
        # Get scene_hint/scene_description/general caption    
        if "caption" not in self.result or self.result["caption"] == "":
            summary = Summary(self.gpt_model, self.result["merged"], self.result["attention"], self.video_path, self.frame_data, self.result["overview_caption"])
            split_scene, caption = summary()
            self.result["scene_list"] = split_scene
            self.result["caption"] = caption
            self.save_result()
            
        # Get scene_qa/general_qa
        if "general_qa" not in self.result or self.result["general_qa"] == {}:
            questioner = Question(self.gpt_model, self.result["scene_list"], self.result["caption"])
            scene_list_wqa, general_qa = questioner()
            self.result["scene_list"] = scene_list_wqa
            self.result["general_qa"] = general_qa
            self.save_result()
            