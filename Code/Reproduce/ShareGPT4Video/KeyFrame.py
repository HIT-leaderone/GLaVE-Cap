import os
from torch.nn import functional as F
import cv2
import math
from transformers import CLIPFeatureExtractor,CLIPVisionModel
import numpy as np
from decord import VideoReader, cpu

class KeyFrame:
    def __init__(self):
        print("Initing Model")
        model_path = 'openai/clip-vit-large-patch14-336'
        self.feature_extractor = CLIPFeatureExtractor.from_pretrained(model_path)
        # print(2)
        self.vision_tower = CLIPVisionModel.from_pretrained(model_path).cuda()
        # print(3)
        self.vision_tower.requires_grad_(False)
        print("Init Finish")


    def check_pure(self, mtx):
        unique_elements = np.unique(mtx)
        return len(unique_elements) == 1

    def calculate_clip_feature_sim_2(self, image_1, image_2):
        input_1 = self.feature_extractor(images=image_1, return_tensors="pt")
        input_2 = self.feature_extractor(images=image_2, return_tensors="pt")
        image_feature_1 = self.vision_tower(**input_1.to(device=self.vision_tower.device), output_hidden_states=True).hidden_states[-1][:, 0]
        image_feature_2 = self.vision_tower(**input_2.to(device=self.vision_tower.device), output_hidden_states=True).hidden_states[-1][:, 0]
        similarity = F.cosine_similarity(image_feature_1.to(device='cpu'), image_feature_2.to(device='cpu'), dim=1)
        # similarity = float(similarity.item())
        # print(f'Sim: {similarity}')
        return similarity

    def extract_keyframe(self, video_path, keyframe_interval = 2, window_threshold = 0.93): 
        video = VideoReader(video_path)   
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_fps = video.get_avg_fps()
        frame_list = []
        cnt_interval = round(keyframe_interval * video_fps)
        selected_frame_idx = []
        for frame_idx in range(len(video)):
            frame = video[frame_idx]
            cv2_frame = cv2.cvtColor(frame.asnumpy(), cv2.COLOR_RGB2BGR)

            if len(selected_frame_idx) == 0: # first frame
                if self.check_pure(cv2_frame):
                    continue
                else:
                    selected_frame_idx.append(frame_idx)
                    print(f"Add {frame_idx}")
                    continue
            if frame_idx == len(video) - 1: # last frame
                if len(selected_frame_idx) == 1 or (frame_idx - last_idx) / video_fps >= keyframe_interval:
                    selected_frame_idx.append(frame_idx)
                    print(f"Add {frame_idx}")                    
                continue

            if (frame_idx - selected_frame_idx[0]) % cnt_interval != 0:
                continue
            last_idx = selected_frame_idx[-1]
            if (frame_idx - last_idx) / video_fps >= keyframe_interval:
                # print(f"calc {last_idx}, {frame_idx}")
                tmp = cv2.cvtColor(video[last_idx].asnumpy(), cv2.COLOR_RGB2BGR)
                dynamic_sim = self.calculate_clip_feature_sim_2(tmp, cv2_frame)
                # print(dynamic_sim, dynamic_sim < 0.95)
                if dynamic_sim < window_threshold:
                    selected_frame_idx.append(frame_idx)
                    print(f"Add {frame_idx}")
            
        return selected_frame_idx


if __name__=="__main__":
    video_path = 'example.mp4'
    keyframe_interval = 2
    # shortest_duration = 10
    # longest_duration = 120
    # window_threshold = 0.93
    keyframe = KeyFrame()
    print(keyframe.extract_keyframe("/hdd/captioning-methods-reproduction/data/6EIrArTyLVU/6EIrArTyLVU.mp4"))
    # output_dir = 'example/'
    # save keyframes to 'output_dir'