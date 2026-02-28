import os
import cv2
from torch.nn import functional as F
import math
from transformers import CLIPFeatureExtractor,CLIPVisionModel
import numpy as np
import json
import requests

requests.packages.urllib3.disable_warnings()
requests.session().verify = False

EPS = 1e-8

model_path = 'openai/clip-vit-large-patch14-336'
feature_extractor = CLIPFeatureExtractor.from_pretrained(model_path)
vision_tower = CLIPVisionModel.from_pretrained(model_path).cuda()
vision_tower.requires_grad_(False)


def get_resized_wh(width, height, max_size):
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
    else:
        new_width = width
        new_height = height
    return new_width, new_height

def check_pure(mtx):
    unique_elements = np.unique(mtx)
    return len(unique_elements) == 1

def calculate_clip_feature_sim_2(image_1, image_2):
    input_1 = feature_extractor(images=image_1, return_tensors="pt")
    input_2 = feature_extractor(images=image_2, return_tensors="pt")
    image_feature_1 = vision_tower(**input_1.to(device=vision_tower.device), output_hidden_states=True).hidden_states[-1][:, 0]
    image_feature_2 = vision_tower(**input_2.to(device=vision_tower.device), output_hidden_states=True).hidden_states[-1][:, 0]
    similarity = F.cosine_similarity(image_feature_1.to(device='cpu'), image_feature_2.to(device='cpu'), dim=1)
    # print(f'Sim: {similarity}')
    return similarity

def frame_interval_file(video_path, keyframe_interval, keyframe_interval_sam, shortest_duration, longest_duration, window_threshold, output_dir1, output_dir2):    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = math.ceil(video_fps * keyframe_interval - EPS)
    frame_interval_sam = math.ceil(video_fps * keyframe_interval_sam -EPS)
    frame_list = []
    time_project = []
    cnt_tmp = 0
    tot_idx = -1
    tot_pure = 0
    while cap.isOpened():
        ret, frame = cap.read()
        tot_idx += 1
        if not ret:
            break
        if cnt_tmp / video_fps > longest_duration:
            break
        if cnt_tmp == 0 and check_pure(frame) == True:
            pure_cnt = 1
            while pure_cnt < frame_interval:
                ret, frame = cap.read()
                tot_pure += 1
                tot_idx += 1
                if check_pure(frame) != True:
                    break
                pure_cnt += 1
        frame_list.append(frame)
        time_project.append(tot_idx)
        cnt_tmp += 1        
    print(f"tot_frame={tot_idx}, pure={tot_pure}, fps={video_fps}")
    print(f"frame_list={len(frame_list) / frame_interval}")
    start_frame_idx = 0
    selected_frame_list = [0]
    selected_time_list = [0]
    interval_frame = [0]
    if len(frame_list) > frame_interval:
        for i in range(1, len(frame_list)):
            if i % frame_interval_sam == 0:
                interval_frame.append(i)
            if i % frame_interval == 0:
                if i % frame_interval_sam != 0:
                    interval_frame.append(i)
                dynamic_sim = calculate_clip_feature_sim_2(frame_list[start_frame_idx], frame_list[i])
                if dynamic_sim < window_threshold:
                    selected_frame_list.append(len(interval_frame) - 1)
                    selected_time_list.append(time_project[interval_frame[-1]])
                    # print(i, interval_frame[-1])
                    start_frame_idx = i
    if len(selected_frame_list) == 1:
        interval_frame.append(len(frame_list)-1)
        selected_frame_list.append(len(interval_frame)-1)
        selected_time_list.append(time_project[-1])
    elif (len(frame_list)-selected_frame_list[-1]) >= frame_interval:
        interval_frame.append(len(frame_list)-1)
        selected_frame_list.append(len(interval_frame)-1)
        selected_time_list.append(time_project[-1])
    cnt_frame = 0
    for fc in interval_frame:
        time_str = f"{cnt_frame}"
        # print("time_str = ",time_str ,current_time)
        cnt_frame += 1
        frame_filename = f"{time_str}.jpg"
        # frame_filename = f"{time_str}.j[h]"
        frame_filename = os.path.join(output_dir1, frame_filename)
        os.makedirs(output_dir1, exist_ok=True)
        new_width, new_height = get_resized_wh(width, height, 1024)
        if new_width == width and new_height == height:
            pass
        else:
            frame_list[fc] = cv2.resize(frame_list[fc], (new_width, new_height), interpolation=cv2.INTER_AREA)
        suc = cv2.imwrite(frame_filename, frame_list[fc])
        if not suc:
            print(f"Failed to save frame {time_str} to {frame_filename}.")

    cnt_frame = 0
    for fc2 in selected_frame_list:
        fc = interval_frame[fc2]
        time_str = f"{cnt_frame}"
        # print("time_str = ",time_str ,current_time)
        cnt_frame += 1
        frame_filename = f"{time_str}.jpg"
        # frame_filename = f"{time_str}.j[h]"
        frame_filename = os.path.join(output_dir2, frame_filename)
        os.makedirs(output_dir2, exist_ok=True)
        new_width, new_height = get_resized_wh(width, height, 1024)
        if new_width == width and new_height == height:
            pass
        else:
            frame_list[fc] = cv2.resize(frame_list[fc], (new_width, new_height), interpolation=cv2.INTER_AREA)
        suc = cv2.imwrite(frame_filename, frame_list[fc])
        if not suc:
            print(f"Failed to save frame {time_str} to {frame_filename}.")

    with open(f'{output_dir2}/key_list.json', 'w') as f:
        json.dump(selected_frame_list, f)
    with open(f'{output_dir2}/frameid_list.json', 'w') as f:
        json.dump({"FPS":video_fps, "frame_list":selected_time_list}, f)
    cap.release()

def keyframe(keyframe_interval, video_name, video_base, sam_base, key_base):
    keyframe_interval_sam = 0.5
    shortest_duration = 0
    longest_duration = 180
    window_threshold = 0.93
    print(f"Found file Exact Key Frame: {video_name}")
    video_path = os.path.join(video_base, video_name)
    output_dir1 = os.path.join(sam_base, video_name.split(".")[0])
    output_dir2 = os.path.join(key_base, video_name.split(".")[0])
    if not os.path.exists(output_dir1): os.makedirs(output_dir1)
    if not os.path.exists(output_dir2): os.makedirs(output_dir2)
    frame_interval_file(video_path, keyframe_interval, keyframe_interval_sam, shortest_duration, longest_duration, window_threshold, output_dir1, output_dir2)
