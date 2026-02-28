# Supplementary Materials for GLaVE-Cap: Global-Local Aligned Video Captioning with Vision Expert Integration

This supplementary material contains three main components: `code`, `GLaVE-Bench`, and `GLaVE-1.2M`.

## 1. Code/

This directory includes all code necessary for reproducing our results and conducting evaluation. It contains:

#### **GLaVE-Cap/**: 

Our proposed framework for generating fine-grained video captions.

#### **Evaluation/**: 

Scripts for evaluating the captioning outputs.

#### **Reproduce/** 

Reproductions of representative video captioning methods used for comparison in our experiments.

**Please refer to `Code/README.md` for a quick environment install and quick start.**



## 2. GLaVE-Bench/

This directory provides the benchmark data, including:

- **Annotations**: All manually curated reference captions for evaluation.
- **Annotation Guidelines**: Instructions followed by annotators during the labeling process.

> Note: The annotation guidelines and annotations are originally in Chinese, as the annotators were not proficient in English. We also provide English versions of both (files suffixed with `_eng`). Due to the license restrictions of Video-MME, we are not permitted to redistribute the original videos. Please visit [Video-MME](https://huggingface.co/datasets/lmms-lab/Video-MME) to access the original videos.



Our benchmark dataset supports the evaluation of fine-grained video understanding. Most questions are linked to a specific scene (`scene: -1` denotes the global question-option that assesses holistic comprehension and reasoning) and annotated with a question type (e.g., object direction, attribute change). Scene hints are provided via `scene_hint` to specify the scene and reduce ambiguity.  The structured question-answer pairs are stored in `qa` to facilitate a comprehensive evaluation of caption quality or model performance. **The Data Format of the annotations is as follows:**

```
[video_id].json
├── scene_hint # Scene hints that specify the scene and reduce ambiguity.
│   ├── "0": "A title screen introducing the topic."
│   ├── "1": "The introduction of the smoke signal."
│   └── ...
├── qa
│   ├── "0ay2Qy3wBe8_0" # Question ID format: [video_name]_[question_number]
│   │   ├── id: "0ay2Qy3wBe8_0"
│   │   ├── scene: 0 # Corresponding scene ID
│   │   ├── dimension: "Object Direction" # Type of the question
│   │   ├── question: "Where is the arrow pointing relative to the title?"
│   │   ├── options:
│   │   │   ├── "A. The arrow is pointing away from the title."
│   │   │   ├── "B. The arrow is pointing toward the title."
│   │   │   ├── "C. The arrow is pointing to the left of the title."
│   │   │   └── "D. The arrow is pointing below the title."
│   │   └── answer: "B"
│   ├── "0ay2Qy3wBe8_1"
│   │   ├── id: "0ay2Qy3wBe8_1"
│   │   ├── scene: 0
│   │   ├── dimension: "Attribute Change"
│   │   ├── question: "What is the aesthetic of the new frame after the backdrop transition?"
│   │   ├── options:
│   │   │   ├── "A. The new frame has a minimalist aesthetic."
│   │   │   ├── "B. The new frame has a futuristic aesthetic."
│   │   │   ├── "C. The new frame has a retro aesthetic."
│   │   │   └── "D. The new frame has a grunge aesthetic."
│   │   └── answer: "C"
│   └── ...
```



## 3. GLaVE-1.2M/

This directory contains 12 samples from GLaVE-1.2M. Each sample includes a video, its caption, and corresponding question-answer pairs.

To facilitate broader and more effective use of our dataset within the research community, we retain all outputs generated during the annotation pipeline. This includes local captions that capture frame-level details (`different`, `attention`, `merged`), high-level summaries (`overview_caption`), detailed scene/video level captions (`scene_list.caption`, `caption`), and both local and global multiple-choice question-answer pairs (`scene_list.QA_pair`, `general_qa`). **The Data Format of the annotations is as follows:**

```
├── different # The differential captions highlighting changes between two adjacent frames
│   └── ...
├── attention # The detailed caption with detailed descriptions of key elements
│   └── ...
├── merged # Merged local captions combining multiple perspectives
│   └── ...
├── overview_caption # A high-level summary caption describing the overall video content
│   └── The video is an introductory tutorial for beginner pilots...
├── scene_list
│   ├── "0" # Scene ID
│   │   ├── frame_range: [0,1] # Frame index range representing the scene interval
│   │   ├── scene_hint: "Brand Logo Introduction" # Scene hints that specify the scene and reduce ambiguity.
│   │   ├── caption: "The video begins with a completely black screen..." # The detailed scene-level caption
│   │   └── QA_pair # Scene-level multiple-choice questions designed to test fine-grained understanding of individual scenes
│   │       ├── "0"
│   │       │   ├── Question: "Where does the major scene of the video take place in the beginning?"
│   │       │   ├── Answer: "The major scene of the video takes place on a completely black screen."
│   │       │   ├── Dimension: "Description-Scene" # Type of the question
│   │       │   ├── Options
│   │       │   │   ├── "A. The major scene of the video takes place in a brightly lit room in the beginning."
│   │       │   │   ├── "B. The major scene of the video takes place on a colorful background in the beginning."
│   │       │   │   ├── "C. The major scene of the video takes place on a completely black screen in the beginning."
│   │       │   │   └── "D. The major scene of the video takes place outdoors in the beginning."
│   │       │   └── Answer_choices: "C"
│   │       └── ...
│   └── ...
├── general_qa # Video-level multiple-choice questions aimed at holistic comprehension and reasoning across the entire video. The format is similar to the scene-level question-options pairs.
│   ├── "0"
│   │   ├── Question: "What happens after the 'DJI' logo is introduced on the black screen?"
│   │   ├── Answer: "The video transitions to a minimalist scene with a pure white background and a central disclaimer."
│   │   ├── Dimension: "Temporal"
│   │   ├── Options
│   │   │   ├── "A. The video transitions to a minimalist scene with a pure white background and a central disclaimer."
│   │   │   ├── "B. The video shows a detailed layout of the Phantom 3 Standard drone against an outdoor setting."
│   │   │   ├── "C. The video cuts to a vibrant scene featuring the presenter in front of a blue background."
│   │   │   └── "D. The video displays a promotional clip of the DJI store website."
│   │   └── Answer_choices: "A"
│   └── ...
├── caption # The video caption
│   └── The video begins with a completely black screen
```



**Note that: All data and code are provided strictly for academic and non-commercial use. Please contact the authors if further clarification or permissions are needed.**
