import json
import copy
from prompts import overview_system
import traceback

class Overview:
    def __init__(self, gpt_model, frame):
        self.gpt_model = gpt_model
        self.frame = frame
      
    def get_response(self, system_prompt, content):
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
        response = self.gpt_model.send_stable_request(message)
        return response 
    
    def __call__(self): 
        print("-"*40,f"[Info] Task: get overview_caption","-"*40)
        content = []
        for i in range(len(self.frame)):
            content.append({"type": "text", "text": f"The {i}-th keyframe:"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.frame[i].unmasked_base64}"}})
        for retry in range(20):
            try:
                print(f"Try {retry}")
                res = self.get_response(system_prompt=overview_system, content=content)
                print("overivew_caption", res)
                return res
            except Exception as e:
                print(f"[Error] {e}")
                traceback.print_exc()
                continue
        raise Exception("Retry Limit Exceeded")

