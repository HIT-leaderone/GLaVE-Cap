import sys
import os
import cv2
import datetime
from get_mask import MaskModel
from keyframe import keyframe
from edge_id import process_id

def solve(model, video_dir, output_dir):
    model.process(video_dir, output_dir)

def get_subdirectories(directory):
    subdirectories = []
    for dir in os.listdir(directory):
        subdirectories.append(os.path.join(directory, dir))
    subdirectories = sorted(subdirectories)
    return subdirectories

if __name__ == "__main__":
    args = sys.argv
    L = int(args[1])
    R = int(args[2])

    print("Init Paths")
    video_base = "../data/video"
    output_dir_prefix = "../data"
    sam_base = output_dir_prefix + "/sam_dir"
    key_base = output_dir_prefix + "/key_dir"
    annotation_base = output_dir_prefix + "/annotation"
    video_dirs = get_subdirectories(video_base)
    print(f"#videos = {len(video_dirs)}")
    print(f"The task range from [{L},{R})")
    print(f"Init Model")
    model = MaskModel()
    print("Finish")
    for i in range(L,min(len(video_dirs),R)):
        video_dir = video_dirs[i]
        print("#"*100)
        print("TIME=",datetime.datetime.now())
        print(f"runnning {i} video video_dir={video_dir}")
        file_name = video_dir.split('/')[-1]
        file_name_clear = file_name.split('.')[0]
        output_dir = os.path.join(output_dir_prefix, file_name)
        keyframe(2.0, file_name, video_base, sam_base, key_base)
        print("#"*100)
        print(f"Running SAM, name = {file_name}")
        solve(model, os.path.join(sam_base,file_name_clear), os.path.join(annotation_base,file_name_clear))
        print("#"*100)
        process_id(file_name_clear, key_base, annotation_base)
        