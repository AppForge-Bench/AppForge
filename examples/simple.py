import os, shutil, json
from pathlib import Path
def print_tree(__path, prefix=""):
    answer = ""
    def print_answer(str):
        nonlocal answer
        answer += str+'\n'
    def dfs(startpath, prefix=""):
        items = list(startpath.iterdir())
        items.sort()  

        for index, path in enumerate(items):
            item = path.relative_to(startpath)
            is_last = index == len(items) - 1
            if is_last:
                print_answer(prefix + "└── " + str(item))
                new_prefix = prefix + "    "
            else:
                print_answer(prefix + "├── " + str(item))
                new_prefix = prefix + "│   "
            if path.is_dir():
                dfs(path, new_prefix)
    dfs(__path, prefix)
    return answer

def simple_output_parser(output):
    output = output[output.find('{'):output.rfind('}')+1]
    try:
        return json.loads(output)
    except:
        return None
    
    
def simple_prompt(description, base_repo):
        system_prompt = 'You are an autonomous programmer and you are modifying a default Android app template with empty activity.\n'
        system_prompt += "Your code will be compiled with Android API 31.\n"
        user_prompt = f'''
The default Android app template "File Structure" is shown below. \
You can replace or add some files in the templates to implement the app.
"File Structure":
{print_tree(base_repo)}



Your app should implement every feature in "App Features", and we'll test on each of the features. \
Note that you should pay attention to the resource-id, content-desc, texts and other attributes we provide with corresponding widgets in 'App Features' \
and exactly match the attributes when implementing the widgets.
"App Features":
{description}



'''+'''\
Please return a json string and only a json string of files to be revised and the revised code in following format:
{
    "app/src/main/AndroidManifest.xml":...,
    "app/src/main/java/com/example/calculator/MainActivity.java":...,
    ...
}
'''

        return [
            
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": system_prompt + user_prompt,
                }] ,
            }
        ]
        

class simple_agent():
    def __init__(self, output_parser, llm, template_repo):
        self.output_parser = output_parser
        self.llm = llm
        self.messages = []
        self.template_repo = template_repo
    
    def solve(self, description):
        self.messages = simple_prompt(description, self.template_repo)
        
        answer = self.llm(self.messages)['parsed_output']
        self.messages.append({"role": "assistant", "content": answer})
        return answer,self.output_parser(answer)
    
    def repair(self, compile_errors):
        if len(compile_errors)==0:
            # no exact error is output
            user_prompt = f"\
Your generated code can't be successfully compiled!\n"
        else:
            user_prompt = f"Your generated code can't be successfully compiled! Compilation errors are:\n\
{compile_errors}\n\n\n"
        user_prompt += 'Remember, '+self.messages[0]['content'][0]['text'] 
        
        self.messages += [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": user_prompt,
                }] ,
            }
        ]
            
        answer = self.llm(self.messages)['parsed_output']
        self.messages.append({"role": "assistant", "content": answer})
        return answer, self.output_parser(answer)

        
