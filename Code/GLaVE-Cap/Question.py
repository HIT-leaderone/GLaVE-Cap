import json
import copy
import re
from prompts import system_prompt_question_scene, system_prompt_question_video, usr_prompt_question, system_prompt_options, system_prompt_qarefine

def check_output_format_refine(output):
    try:
        output_list = json.loads(output[output.find("["):output.rfind("]") + 1])
    except json.JSONDecodeError:
        return False, "Invalid JSON format"
    
    result_list = []
    for output_dict in output_list:
        success, output_dict = check_output_format_refine_json(output_dict)
        if success == True:
            result_list.append(output_dict)
        else: 
            print("Error log:",log)
            return False, "JSON ERROR"
    return True, result_list
    
def check_output_format_refine_json(output_dict):
    if "Question" not in output_dict or "Answer" not in output_dict:
        return False, "'Question' or 'Answer' key missing"
    if not isinstance(output_dict["Question"], str) or not isinstance(output_dict["Answer"], str):
        return False, "'Question' and 'Answer' should be a string"
    
    return True, output_dict

def check_output_format(output):
    try:
        output_dict = json.loads(output)
    except json.JSONDecodeError:
        return False, "Invalid JSON format"
    
    if "Options" not in output_dict or "Answer" not in output_dict:
        return False, "'Options' or 'Answer' key missing"
    
    if not isinstance(output_dict["Options"], list) or len(output_dict["Options"]) != 4:
        return False, "'Options' should be a list with 4 items"
    
    for option in output_dict["Options"]:
        if not isinstance(option, str) or not re.match(r"^[A-D]\. .+", option):
            return False, f"Invalid option format: {option}"

    if output_dict["Answer"] not in ["A", "B", "C", "D"]:
        return False, "Answer should be one of 'A', 'B', 'C', or 'D'"
    
    return True, output_dict
        
class Question:
    def __init__(self, gpt_model, scene_list, general_caption):
        self.gpt_model = gpt_model
        self.scene_list = copy.deepcopy(scene_list)
        self.general_caption = general_caption
      
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

    def get_response(self, description, task_type):
        if task_type == "scene":
            Dimension_list = ["Spatial", "Description-Scene", "Description-Human", "Description-Object", "Count", "Binary", "Fine Grained Action", "Object Direction", "Camera Direction", "Camera Shot", "Speed", "Attribute Change", "Visual-cue"]
            system_prompt = system_prompt_question_scene
        elif task_type == "video":
            Dimension_list = ["Temporal", "Plot Understanding", "Time Order", "Causal"]
            system_prompt = system_prompt_question_video
        content = [{"type": "text", "text": usr_prompt_question.format(caption = description)}]
        message = self.get_message(system_prompt, content)
        
        for i in range(20):
            try:
                print(f"QA generation try {i}")
                response = self.gpt_model.send_stable_request(message)
                print("response =", response[response.find("{"):response.rfind("}") + 1])
                QA_dict = json.loads(response[response.find("{"):response.rfind("}") + 1])
                QA_keys = ["Dimension", "Question", "Answer"]
                for id, QA_data in QA_dict.items():
                    missing_keys = [key for key in QA_keys if key not in QA_data]
                    if missing_keys:
                        raise KeyError(f"Keys {missing_keys} not found in dictionary.")
                    if QA_data["Dimension"] not in Dimension_list:
                        raise ValueError(f"Invalid Dimension values found: {QA_data["Dimension"]}.")  
                return QA_dict
            except Exception as e:
                print(f"QA generation error: {e}")
                continue
        return response
    
    def generate_option(self, QA_pair, caption):
        for id, QA_data in QA_pair.items():
            input_dict = {"Caption": caption, "Question": QA_data["Question"], "Answer": QA_data["Answer"]}
            input_text = json.dumps(input_dict)
            content = [{"type": "text", "text": input_text}]
            message = self.get_message(system_prompt_options, content)
            for i in range(20):
                options_data = self.gpt_model.send_stable_request(message)
                success, options_data = check_output_format(options_data)
                print("options response=", QA_data["Question"], options_data)
                if success == True: 
                    QA_data["Options"] = options_data["Options"]
                    QA_data["Answer_choices"] = options_data["Answer"]
                    break
                else:
                    print("Error logs:", options_data)
            if "Answer_choices" not in QA_data:
                print(f"options generation error: Max retry")
        print("options QA_pairs", QA_pair)
        return QA_pair
    
    def refine(self, QA_pair):
        result_pair = {}
        tmp_id = 0
        for id, QA_data in QA_pair.items():
            input_dict = {"Question": QA_data["Question"], "Answer": QA_data["Answer"]}
            input_text = json.dumps(input_dict)
            content = [{"type": "text", "text": input_text}]
            message = self.get_message(system_prompt_qarefine, content)
            for i in range(20):
                refine_data = self.gpt_model.send_stable_request(message)
                print("refine_data=", refine_data)
                if refine_data == "None": break
                success, refine_data = check_output_format_refine(refine_data)
                print("refine response=", QA_data["Question"], refine_data)
                if success == True: 
                    for qa_pair in refine_data:
                        result_pair[tmp_id] = qa_pair
                        result_pair[tmp_id]["Dimension"] = QA_data["Dimension"]
                        tmp_id += 1
                    break
                else:
                    print("Error logs:", refine_data)
        print("refine QA_pairs", result_pair)
        return result_pair
    
    def __call__(self): 
        for scene_id, scene_data in self.scene_list.items():
            caption = scene_data["caption"]
            scene_data["QA_pair"] = self.get_response(caption, "scene")
            scene_data["QA_pair"] = self.refine(scene_data["QA_pair"])
            scene_data["QA_pair"] = self.generate_option(scene_data["QA_pair"], caption)
        general_qa = self.get_response(self.general_caption, "video")
        general_qa = self.refine(general_qa)
        general_qa = self.generate_option(general_qa, caption)
        print("-"*20, f"Finish Caption", "-"*20)
        print(general_qa)
        return self.scene_list, general_qa   