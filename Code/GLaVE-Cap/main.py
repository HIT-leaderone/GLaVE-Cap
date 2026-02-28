import os
import json
import argparse
import sys
from datetime import datetime
import yaml
import argparse
from ProcessVideo import ProcessVideo
def get_subdirectories(directory):
    subdirectories = []
    for dir in os.listdir(directory):
        subdirectories.append(os.path.join(directory, dir))
    return subdirectories

def load_json_files(folder_path, time_list):
    json_list = []
    json_files = [filename for filename in os.listdir(folder_path) if filename.endswith(".json")]
    json_files.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))
    cnt = 0
    for filename in json_files:
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r') as file:
            original_dict = json.load(file)
            reorganized_dict = {}
            for id, data in original_dict["labels"].items():
                reorganized_dict[id] = {
                    "x1": data["x1"],
                    "y1": data["y1"],
                    "x2": data["x2"],
                    "y2": data["y2"]
                }
            json_list.append(reorganized_dict)
    return json_list
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="captioning")
    parser.add_argument(
        "--config",
        type=str,
        default="paths",
        help="Name of config to read"
    )
    parser.add_argument(
        "--range",
        type=int,
        nargs=2,  # 指定两个整数
        metavar=("START", "END"),  # 参数的占位符名称
        help="Task range [L, R)",
        required=True
    )
    args = parser.parse_args()
    L = int(args.range[0])
    R = int(args.range[1])
    path_config = args.config
    print("[Init] Reading Config:")
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        print(f"   unmasked_videos = {config[path_config]["unmasked_videos"]}")
        print(f"   masked_videos   = {config[path_config]["masked_videos"]}")
        print(f"   output_dir      = {config[path_config]["output_dir"]}")
    print("[Init] Init Paths")
    unmasked_video_dirs_root = get_subdirectories(config[path_config]["unmasked_videos"])
    masked_video_dirs_root = get_subdirectories(config[path_config]["masked_videos"])
    masked_video_dirs_root = sorted(masked_video_dirs_root)
    unmasked_video_dirs = []
    masked_video_dirs = []
    for masked_video_dir in masked_video_dirs_root:
        masked_video_name = masked_video_dir.split("/")[-1]
        masked_video_dirs.append(os.path.join(masked_video_dir, "masked_number"))
        for video_dir in unmasked_video_dirs_root:
            video_name = video_dir.split("/")[-1].split(".")[0]
            if video_name == masked_video_name:            
                unmasked_video_dirs.append(video_dir)   

    print(f"   #unmasked = {len(unmasked_video_dirs)}")
    print(f"   #masked   = {len(masked_video_dirs)}")
    assert(len(unmasked_video_dirs) == len(masked_video_dirs))
    print("[Init] Init Finish")

    print(f"[Init] The task range from [{L}, {R})")
    for i in range(L,min(len(unmasked_video_dirs),R)):
        print("Time:", datetime.now())
        file_name = unmasked_video_dirs[i].split('/')[-1]
        # only support mp4 and mkv
        if os.path.exists(os.path.join(config[path_config]["video_dir"], file_name+".mp4")):
            video_dir = os.path.join(config[path_config]["video_dir"], file_name+".mp4")
        else: video_dir = os.path.join(config[path_config]["video_dir"], file_name+".mkv")
        print("video_dir=",video_dir)
        file_name = file_name.split('.')[0]
        print("#"*100)
        print(f"Running {i}, name = {file_name}")
        print("#"*100)
        with open(f'{unmasked_video_dirs[i]}/key_list.json', 'r') as file:
            time_list = json.load(file)
        with open(f'{unmasked_video_dirs[i]}/frameid_list.json', 'r') as file:
            frame_data = json.load(file)
        directory, _ = os.path.split(masked_video_dirs[i])
        json_data_path = os.path.join(directory, "json_data_modify")
        supp = load_json_files(json_data_path, time_list)
        try:
            processor = ProcessVideo(unmasked_video_dirs[i], masked_video_dirs[i], supp, os.path.join(config[path_config]["output_dir"], file_name), video_dir, frame_data)
            processor()
        except Exception as e:
            print(f"[Error]: {e}")
            print(f"Skipped")
        




