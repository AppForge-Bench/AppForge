
from typing import Optional
import json,subprocess,time
import docker
from pathlib import Path
import os

from .extracts import extract_error, extract_fuzz, extract_test
from .utils import remove_directory, sumup_json, compare_folder


class AppForge:
    """
    A class for building, testing, and fuzzing Android applications.
    This class provides functionality to compile Android apps from templates,
    run tests, and perform fuzzing operations either using local emulator or Docker.
    
    """
    docker_base_folder = Path('/AppDev-Bench/AppDev-Bench/runs')
    docker_bench_folder = Path('/AppDev-Bench/AppDev-Bench')
    template_folder = Path('compiler/templates')
    task_num = 101
    
    def __init__(self, runs: str,
                 base_folder: Path = Path('runs'),
                 use_docker: bool = False,
                 emulator_id: Optional[str] = None,
                 sdk_path: Optional[Path] = None,
                 bench_folder: Optional[Path] = None,
                 docker_name: str = 'zenithfocuslight/appforge:latest',
                 docker_port: int = 6080,
                 record_video: bool = False,
                 use_existing_docker: bool = False,
                 existing_docker_id: Optional[str] = None,
                 ):
        """
        Initialize the AppForge instance.
        
        Args:
            runs (str): Name identifier for the current run session. Will build a same name folder under base_folder for storing data.
            base_folder (Path): Base directory for storing run data. Defaults to '/runs'.
            use_docker (bool): Whether to use Docker for operations. Defaults to False.
            emulator_id (Optional[str]): ID of the emulator to use. Required if not using Docker.
            sdk_path (Optional[Path]): Path to Android SDK. Required if not using Docker.
            bench_folder (Optional[Path]): Path to benchmark folder. Required if not using Docker.
            docker_name (str): Docker image name to use. Defaults to 'zenithfocuslight/appforge:latest'.
            docker_port (int): Port to expose from Docker container. Defaults to 6080.
            record_video (bool): whether to record video
            use_existing_docker (bool): whether to use existing docker
            existing_docker_id (str): if yes, use which one
        """
        assert (use_docker ^ (emulator_id is not None)), \
            'We must choose one and only one option of docker or local emulator for evaluation!'
        self.emulator_id = emulator_id
        self.base_folder = base_folder
        self.app_folder = base_folder / runs
        self.app_folder.mkdir(parents=True, exist_ok=True)
        self.use_docker = use_docker
        self.use_existing_docker = use_existing_docker
        self.raw_folder = self.app_folder / 'raw_output'
        self.raw_folder.mkdir(parents=True, exist_ok=True)
        (self.app_folder / 'workspace').mkdir(parents=True, exist_ok=True)
        (self.app_folder / 'videos').mkdir(parents=True, exist_ok=True)
        self.record_video = record_video
       
        if self.use_docker:
            self.docker_folder = self.docker_base_folder / runs
            self.emulator_id='emulator-5554'
            client = docker.from_env()
            if self.use_existing_docker:
                print(f'AppForge: Directly Using docker {docker_name}...')
                self.container = client.containers.get(existing_docker_id)
            else:
                print(f'AppForge: Starting docker {docker_name}...')
                host_user_uid = os.getuid()
                host_user_gid = os.getgid()
                self.container = client.containers.run(
                    docker_name,
                    user=f'{host_user_uid}:{host_user_gid}',
                    ports={f'{docker_port}/tcp': docker_port},  
                    devices=['/dev/kvm:/dev/kvm'], 
                    detach=True,
                    volumes={
                        str(self.base_folder): {  # 主机目录
                            'bind': str(self.docker_base_folder),  # 容器内目录
                            'mode': 'rw'  # 读写模式
                        }
                    },
                    privileged=True,
                )   
            print('AppForge: Waiting emulator on docker to get online...')
            while True:
                print('AppForge: This might take a while (2-3min)...')
                try:
                    self.ensure_emulator()
                    print('AppForge: Emulator confirmed...')
                    break
                except:
                    time.sleep(10)    
        else:
            assert sdk_path and bench_folder, 'Android SDK and Benchmark folder not provided!'
            self.sdk_path = sdk_path
            self.bench_folder = bench_folder
        with open('tasks/tasks.json','r') as file:
            self.task_sheet = json.load(file)
    
    def clean_up(self):
        """
        Clean up resources and stop Docker container if used.
        """
        if self.use_docker and not self.use_existing_docker:
            print('AppForge: Shutting down docker...')
            self.container.stop()
            self.container.remove()
            
        
    def description(self, task_id: int):
        """
        Get description of a specific task.
        
        Args:
            task_id (int): ID (0~100) of the task to describe.
            
        Returns:
            dict: Dictionary containing task description with keys:
                - task: App name
                - features: Refined feature descriptions
                - gradle_version: Gradle version used
                - api_version: Android API version
                - device: Target device name
                
        """
        assert task_id>=0 and task_id<=self.task_num, \
            f'Task ID ranges from 0~{self.task_num-1}.'
            
        return {
            'task': self.task_sheet[task_id]["app_key"],
            'features':self.task_sheet[task_id]["refined_features"],
            'api_version':'Android 12',
            'device':'Nexus 4',
        }
    
    def task_name(self, task_id: int):
        return self.description(task_id)['task']
    def apk_folder(self, task_id):
        return self.app_folder / str(task_id)
    def workspace(self, task_id):
        return self.app_folder / 'workspace' / str(task_id)
    def compile_log(self, task_id):
        return self.apk_folder(task_id) / 'compile.log'
    def raw_log_file(self, task_id):
        return self.raw_folder / f'{task_id}.log'
    def test_log(self, task_id):
        return self.apk_folder(task_id) / 'test.log'
    def fuzz_log(self, task_id):
        return self.apk_folder(task_id) / 'fuzz.log'
    def json_file(self, task_id):
        return self.apk_folder(task_id) / 'changed.json'
    def result_path(self, task_id):
        return self.app_folder / str(task_id) / 'test_result.json'
    def fuzz_result_path(self, task_id):
        return self.app_folder / str(task_id) / 'fuzz_result.json'
    def direct_apk_path(self, task_id):
        return self.app_folder / str(task_id) / str(task_id) /'app'/'build'/'outputs'/'apk'/'debug'/'app-debug.apk' 
    def video_path(self, task_id):
        return self.app_folder / 'videos'/ f'{str(task_id)}.mp4'
        
    def docker_apk_folder(self, task_id):
        return self.docker_folder / str(task_id) 
    def docker_workspace(self, task_id):
        return self.docker_folder / 'workspace' / str(task_id)
    def docker_json_file(self, task_id):
        return self.docker_apk_folder(task_id) / 'changed.json'
    def docker_direct_apk_path(self, task_id):
        return self.docker_folder / str(task_id) / str(task_id) /'app'/'build'/'outputs'/'apk'/'debug'/'app-debug.apk'     
    def docker_video_path(self, task_id):
        return self.docker_folder / 'videos'/ f'{str(task_id)}.mp4'
    
    def ensure_emulator(self):
        """
        Ensure that the emulator is online and accessible.
        """
        if self.use_docker:
            if self.emulator_id not in self.container.exec_run('adb devices').output.decode():
                assert 0, 'Emulator offline!'
        else:
            if self.emulator_id not in subprocess.run(['adb', 'devices'], capture_output=True, text=True).stdout:
                assert 0, 'Emulator offline!'
        
        
    def compile_json_based_on_template(self, changed: dict[str, str], task_id: int, raw_log: Optional[str] = None):
        """
        Apply changes from JSON on template and compile the application.
        
        Args:
            changed (dict[str, str]): Dictionary containing changes to apply.
            task_id (int): ID of the task to compile.
            
        Returns:
            str: Compilation errors if any, empty string if successful.
        """
        print(f'AppForge: Compiling on {task_id}...')
        remove_directory(self.apk_folder(task_id))
        self.apk_folder(task_id).mkdir()

        with open(self.raw_log_file(task_id), 'a+', encoding='utf-8') as file:
            file.write('='*20+'\n')
            if raw_log:
                file.write(raw_log)
        if changed:
            with open(self.json_file(task_id), 'w+', encoding='utf-8') as file:
                json.dump(changed, file)
            
            if self.use_docker:
                cmd = f'''python3 build.py --android-sdk-path="/opt/android" \
                --templates-dir=./templates --generated-files="{str(self.docker_json_file(task_id))}" --output="{str(self.docker_apk_folder(task_id))}" --project-name="{str(task_id)}" --json_content_directly'''
                output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder / 'compiler')).output.decode()
            else:
                cmd = f'''python build.py --android-sdk-path="{str(self.sdk_path)}" \
                    --templates-dir=./templates --generated-files="{str(self.json_file(task_id))}" --output="{str(self.apk_folder(task_id))}" --project-name="{str(task_id)}" --json_content_directly'''
                output = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder / 'compiler')).stdout

            with open(self.compile_log(task_id),'w+') as file:
                file.write(output)
            if self.use_docker:    
                return extract_error(output, ignore_path_str=str(self.docker_apk_folder(task_id)))
            else:
                return extract_error(output, ignore_path_str=str(self.apk_folder(task_id)))
        else:
            output = 'Wrong Json Format\n'
            with open(self.compile_log(task_id),'w+') as file:
                file.write(output)
            return output
        
    def compile_folder(self, folder: Path, task_id: int):
        """
        Copy files from target folder and compile the application.
        
        Args:
            folder (Path): Source folder containing files to compile.
            task_id (int): ID of the task to compile.
            
        Returns:
            str: Compilation errors if any, empty string if successful.
        """
        changed = compare_folder(folder, self.template_folder / 'empty_activity')
        return self.compile_json_based_on_template(changed, task_id)
            
   
    def test(self, task_id: int):
        """
        Run test cases on the specified task.
        
        Args:
            task_id (int): ID of the task to test.
            
        Returns:
            dict: Test results containing:
                - compile (int): 1 if compilation successful, 0 otherwise; 
                    if not successfully compiled, other value is set to be 0
                - test (float): Test pass rate between 0.0 and 1.0
                - all_pass (int): 1 if all tests passed, 0 otherwise
            
        """
        print(f'AppForge: Testing on {task_id}...')
        self.ensure_emulator()
        assert self.apk_folder(task_id).exists(), 'Target task not built!'
        if self.result_path(task_id).exists():
            with open(self.result_path(task_id), 'r', encoding='utf-8') as file:
                return json.load(file)


        if self.direct_apk_path(task_id).exists():
            if self.use_docker:
                if self.record_video:
                    cmd = f'adb shell screenrecord {str(self.docker_video_path(task_id))} &'
                    output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder)).output.decode()
                    cmd = 'echo $!'
                    output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder)).output.decode()
                    pid = int(output.strip())
                    
                cmd = f'''python3 evaluate_app.py     --apk-path="{str(self.docker_direct_apk_path(task_id))}"  \
                --test no_fuzz  --package-name="{self.task_name(task_id)}"     --device-id="{self.emulator_id}"    --task="{self.task_name(task_id)}" '''
                output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder)).output.decode()

                if self.record_video:
                    cmd = f'kill {pid}'
                    output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder)).output.decode()
            else:
                if self.record_video:
                    cmd = f'adb shell screenrecord {str(self.video_path(task_id))} &'
                    results = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder))
                    cmd = 'echo $!'
                    results = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder))
                    output,err = results.stdout, results.stderr 
                    pid = int(output.strip())
                    
                cmd = f'''python evaluate_app.py     --apk-path="{str(self.direct_apk_path(task_id))}"   \
                --test no_fuzz  --package-name="{self.task_name(task_id)}"     --device-id="{self.emulator_id}"    --task="{self.task_name(task_id)}" '''
                results = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder))
                output,err = results.stdout, results.stderr 
                
                if self.record_video:
                    cmd = f'kill {pid}'
                    results = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder))
                    
        else:
            output = 'Compilation Failure!'
            
        with open(self.test_log(task_id),'w+') as file:
            file.write(output)

        result = extract_test(output)
        with open(self.result_path(task_id), 'w+', encoding='utf-8') as file:
            json.dump(result, file)
        return result
    
    def fuzz(self, task_id: int):
        """
        Run 10-minute fuzzing on the specified task.
        
        Args:
            task_id (int): ID of the task to fuzz.
            
        Returns:
            dict: Fuzzing results containing:
                - compile (int): 1 if compilation successful, 0 otherwise;
                    if not successfully compiled, other value is set to be 0
                - no_crash (int): 1 if no crashes detected, 0 otherwise
                - native (int): 1 if native crash detected, 0 otherwise
                - java (int): 1 if Java crash detected, 0 otherwise
                - anr (int): 1 if ANR detected, 0 otherwise
                - failtostart (int): 1 if app failed to start, 0 otherwise
            
        """
        print(f'AppForge: Fuzzing on {task_id}...')
        self.ensure_emulator()
        assert self.apk_folder(task_id).exists(), 'Target task not built!'
        if self.fuzz_result_path(task_id).exists():
            with open(self.fuzz_result_path(task_id), 'r', encoding='utf-8') as file:
                return json.load(file)

        if self.direct_apk_path(task_id).exists():
            if self.use_docker:
                cmd = f'''python3 evaluate_app.py     --apk-path="{str(self.docker_direct_apk_path(task_id))}"  \
                --test only_fuzz  --package-name="{self.task_name(task_id)}"     --device-id="{self.emulator_id}"    --task="{self.task_name(task_id)}" '''
                output = self.container.exec_run(cmd,workdir=str(self.docker_bench_folder)).output.decode()
            else:
                cmd = f'''python evaluate_app.py     --apk-path="{str(self.direct_apk_path(task_id))}"   \
                --test only_fuzz  --package-name="{self.task_name(task_id)}"     --device-id="{self.emulator_id}"    --task="{self.task_name(task_id)}" '''
                results = subprocess.run(cmd, capture_output=True,shell=True,text=True,cwd=str(self.bench_folder))
                output,err = results.stdout, results.stderr 
        else:
            output = 'Compilation Failure!'
            
        with open(self.fuzz_log(task_id),'w+') as file:
            file.write(output)
        result = extract_fuzz(output)
        with open(self.fuzz_result_path(task_id), 'w+', encoding='utf-8') as file:
            json.dump(result, file)
        return result
    
    def evaluation_only_test(self, eval_list: Optional[list] = None):
        """
        Run test cases on specified tasks or all tasks.
        
        Args:
            eval_list (Optional[list]): List of task IDs to evaluate. If None, evaluates all tasks.
            
        Returns:
            dict: Aggregated test results for all evaluated tasks.
        """
        all_results = {}
        if eval_list:
            for i in eval_list:
                all_results[i] = {**self.test(i)}
        else:
            for i in range(self.task_num):
                all_results[i] = {**self.test(i)}
        return sumup_json(all_results)
        
    def evaluation(self, eval_list: Optional[list] = None):
        """
        Run test cases and fuzzing on specified tasks or all tasks.
        
        Args:
            eval_list (Optional[list]): List of task IDs to evaluate. If None, evaluates all tasks.
            
        Returns:
            dict: Aggregated test and fuzzing results for all evaluated tasks. 
            In addition, we calculate 'crash_rate' which stands for the crash rate on successfully compiled apks. 
        """
        all_results = {}
        if eval_list:
            for i in eval_list:
                all_results[i] = {**self.test(i), **self.fuzz(i)}
        else:
            for i in range(self.task_num):
                all_results[i] = {**self.test(i), **self.fuzz(i)}
        ans = sumup_json(all_results)
        ans['crash_rate'] = 1 - ans['no_crash'] / ans['compile']
        return ans
