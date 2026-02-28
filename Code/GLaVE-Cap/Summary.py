import json
import copy
import re
from scenedetect import detect, ContentDetector
from prompts import system_prompt_scene_split, firsts_clip_system, other_clip_system

def remove_id_tags(text):
    pattern = r'\s?[\(\[\<]ID=\d+[\)\]\>]'
    return re.sub(pattern, '', text)

class Summary:
    def __init__(self, gpt_model, result, result_image, video_path, frame_data, overview_caption):
        self.result = copy.deepcopy(result)
        for i, merge_data in enumerate(self.result):
            self.result[i] = remove_id_tags(merge_data)
        self.video_path = video_path
        self.video_fps = frame_data["FPS"]
        self.image_idx = frame_data["frame_list"]
        self.gpt_model = gpt_model
        self.result_image = result_image
        self.overview_caption = overview_caption
      
    def get_message(self, system_prompt, content):
        message = [
            {
                "role": "system", 
                "content": [{"type": "text", "text": system_prompt}]
            },
            {
                "role": "user",
                "content": content
            }
        ]
        return  message
        
    def get_response(self, system_prompt, content):
        message = self.get_message(system_prompt, content)
        response = self.gpt_model.send_stable_request(message)
        print(response)
        return response
    
    def get_scene_idx_range(self):
        #segment video via PySceneDetect
        raw_scene_list = detect(self.video_path, ContentDetector())
        scene_list = []
        for scene in raw_scene_list:
            scene_list.append([scene[0].get_frames(), scene[1].get_frames()])
        if len(scene_list) == 0: scene_list = [[0, self.image_idx[-1] + 1]]
        print("scene_list=",len(scene_list), scene_list, len(self.image_idx))
        
        # project frame_interval to key_frame idx
        result = {}
        scene_idx = 0
        for start, end in scene_list:
            # print(start, end)
            now_list = []
            for idx, frame in enumerate(self.image_idx):
                if frame >= start and frame < end:
                    now_list.append(idx + 1)
            if now_list == []: continue
            result[scene_idx]=[now_list[0], now_list[-1]]
            scene_idx += 1
        print("auto scene_list=",result)
        return result

    def split_scene(self, st, ed, auto_split):
        print("split scene=", st, ed)
        content = []
        for i, caption in enumerate(self.result_image[st : ed]):
            content.append({"type": "text", "text": f"The {i+1}-th detailed caption: {caption.replace("\n", "")}\n"})
        content.append({"type": "text", "text": f"Automatic scene segmentation result: {json.dumps(auto_split)}"})
        message = self.get_message(system_prompt_scene_split, content)
        for i in range(20):
            try:
                result = {}
                print(f"Split try {i}")
                response = self.gpt_model.send_stable_request(message)
                print(f"response = {response}")
                split_scene = json.loads(response[response.find("{"):response.rfind("}") + 1])
                last_frame_scene = st - 1
                for scene_id, scene_data in split_scene.items():
                    if len(scene_data["frame"]) == 1:
                        scene_data["frame"].append(scene_data["frame"][0])
                    assert(len(scene_data["frame"]) == 2)
                    scene_data["frame"][0] += st - 1
                    scene_data["frame"][1] += st - 1
                    assert(scene_data["frame"][1] < ed)   
                    assert(scene_data["frame"][0] <= scene_data["frame"][1])
                    assert(scene_data["frame"][0] == last_frame_scene + 1)
                    result[scene_id]={"frame_range":[scene_data["frame"][0], scene_data["frame"][1]]}
                    result[scene_id]["scene_hint"] = scene_data["scene_hint"]
                    last_frame_scene = scene_data["frame"][1]
                assert(last_frame_scene == ed - 1)
                print(result)
                return result
            except Exception as e:
                print(f"Scene split error: {e}")
                continue

    def __call__(self): 
        auto_split_scene = self.get_scene_idx_range()
        split_scene = self.split_scene(0, len(self.image_idx), auto_split_scene)
        print("split_scene=", split_scene)
        print("Scene Split finish ", "-" * 40)
        
        previous_caption = ""
        for scene_id, scene_data in split_scene.items():
            print("-"*20, f"scene = {scene_id}, [{scene_data["frame_range"][0]}, {scene_data["frame_range"][1]}]", "-"*20)
            content = []
            if previous_caption != "":
                content.append({"type": "text", "text": f"Current Scene Frame Range : [{scene_data["frame_range"][0]} - {scene_data["frame_range"][1]}]"})
                content.append({"type": "text", "text": f"Overview caption : {self.overview_caption}"})
                time_n = "{:.2f}".format(1.0 * self.image_idx[scene_data["frame_range"][0] - 1] / self.video_fps)
                content.append({"type": "text", "text": f"Previous Scene Descriptions: \n"})
                content.append({"type": "text", "text": previous_caption + '\n'})
            
            for idx in range(scene_data["frame_range"][0], scene_data["frame_range"][1] + 1):
                time_n = "{:.2f}".format(1.0 * self.image_idx[idx] / self.video_fps)
                if idx == 0: 
                    content.append({"type": "text", "text": f"Caption describing {time_n} seconds: {self.result[idx]}\n"})
                    continue
                time_nn = "{:.2f}".format(1.0 * self.image_idx[idx - 1] / self.video_fps)
                content.append({"type": "text", "text": f"Transition caption between {time_nn} seconds and {time_n} seconds: {self.result[idx]}\n"})
            if int(scene_id) == 0: system_prompt = firsts_clip_system
            else: system_prompt = other_clip_system
            response = self.get_response(system_prompt, content).replace("\n", "")

            split_scene[scene_id]["caption"] = response
            previous_caption += response + " "
            previous_caption += '\n'
        print("-"*20, f"Finish Caption", "-"*20)
        print(previous_caption)
        return split_scene, previous_caption   