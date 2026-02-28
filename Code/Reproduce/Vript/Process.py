import cv2
import os
import base64
import json

from utils.ResultManager import ResultManager
from scenedetect import SceneManager, open_video, ContentDetector, split_video_ffmpeg


class ProcessVript:
    def __init__(self, video_file: str, result_file: str, gpt_model):
        self.video_file = video_file
        self.result = ResultManager(result_file, "Vript pipeline")
        self.gpt_model = gpt_model

    def get_info(self):
        cap = cv2.VideoCapture(self.video_file)
        self.frame_rate = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_count = frame_count
        self.duration = frame_count / self.frame_rate if self.frame_rate > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"#frame={frame_count}, fps={self.frame_rate}, duration={self.duration}, size={width}x{height}")

    def split_scene(self):
        video = open_video(self.video_file)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()
        
        frame_ranges = [(start.get_frames(), end.get_frames()) for start, end in scene_list]
        return frame_ranges

    def sample_frames(self, start: int, end: int):
        cap = cv2.VideoCapture(self.video_file)
        total_frames = end - start
        duration_time = total_frames / self.frame_rate
        if duration_time < 6:
            sample_points = [0.2, 0.5, 0.8]
        elif duration_time < 30:
            sample_points = [0.15, 0.4, 0.6, 0.85]
        else:
            sample_points = [0.15, 0.3, 0.5, 0.7, 0.85]

        sample_indices = [start + int(p * total_frames) for p in sample_points]
        print(f"Sampled frames: {sample_indices}")
        sample_frames = []
        for frame_idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            _, buffer = cv2.imencode(".png", frame)
            frame_base64 = base64.b64encode(buffer).decode("utf-8")
            sample_frames.append(frame_base64)
        cap.release()
        return sample_frames


    def get_caption(self, scenes):
        title_instruction = ""

        content = []
        voiceover_instruction = ""
        voiceover_text = ""
        for scene_img in scenes:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{scene_img}"}})
        content.append({"type": "text", "text": f"""\
Based on the {voiceover_instruction}successive frames {title_instruction}above, please describe:
1) the shot type (15 words)
2) the camera movement (15 words)
3) what is happening as detailed as possible (e.g. plots, characters' actions, environment, light, all objects, what they look like, colors, etc.) (150 words)   
4) Summarize the content to title the scene (10 words)
Directly return in the json format like this:
{{"shot_type": "...", "camera_movement": "...", "content": "...", "scene_title": "..."}}. Do not describe the frames individually but the whole clip.
"""})
        messages = [
            {
                "role": "system",
                "content": "You are an excellent video director that can help me analyze the given video clip."
            },
            {
                "role": "user",
                "content": content
            }
        ]
        for retry in range(5):
            try:
                ret = self.gpt_model.send_stable_request(messages)
                ret_json = json.loads(ret[ret.find('{'):ret.rfind('}') + 1])
                break
            except:
                print(f"[Error] Error Parse: {ret}, retry {retry}")
                
        print(ret_json)            
        return ret_json

    def __call__(self):
        if self.result.has("caption"):
            # print(self.result.get('caption'))
            print("Cached")
            return
        # Get basic info
        self.get_info()
        # Split scenes
        scenes = []
        scenes = self.split_scene()
        if len(scenes) == 0:
            scenes.append([0, self.frame_count])
        print(scenes)
        # Get captions
        captions = []
        cnt_sample_frames = 0
        for idx, (start, end) in enumerate(scenes):
            print('-' * 80)
            print(f"Scene {idx}: ranging {start} - {end}")
            frames = self.sample_frames(start, end)
            caption = self.get_caption(frames)
            captions.append(caption)
            cnt_sample_frames += len(frames)

        output = []
        for idx, scene in enumerate(scenes):
            start_time, end_time = scene
            start_time /= self.frame_rate
            end_time /= self.frame_rate
            print(captions[idx])
            caption = f"[Scene {idx+1}/{len(scenes)}: {captions[idx]['scene_title']}](Duration: [{start_time:.1f}, {end_time:.1f}]/{self.duration:.1f}s)\n"
            caption += captions[idx]['content'] + "\n"
            output.append(caption)

        final_caption = "\n".join(output)
        self.result.set("caption", final_caption)
        self.result.set("#sample_frames", cnt_sample_frames)
        self.result.set('#prompt_tokens', self.gpt_model.prompt_tokens)
        self.result.set('#completion_tokens', self.gpt_model.completion_tokens)
