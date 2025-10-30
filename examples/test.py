from LLMs import qwen3_coder,naive,deepseekchat,deepseekr1
from claude_code import claude_code
import json,os,random,tarfile
from pathlib import Path
import glob,sys,argparse
import subprocess
import shutil
# import appforge
import AppForge
from AppForge import AppForge
from simple import simple_output_parser,simple_agent

if __name__ == "__main__":
    # python examples/test_qwen3.py --use_docker --start_id 0 --end_id 1 --docker_port=6088
    ap = argparse.ArgumentParser("---run main tests---")
    
    ap.add_argument('--use_docker', action='store_true',
                    help="whether to use docker")
    ap.add_argument('--docker_name', default='zenithfocuslight/appforge:latest',
                    help="docker image name; most of the occasions default name is ok")
    ap.add_argument('--docker_port', type=int, default=6080,
                    help="docker port")
    ap.add_argument("--emulator_id", default="emulator-5554",
                    help="adb device id, such as 'emulator-5554'")
    
    ap.add_argument('--base_folder', default = 'runs',
                    help="where to put generated apks")
    # ap.add_argument('--template_path', default = 'compiler/templates/empty_activity')
    ap.add_argument('--bench_folder', default = None,
                    help="where you download bench folder; required when test locally")    
    ap.add_argument('--sdk_path', default = None,
                    help="where you have your android sdk; required when test locally")
    
    
    ap.add_argument("--model", default="qwen3coder",
                    choices=["qwen3coder","naive","deepseekv3","deepseekr1","claude_code"])
    ap.add_argument("--api_key_path",default=None,
                    help="where you have your api keys")
    
    ap.add_argument("--runs", default="example_qwen3",
                    help="name of this test run")
    
    ap.add_argument('--fuzz', action='store_true',
                    help="whether to run tests only or tests and fuzz both")
    
    ap.add_argument('--record_video', action='store_true',
                    help="whether to record videos when testing")
    
    ap.add_argument('--start_id', type=int, default=0,
                    help="range of tested apps (inclusive)")
    ap.add_argument('--end_id', type=int, default=100,
                    help="range of tested apps (inclusive)")
    
    ap.add_argument('--self_fix_attempts', type=int, default=0,
                    help="self fix with compile feedback")
    
    args = ap.parse_args()
    args.template_path = 'compiler/templates/empty_activity'
    # exit(0)
    os.makedirs(args.base_folder,exist_ok=True)
    if args.use_docker:
        evaluator = AppForge(args.runs, base_folder = Path(args.base_folder).resolve(), use_docker=True, \
            docker_name=args.docker_name, docker_port=args.docker_port, record_video=args.record_video)
    else:
        assert args.sdk_path and args.bench_folder, 'Android SDK and Benchmark folder not provided!'
        evaluator = AppForge(args.runs, base_folder = Path(args.base_folder).resolve(), emulator_id=args.emulator_id,\
            bench_folder = Path(args.bench_folder).resolve(),sdk_path = Path(args.sdk_path).resolve(), record_video=args.record_video)
    
    base_folder_path = Path(args.base_folder)
    done = {}
    try:
        with open(base_folder_path / str(args.runs) / 'done.json', 'r+') as file:
            done = json.load(file)   
    except :
        None
        
    done = {int(key): value for key, value in done.items()}
        
    try:
        for task_id in range(args.start_id,args.end_id+1):
            if task_id in done:
                continue
            
            if args.model == 'qwen3coder':
                simpleAgent = simple_agent(simple_output_parser, qwen3_coder(api_key_path=Path(args.api_key_path).absolute()),\
                    template_repo = Path(args.template_path))
            elif args.model == 'deepseekv3':
                simpleAgent = simple_agent(simple_output_parser, deepseekchat(api_key_path=Path(args.api_key_path).absolute()),\
                    template_repo = Path(args.template_path))
            elif args.model == 'deepseekr1':
                simpleAgent = simple_agent(simple_output_parser, deepseekr1(api_key_path=Path(args.api_key_path).absolute()),\
                    template_repo = Path(args.template_path))
            elif args.model == 'claude_code':
                assert args.self_fix_attempts==0
                simpleAgent = claude_code(args.template_path, evaluator, task_id)
            elif args.model == 'naive':
                simpleAgent = simple_agent(simple_output_parser, naive(),\
                    template_repo = Path(args.template_path))
            else:
                assert 0,f"No such model {args.model}"
            raw_log, changed = simpleAgent.solve(evaluator.description(task_id)['features'])
            compile_error = evaluator.compile_json_based_on_template(changed, task_id, raw_log=raw_log)
            for i in range(args.self_fix_attempts):
                if compile_error is None:
                    break
                raw_log, changed = simpleAgent.repair(compile_error)
                compile_error = evaluator.compile_json_based_on_template(changed, task_id, raw_log=raw_log)
            done[task_id] = True
        if args.fuzz:
            print(evaluator.evaluation(list(done.keys())))
        else:
            print(evaluator.evaluation_only_test(list(done.keys())))
    finally:
        with open(base_folder_path / str(args.runs) / 'done.json', 'w+') as file:
            json.dump(done, file)
        evaluator.clean_up()

        
