import os, shutil, json, subprocess
from pathlib import Path

class claude_code():
    def __init__(self, template_path, evaluator, task_id):
        self.template_path = template_path
        self.evaluator = evaluator
        self.task_id = task_id
        self.workspace = self.evaluator.workspace(self.task_id)
        
        
    def simple_prompt(self, description):
        system_prompt = 'You are an autonomous programmer and you are modifying a default Android app template with empty activity in local directory.\n'
        system_prompt += "Your code will be compiled with Android API 31. \n"
        user_prompt = f'''You can replace or add some files in the templates to implement the app.
Your app should implement every feature in 'App Features', and we'll test on each of the features. \
Note that you should pay attention to the resource-id, content-desc, texts and other attributes we provide with corresponding widgets in 'App Features' \
and exactly match the attributes when implementing the widgets. 
'App Features':
{description}

You should directly modify the file in the given file directory to implement the app.
'''
        if self.evaluator.use_docker:
            docker_cmd = 'docker  exec -it  -w  {self.evaluator.docker_workspace(self.task_id)} {self.evaluator.container.id} ./gradlew build'
            user_prompt += f"You can use '{docker_cmd}' command to compile your code."        
        else:
            user_prompt += "You can use './gradlew build' command to compile your code."        
        return system_prompt+user_prompt
    
    def run(self, workspace, desc):
        cmd = ['claude','-p',f'"{self.simple_prompt(desc)}"','--add-dir','./','--allowed-tools','"Bash(*),Edit,Write,MultiEdit"']
        output = subprocess.run(cmd,capture_output=True,text=True,cwd=str(workspace.resolve())).stdout


    
    def solve(self, desc):
        template_path = self.template_path
        src = Path(template_path).resolve()
        if not src.is_dir():
            raise ValueError(f"template_path not exists: {template_path}")

        workspace = self.workspace
        
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.copytree(src, workspace)

        self.run(workspace, desc)

        changed: dict[str, str] = {}
        for root, _dirs, files in os.walk(workspace):
            for name in files:
                p = Path(root) / name
                rel = str(p.relative_to(workspace))
                src_file = src / rel

                try:
                    new_text = p.read_text(encoding="utf-8")
                except Exception:
                    continue

                if not src_file.exists():
                    changed[rel] = new_text
                else:
                    try:
                        old_text = src_file.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    if new_text != old_text:
                        changed[rel] = new_text


        return 'No raw log provided', changed

   
