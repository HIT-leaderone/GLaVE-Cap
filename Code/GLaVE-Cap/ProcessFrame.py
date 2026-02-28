from prompts import prompt_different, prompt_attention, prompt_merge
from FrameInfo import FrameInfo
import re

class ProcessFrame:
    def __init__(self, current: FrameInfo, previous: FrameInfo, gpt_model, ID, overiview_caption):
        self.current = current
        self.previous = previous
        self.gpt_model = gpt_model
        self.ID = ID
        self.overiview_caption = overiview_caption
        
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
        print(response)
        return response
    
    def get_different(self):
        print("-"*40,f"[Info] Task: get_different","-"*40)
        content = []
        content.append({"type": "text", "text": f"Current Frame ID: {self.ID}\n"})
        content.append({"type": "text", "text": f"Overview caption: {self.overiview_caption}\n"})
        content.append({"type": "text", "text": f"First Video frame: "})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.previous.masked_base64}"}})
        content.append({"type": "text", "text": f"First JSON: {self.previous.metadata}\n"})
        content.append({"type": "text", "text": f"Second Video frame: "})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.current.masked_base64}"}})
        content.append({"type": "text", "text": f"Second JSON: {self.current.metadata}"})
        different = self.get_response(prompt_different, content)
        return different

    def get_attention(self):
        print("-"*40,f"[Info] Task: get_attention","-"*40)
        content = []
        content.append({"type": "text", "text": f"Current Frame ID: {self.ID}\n"})
        content.append({"type": "text", "text": f"Overview caption: {self.overiview_caption}\n"})
        content.append({"type": "text", "text": "Image:"})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.current.unmasked_base64}"}})
        content.append({"type": "text", "text": "Edited Image:"})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.current.masked_base64}"}})
        content.append({"type": "text", "text": f"JSON: {self.current.metadata}"})
        attention = self.get_response(prompt_attention, content)
        return attention
    
    def merge(self):
        print("-"*40,f"[Info] Task: merge","-"*40)
        content = []
        content.append({"type": "text", "text": f"Current Frame ID: {self.ID}\n"})
        content.append({"type": "text", "text": f"Overview caption: {self.overiview_caption}\n"})
        content.append({"type": "text", "text": f"Differential Caption: {self.current.different}\n"})
        content.append({"type": "text", "text": f"Supplementary Material: {self.current.attention}\n"})
        merged = self.get_response(prompt_merge, content)
        return merged
    
    def __call__(self):
        if self.previous == None:
            if self.current.attention == "": self.current.attention = self.get_attention()
            if self.current.different == "": self.current.different = self.current.attention
            if self.current.merged == "": self.current.merged = self.current.attention
        else:
            if self.current.different == "": self.current.different = self.get_different()
            if self.current.attention == "": self.current.attention = self.get_attention()
            if self.current.merged == "": self.current.merged = self.merge()
        return self.current



    