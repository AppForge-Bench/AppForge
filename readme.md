### 🚀 Prerequisite Environment Setup
There are two ways of building prerequisites of AppForge: Through docker deployment (needs your machine support CPU virtualization) or local emulator (needs to build Android Emulator on your machine). Both options need your machine supports **CPU Virtualization**.

If you are evaluating through docker, check *Docker_Setup*; or you are using local emulator or devices, check *Local_Emulator_Setup* first.

#### 🚀 Docker Setup

##### Docker Environment

Our docker image contains Android docker image from [budtmo/docker-android: Android in docker solution with noVNC supported and video recording](https://github.com/budtmo/docker-android), which requires virtualization as described in https://github.com/budtmo/docker-android?tab=readme-ov-file#quick-start.

In short, our docker image can only be run under ***Ubuntu OS***. If you are using other systems,  you might need to use Virtual Machine that support Virtualization with Ubuntu OS. To check if the virtualization is enabled:

```
sudo apt install cpu-checker
kvm-ok
```

The original repo of Android Docker provides many solutions to different system users.
For Win11 user, you can check https://github.com/budtmo/docker-android?tab=readme-ov-file#wsl2-hardware-acceleration-windows-11-only.
For cloud service user, you can check https://github.com/budtmo/docker-android/blob/master/documentations/USE_CASE_CLOUD.md.

If you encounter unexpected errors with CPU Virtualization, you can also check the issues in the original repo of Android Docker: https://github.com/budtmo/docker-android/issues.

##### Docker Pull & Run

Make sure docker is installed on your device, and run:

```
docker image pull zenithfocuslight/appforge:latest
```
You can check whether you can successfully run the docker image by:
```
docker run --rm -d -p 6080:6080  --device /dev/kvm zenithfocuslight/appforge:latest
```
but you don't have to keep it run when running our code for we'll start a new one.


#### 🚀 Local Emulator Setup

##### Prerequisite

Make sure you have Android Studio and SDK installed on your machine. For users who haven't installed these prerequisites, you can check https://github.com/AppForge-Bench/AppForge/blob/main/documentation/local_emulator.md. However, if you don't have them installed on your machine before and are able to use Ubuntu system with CPU virtualization, we strongly recommend you to use docker environment. 

##### Download Evaluation Files

Download evaluation repo and install dependencies.

```
git pull https://github.com/AppForge-Bench/AppForge_Bench
cd AppForge_Bench
pip install -r requirements.txt

python -m uiautomator2 init
```

### 🚀 Environment Setup
Then download then repo and install our module **AppForge**:

```python
git clone https://github.com/AppForge-Bench/AppForge

cd AppForge
pip install -e .
# or to run our examples (recommended):
pip install -e .[example]
```




### 🔰 Quick Start Example

We provide a example with *test.py* under *examples*. A quick test with qwen3coder on taskid=54 (a calculator app) can be run through (for **Docker** users):

```
python examples/test.py --use_docker --docker_port=6080 \
--model=qwen3coder --runs=example_qwen3 --api_key_path=<api_key_path> --start_id 54 --end_id 54
```

In case you don't have access to the model, you can run with option *--naive*, which implements a naive solution of making no change on the base template.

```
python examples/test.py --use_docker --docker_port=6080 \
--model=naive --runs=example_naive --start_id 54 --end_id 54
```

Similarly, we can run following code with **local emulator**s:

```
python examples/test.py --emulator_id <emulator_id> --bench_folder <position_where_you_pull_the_AppBench_forge> --sdk_path <sdk_path> \
--model=qwen3coder --runs=example_qwen3 --api_key_path=<api_key_path> --start_id 54 --end_id 54
```

For example on our machine we run following command:

```
python examples/test.py --emulator_id  emulator-5554 --bench_folder /mnt/AppForge-Bench --sdk_path /home/Android/sdk \
--model=qwen3coder --runs=example_qwen3 --api_key_path=dash_scope.key --start_id 54 --end_id 54 
```

To activate self-fix with compilation feedback, set parameter value *--self_fix_attempts*. 

To record videos when testing, set parameter option *--record_video*.

More detailed running parameters can be seen in the source code.
