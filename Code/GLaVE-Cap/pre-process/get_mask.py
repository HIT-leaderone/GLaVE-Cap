import os
import cv2
import torch
import numpy as np
import supervision as sv
from PIL import Image
from sam2.build_sam import build_sam2_video_predictor, build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection 
from utils.track_utils import sample_points_from_masks
from utils.video_utils import create_video_from_images
from utils.common_utils import CommonUtils
from utils.mask_dictionary_model import MaskDictionaryModel, ObjectInfo
import json
import copy

class MaskModel:
    def __init__(self):
        # use bfloat16 for the entire notebook
        torch.autocast(device_type="cuda", dtype=torch.bfloat16).__enter__()
        if torch.cuda.get_device_properties(0).major >= 8:
            # turn on tfloat32 for Ampere GPUs (https://pytorch.org/docs/stable/notes/cuda.html#tensorfloat-32-tf32-on-ampere-devices)
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        # init sam image predictor and video predictor model
        sam2_checkpoint = "./checkpoints/sam2.1_hiera_large.pt"
        model_cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("device", self.device)

        self.video_predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)
        sam2_image_model = build_sam2(model_cfg, sam2_checkpoint, device=self.device)
        self.image_predictor = SAM2ImagePredictor(sam2_image_model)

        # init grounding dino model from huggingface
        model_id = "IDEA-Research/grounding-dino-base"
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.grounding_model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(self.device)
        
        # VERY important: text queries need to be lowercased + end with a dot
        self.text = "person . animal . vehicle . robot . bird . cat . dog . horse . sheep . cow . elephant . bear . zebra . giraffe . bicycle . car . motorcycle . airplane . bus . train . truck . boat . airplane . motorbike ."

    def process(self, video_dir, output_dir):
        mask_data_dir = os.path.join(output_dir, "mask_data")
        json_data_dir = os.path.join(output_dir, "json_data")
        result_dir = os.path.join(output_dir, "result")
        CommonUtils.creat_dirs(mask_data_dir)
        CommonUtils.creat_dirs(json_data_dir)
        # scan all the JPEG frame names in this directory
        frame_names = [
            p for p in os.listdir(video_dir)
            if os.path.splitext(p)[-1] in [".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG"]
        ]

        frame_names.sort(key=lambda p: int(os.path.splitext(p)[0]))

        # init video predictor state
        print("video_dir=", video_dir)
        inference_state = self.video_predictor.init_state(video_path=video_dir)
        step = 1 # the step to sample frames for Grounding DINO predictor

        sam2_masks = MaskDictionaryModel()
        PROMPT_TYPE_FOR_VIDEO = "mask" # box, mask or point
        objects_count = 0
        frame_object_count = {}
        """
        Step 2: Prompt Grounding DINO and SAM image predictor to get the box and mask for all frames
        """
        print("Total frames:", len(frame_names))
        for start_frame_idx in range(0, len(frame_names), step):
        # prompt grounding dino to get the box coordinates on specific frame
            print("start_frame_idx", start_frame_idx)
            # continue
            img_path = os.path.join(video_dir, frame_names[start_frame_idx])
            image = Image.open(img_path).convert("RGB")
            # print("finish load image")
            image_base_name = frame_names[start_frame_idx].split(".")[0]
            mask_dict = MaskDictionaryModel(promote_type = PROMPT_TYPE_FOR_VIDEO, mask_name = f"mask_{image_base_name}.npy")
            # print("finish add mask_dict")
            # run Grounding DINO on the image
            inputs = self.processor(images=image, text=self.text, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.grounding_model(**inputs)
            results = self.processor.post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                box_threshold=0.25,
                text_threshold=0.25,
                target_sizes=[image.size[::-1]]
            )
            # print("finish grounding dino")
            # prompt SAM image predictor to get the mask for the object
            self.image_predictor.set_image(np.array(image.convert("RGB")))
            # print("finish sam2")
            # process the detection results
            input_boxes = results[0]["boxes"] # .cpu().numpy()
            # print("results[0]",results[0])
            OBJECTS = results[0]["labels"]
            if input_boxes.shape[0] != 0:
                # prompt SAM 2 image predictor to get the mask for the object
                masks, scores, logits = self.image_predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    box=input_boxes,
                    multimask_output=False,
                )
                # convert the mask shape to (n, H, W)
                if masks.ndim == 2:
                    masks = masks[None]
                    scores = scores[None]
                    logits = logits[None]
                elif masks.ndim == 4:
                    masks = masks.squeeze(1)
                """
                Step 3: Register each object's positive points to video predictor
                """

                # If you are using point prompts, we uniformly sample positive points based on the mask
                if mask_dict.promote_type == "mask":
                    mask_dict.add_new_frame_annotation(mask_list=torch.tensor(masks).to(self.device), box_list=torch.tensor(input_boxes), label_list=OBJECTS)
                else:
                    raise NotImplementedError("SAM 2 video predictor only support mask prompts")
            else:
                print("No object detected in the frame, skip merge the frame merge {}".format(frame_names[start_frame_idx]))
                mask_dict = sam2_masks

            """
            Step 4: Propagate the video predictor to get the segmentation results for each frame
            """
            objects_count = mask_dict.update_masks(tracking_annotation_dict=sam2_masks, iou_threshold=0.8, objects_count=objects_count)
            frame_object_count[start_frame_idx] = objects_count
            print("objects_count", objects_count)
            
            if len(mask_dict.labels) == 0:
                mask_dict.save_empty_mask_and_json(mask_data_dir, json_data_dir, image_name_list = frame_names[start_frame_idx:start_frame_idx+step])
                print("No object detected in the frame, skip the frame {}".format(start_frame_idx))
                continue
            else:
                self.video_predictor.reset_state(inference_state)

                for object_id, object_info in mask_dict.labels.items():
                    frame_idx, out_obj_ids, out_mask_logits = self.video_predictor.add_new_mask(
                            inference_state,
                            start_frame_idx,
                            object_id,
                            object_info.mask,
                        )
                video_segments = {}  # output the following {step} frames tracking masks
                for out_frame_idx, out_obj_ids, out_mask_logits in self.video_predictor.propagate_in_video(inference_state, max_frame_num_to_track=step, start_frame_idx=start_frame_idx):
                    frame_masks = MaskDictionaryModel()
                    
                    for i, out_obj_id in enumerate(out_obj_ids):
                        out_mask = (out_mask_logits[i] > 0.0) # .cpu().numpy()
                        object_info = ObjectInfo(instance_id = out_obj_id, mask = out_mask[0], class_name = mask_dict.get_target_class_name(out_obj_id), logit=mask_dict.get_target_logit(out_obj_id))
                        object_info.update_box()
                        frame_masks.labels[out_obj_id] = object_info
                        image_base_name = frame_names[out_frame_idx].split(".")[0]
                        frame_masks.mask_name = f"mask_{image_base_name}.npy"
                        frame_masks.mask_height = out_mask.shape[-2]
                        frame_masks.mask_width = out_mask.shape[-1]

                    video_segments[out_frame_idx] = frame_masks
                    sam2_masks = copy.deepcopy(frame_masks)

                print("video_segments:", len(video_segments))
            """
            Step 5: save the tracking masks and json files
            """
            for frame_idx, frame_masks_info in video_segments.items():
                mask = frame_masks_info.labels
                mask_img = torch.zeros(frame_masks_info.mask_height, frame_masks_info.mask_width)
                for obj_id, obj_info in mask.items():
                    mask_img[obj_info.mask == True] = obj_id
                # print(f"Saving {frame_idx}, name={frame_masks_info.mask_name}, #mask = {len(frame_masks_info.labels)}")
                mask_img = mask_img.numpy().astype(np.uint16)
                np.save(os.path.join(mask_data_dir, frame_masks_info.mask_name), mask_img)

                json_data_path = os.path.join(json_data_dir, frame_masks_info.mask_name.replace(".npy", ".json"))
                frame_masks_info.to_json(json_data_path)
            


if __name__ == "__main__":
    model = MaskModel()