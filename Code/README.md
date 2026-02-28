#### Video Process

Our proposed framework for generating keyframes and masked keyframes from video.

**Quick Install**:

```
# need to prepare video in code/GLaVE-Cap/data/video
cd code/GLaVE-Cap
conda create -n pre-process python=3.10
conda activate pre-process
git clone git@github.com:IDEA-Research/Grounded-SAM-2.git
cp ./pre-process/* ./Grounded-SAM-2/
cd Grounded-SAM-2
cd checkpoints
bash download_ckpts.sh
cd ..
conda install pytorch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 pytorch-cuda=12.4 -c pytorch -c nvidia

# install SAM-2
pip install -e .

# install Grounding Dino, please refer to the official repository (https://github.com/IDEA-Research/GroundingDINO) if you encounter difficulties.
export LD_LIBRARY_PATH=/path/to/pre-process/lib/python3.10/site-packages/torch/lib:$LD_LIBRARY_PATH
export CUDA_HOME=/path/to/cuda-12.4/
pip install --no-build-isolation -e grounding_dino

pip install transformers pyparsing six opencv-python supervision
```

**Quick Start**:

```
python main.py 0 1
```



#### **GLaVE-Cap**: 

Our proposed framework for generating fine-grained video captions.

**Quick Install**:

```
# need to run video process and prepare api_key in code/GLaVE-Cap/gpt_model.py
cd code/GLaVE-Cap
conda create -n GLaVE-Cap python=3.12
conda activate GLaVE-Cap
pip install openai pyyaml
pip install scenedetect[opencv] --upgrade
```

**Quick Start**:

```
python main.py --config GLaVE-Cap --range 0 1
```



#### Evaluation

The evaluation code we use.

**Quick Install**:

```
# need to prepare qa files and api_key in code/Evaluation/utils/GPTModel.py
conda create -n eval python=3.10
conda activate eval
pip install openai
```

**Quick Start**:

```
# need qa_path (such as ./benchmark/annotation)
python eval.py --qa /path/to/annotation
```



#### Reproduce Other Video Methods 

Generating fine-grained video captions via other video-captioning methods (LVD-2M, AuroraCap, ShareGPT4video, LLaVA-Video, Vript). For more reproduction details, please refer to `code/Reproduce/[methods]/README.md`

**Quick Install**:

```
# need to prepare video and api_key in code/Reproduce/utils/GPTModel.py
conda create -n reproduce python=3.10
conda activate reproduce
conda install pytorch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 pytorch-cuda=12.4 -c pytorch -c nvidia
pip install transformers openai opencv-python decord
pip install scenedetect[opencv] --upgrade
```

**Quick Start**:

```
python main.py --input ../GLaVE-Cap/data/video --output ./output --left 0 --right 1 --model gpt4o
```

