import cv2
import os
import base64
import json
import math
import ast

from utils.ResultManager import ResultManager
from utils.GPTModel import GPT4o

class ProcessEvaluate:
    def __init__(self, caption: str, qa_dataset: dict, result_file: str, optione=True, repeat=1):
        self.caption = caption
        self.scene_hint = qa_dataset['scene_hint']
        self.qa = qa_dataset['qa']
        self.result = ResultManager(result_file, "Evaluate Result")
        self.optione = optione
        self.repeat = repeat
        self.gpt_model = GPT4o()

    def parse(self, response):
        response = response[response.rfind('{'):response.rfind('}')+1]
        try:
            data = ast.literal_eval(response)  # 安全地解析字符串为字典
            if isinstance(data, dict):
                if 'answer' not in data:
                    raise ValueError("No answer")
                ret = data['answer']
                if ret not in ['A', 'B', 'C', 'D', 'E']:
                    raise ValueError(f"unrecognized choice letter {ret}")
                return ret
            else:
                raise ValueError("解析后的数据不是字典")
        except (SyntaxError, ValueError) as e:
            print(f"解析失败: {e}")
        return None

    def Ask(self, question):
        print(question)

        scene_id = int(question['scene'])
        if scene_id != -1:
            system_prompt = """\
# Task
You will be given a detailed description of a video along with a brief description of one specific scene from the video. Your task is to:
1. Comprehend the overall content of the video based on the provided caption.
2. Identify the specific scene referred to in the given scene description. (To assist you, descriptions of the scenes immediately before and after will also be provided.)
3. Answer a multiple-choice question related to the identified scene.

# Constraints
- If the given scene description does not provide enough details to confidently identify a specific scene, or if the caption lacks sufficient information to answer the question, choose the implicit option: "E. Not enough information mentioned".
- Begin by explaining your reasoning—how you located the scene and arrived at your answer.
- Finally, output your answer in the form of a Python dictionary string with the key 'answer' and a value of either 'A', 'B', 'C', 'D', or 'E', such as: {'answer': 'B'}.

# Structured Input
[caption] <full video description>
[pre-scene] <Description of the scene immediately before>  
[scene] <Brief description of the target scene> 
[post-scene] <Description of the scene immediately after>
[question] <question>
[options]
<choice A>
<choice B>
<choice C>
<choice D>\
"""
            scene_hint = self.scene_hint[str(scene_id)]
            if scene_id - 1 < 0:
                scene_before = "No scene before."
            else:
                scene_before = self.scene_hint[str(scene_id - 1)]
            if scene_id + 1 >= len(self.scene_hint):
                scene_after = "No scene after."
            else:
                scene_after = self.scene_hint[str(scene_id + 1)]
            query = ""
            query += f"[caption] {self.caption}\n"
            query += f"[pre-scene] {scene_before}\n"
            query += f"[scene] {scene_hint}\n"
            query += f"[post-scene] {scene_after}\n"
            query += f"[question] {question['question']}\n"
            for option in question['options']:
                query += option + "\n"
            
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}]
                }
            ]
        else:
            if self.optione:
                system_prompt = """\
# Task
You will be given a detailed description of a video. Your task is to:
1. Comprehend the overall content of the video based on the provided caption.
2. Answer a multiple-choice question related to the video.

# Constraints
- If the caption lacks sufficient information to answer the question, choose the implicit option: "E. Not enough information mentioned".
- You should first provide an analysis of how you answered the question.
- Finally, output your answer in the form of a Python dictionary string with the key 'answer' and a value of either 'A', 'B', 'C', 'D', or 'E', such as: {'answer': 'B'}.

# Structured Input
[caption] <full video description>
[question] <question>
[options]
<choice A>
<choice B>
<choice C>
<choice D>\
"""
            else:
                system_prompt = """\
# Task
You will be given a detailed description of a video. Your task is to:
1. Comprehend the overall content of the video based on the provided caption.
2. Answer a multiple-choice question related to the video.

# Constraints
- You should first provide an analysis of how you answered the question.
- Finally, output your answer in the form of a Python dictionary string with the key 'answer' and a value of either 'A', 'B', 'C', or 'D', such as: {'answer': 'B'}.

# Structured Input
[caption] <full video description>
[question] <question>
[options]
<choice A>
<choice B>
<choice C>
<choice D>\
"""
                    
            query = ""
            query += f"[caption] {self.caption}\n"
            query += f"[question] {question['question']}\n"
            for option in question['options']:
                query += option + "\n"
            
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}]
                }
            ]
        
        print("-"*80)
        for retry in range(10):
            response = self.gpt_model.send_stable_request(messages)
            print(response)
            ret = self.parse(response)
            if ret != None:
                return [ret, response]
            print(f"Retry {retry}")
        return None

    def __call__(self):
        print(f"Caption = {self.caption}")

        for (id, data) in self.qa.items():
            if self.result.has(id):
                ans = self.result.get(id)
                log = self.result.get(f"{id}_log")
            else:
                ans = []
                log = []
            if len(ans) == self.repeat:
                continue
            print("="*80)
            print(f"Question Id: {id}")
            tmp = self.repeat - len(ans)
            if tmp < 0:
                tmp = 0
            for i in range(tmp):
                ret, response = self.Ask(data)
                ans.append(ret)
                log.append(response)
                self.result.set(id, ans)
                self.result.set(f"{id}_log", log)
