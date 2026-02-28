import os
import argparse
import json

from Process import ProcessEvaluate

def process_eval(result_path, qa_path, output_path):
    video_id = os.path.splitext(os.path.basename(result_path))[0]
    print("#"*80)
    print(f"Processing {video_id}")
    print(f"Input : {result_path}")
    print(f"QA    : {qa_path}")
    print(f"Output: {output_path}")
    print("#"*80)
    try:
        with open(result_path) as f:
            result = json.load(f)
            caption = result['caption']
        with open(qa_path) as f:
            qa = json.load(f)
    except Exception as e:
        print(f"[Error] Error reading datas: {e}")
        print("Skip this video")
        return
    process_evaluate = ProcessEvaluate(caption, qa, output_path, repeat=3)
    process_evaluate()

    

def main():
    parser = argparse.ArgumentParser(description="Evaluate Captions")
    parser.add_argument("--input", default="../GLaVE-Cap/output", help="Path to caption result dir")
    parser.add_argument("--qa", required=True, help="Path to qa dataset dir")
    parser.add_argument("--output", default="./output", help="Path to the eval result directory where results will be saved.")
    args = parser.parse_args()
    
    input_dir = args.input
    output_dir = args.output
    qa_dir = args.qa
    
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return
    if not os.path.isdir(qa_dir):
        print(f"Error: QA dataset directory '{qa_dir}' does not exist.")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    result_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.json'))]
    
    if not result_files:
        print("No result files found in the input directory.")
        return
    
    for result_file in result_files:
        result_path = os.path.join(input_dir, result_file)
        qa_path = os.path.join(qa_dir, result_file)
        output_path = os.path.join(output_dir, result_file)
        process_eval(result_path, qa_path, output_path)

if __name__ == "__main__":
    main()
