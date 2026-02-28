import os
import argparse

# This is not useless. It's used to prevent the mysterious segmentation fault, caused by import order
from torch.nn import functional as F

from Vript.Process import ProcessVript
from LlavaVideo.Process import ProcessLlavaVideo
from LVD2M.Process import ProcessLVD2M
from ShareGPT4Video.Process import ProcessShareGPT4Video
from AuroraCap.Process import ProcessAuroraCap
from utils.GPTModel import GPT4o, Qwen

def process_video(video_path, output_dir, model):
    video_id = os.path.splitext(os.path.basename(video_path))[0]
    print("#"*80)
    print(f"Processing {video_id}")
    print(f"Input: {video_path}")
    print("#"*80)
    methods = {
        "Vript": ProcessVript,
        "LlavaVideo": ProcessLlavaVideo,
        "LVD-2M": ProcessLVD2M,
        "ShareGPT4Video": ProcessShareGPT4Video,
        "AuroraCap": ProcessAuroraCap,
    }
    
    for method_name, process_class in methods.items():
        print(f"======== {method_name} ========")
        method_output_dir = os.path.join(output_dir, method_name)
        os.makedirs(method_output_dir, exist_ok=True)
        output_file = os.path.join(method_output_dir, f"{video_id}.json")
        
        process_instance = process_class(video_path, output_file, model)
        process_instance()

def main():
    parser = argparse.ArgumentParser(description="Process videos using multiple methods.")
    parser.add_argument("--input", required=True, help="Path to the input directory containing video files.")
    parser.add_argument("--output", required=True, help="Path to the output directory where results will be saved.")
    parser.add_argument("--model", required=True, choices=["gpt4o", "qwen"], help="Model to use for processing (gpt4o or qwen).")
    parser.add_argument("--left", type=int, default=0, help="Left range for video processing.")
    parser.add_argument("--right", type=int, default=0, help="Right range for video processing.")
    args = parser.parse_args()

    # Select the appropriate model
    if args.model == "gpt4o":
        model = GPT4o()
    elif args.model == "qwen":
        model = Qwen()
    else:
        print(f"Error: Unsupported model '{args.model}' selected.")
        return
    
    input_dir = args.input
    output_dir = args.output
    
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    video_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    if not video_files:
        print("No video files found in the input directory.")
        return
    L = args.left
    R = args.right if args.right < len(video_files) else len(video_files)
    for i in range(L, R):
        video_file = video_files[i]
    # for video_file in video_files:
        try:
            video_path = os.path.join(input_dir, video_file)
            process_video(video_path, output_dir, model)
        except Exception as e:
            print(f"Error: {e}")
            print("Skipped")


if __name__ == "__main__":
    main()
