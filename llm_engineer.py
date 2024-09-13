import dataclasses
import openai
import os
import re
import subprocess
from typing import Optional


@dataclasses.dataclass
class Message:
  role: str
  content: str
  def __str__(self): return f"[{self.role}]: {self.content}"
  def __repr__(self): return str(self)

END_OF_INPUT = "<|ROHAN_OUT|>"

def llm_call(model: str, messages: list[Message], temperature: float):
  client = openai.OpenAI(api_key=os.environ["TOGETHER_API_KEY"], base_url="https://api.together.xyz/v1")
  res = client.chat.completions.create(model=model, messages=[dataclasses.asdict(x) for x in messages], temperature=temperature, max_tokens=4096)
  return res.choices[0].message.content


'''
I need 3 tools, one brain llm
  1. Python Interpreter
  2. Bash Interpreter
  3. File Rewriter
'''


def get_input_from_user() -> str:
  print('User >')
  messages = []
  while True:
    user_input = input()
    messages.append(user_input)
    if END_OF_INPUT in user_input: break
  content = '\n'.join(messages).replace(END_OF_INPUT, '')
  return content.strip()


@dataclasses.dataclass
class BashCMDOutput:
  returncode: int
  stdout: str
  stderr: str

def run_bash_command(container_name: str, command: str) -> BashCMDOutput:
    cmd = f"docker exec {container_name} sh -c '{command}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return BashCMDOutput(result.returncode, result.stdout, result.stderr)


def python_interpreter_tool(container_name: str, code: str, env_name: str) -> tuple[str, str]:
  '''
  Run the code, if error: call python executor agent try to solve the error, with max_retries for 5 times. if success: return the output.

  steps involved:
    1. Saving the code in /tmp/<filename>.py
    2. Run the code
    3. If successful execution: Get the success output and return
    4. If error, send the code and error+output to agent
    5. Get response:
      - If code: update the code in /tmp/<filename>.py
      - else if "Need Package: <package_name>": Wait for user confirmation of installation and then retry


  This execution needs to have a common set of packages installed in conda env.
  '''

  LOCAL_DIR = './play'
  DOCKER_DIR = '/tmp'
  filename = "python_interpreter_tool.py"
  max_retries = 5
  first_msg = True
  user_msg = None

  code_ptrn = re.compile(r"```python(.*?)```", re.DOTALL)
  pkg_req_ptrn = re.compile(r"Need Package: ([\d\w-]+)")

  with open('prompts/python_executor.txt', 'r') as f: sys_prompt = f.read()
  history = [Message(role='system', content=sys_prompt), ]

  with open(f'{LOCAL_DIR}/{filename}', "w") as f: f.write(code)
  while True:
    max_retries -= 1
    bash_command = f"/opt/conda/envs/{env_name}/bin/python {DOCKER_DIR}/{filename}"
    output: BashCMDOutput = run_bash_command(container_name, bash_command)
    if output.returncode == 0 or max_retries <= 0: return output.stdout, output.stderr

    msg = f'Output:\n{output.stdout}\n\nError:\n{output.stderr}'
    if first_msg:
      msg = f'Code:\n```python\n{code}\n```\n\n---\n{msg}'
      first_msg = False
    if user_msg is not None:
      msg = f'User feedback: {user_msg}'
      user_msg = None

    history.append(Message(role='user', content=msg))
    print('\033[92m' + str(history[-1]) + '\033[0m')
    llm_res = llm_call("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", history, temperature=0.8)
    history.append(Message(role='assistant', content=llm_res))
    print(f"\033[94m{history[-1]}\033[0m")

    # check if package installation exists
    pkg_req_ptrn = re.compile(r"Need Package: ([\d\w-]+)")
    match = re.search(pkg_req_ptrn, llm_res)
    if match:
      package_request = match.group(1).strip()
      # wait for confirmation from user.
      user_feedback = input(f"Need you to install this package: {package_request}. Confirm that you have installed it (Y/n): ")
      user_msg = "Package has been installed." if user_feedback == 'Y' else f"Package was not installed. {user_feedback}"
      continue

    # check if python code exists
    match = re.search(code_ptrn, llm_res)
    if match:
      new_code = match.group(1).strip()
      with open(f'{LOCAL_DIR}/{filename}', 'w') as f: f.write(new_code)
      continue

    # if none of the above, give control back to user. User can enter a message and retry the conversation or end the execution
    user_msg = get_input_from_user()


def rewrite_file(workspace: str, filename: str, code: str, cmd: str) -> Optional[str]:
  '''
  Its job is to rewrite the file contents based on the cmd.
  The cmd would be either ADD or REMOVE.
    - ADD will be used to integreate the new code block into the current file
    - REMOVE will be used to remove a certain function from the current file

  If the filename does not exist or the file is empty, create a new file and add the contents to it directly
  If the file has content, then ask the llm to regenerate the whole file with either addition of the code or deletion.
  '''
  if cmd not in ("ADD", "REMOVE"): return f"Error: Command should be one of 'ADD' or 'REMOVE', but got '{cmd}'"

  FILEPATH = f'{workspace}/{filename}'
  if not os.path.exists(FILEPATH):
    if cmd == "ADD":
      with open(FILEPATH, 'w') as f: f.write(code)
    else:
      # TODO: (rohan) this shouldn't happen. If the file doesn't exist, then the remove command should not have been called
      return None

  # get the contents of the file
  with open('prompts/file_rewriter.txt', 'r') as f: sys_prompt = f.read()
  history = [Message('system', sys_prompt),]

  with open(FILEPATH, 'r') as f: file_contents = f.read()
  user_msg = f"CURRENT_FILE_CONTENTS:\n```python\n{file_contents.strip()}\n```\n\n"
  user_msg += f"CONTENT_TO_MODIFY:\n```python\n{code.strip()}\n```\n\n"
  user_msg += f'COMMAND: {cmd}'

  history.append(Message('user', user_msg))
  print("\033[92m" + str(history[-1]) + "\033[0m")

  code_ptrn = re.compile(r"```python(.*?)```", re.DOTALL)
  max_retries = 3
  while max_retries > 0:
    max_retries -= 1
    llm_res = llm_call("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", history, temperature=0.8)
    print('\033[94m' + f'Assistant:{llm_res}'+'\033[0m') 

    # check if python code exists
    match = re.search(code_ptrn, llm_res)
    if match:
      new_code = match.group(1).strip()
      with open(FILEPATH, 'w') as f: f.write(new_code)
      return None

  return "Error: was unable to modify the contents"


def brain():
  with open('prompts/brain.txt', 'r') as f: sys_prompt = f.read()
  history = [Message('system', sys_prompt), ]
  user_turn = True

  tool_name_ptrn = re.compile(r'TOOL_NAME: ([\d\w]+)', re.DOTALL)
  code_ptrn = re.compile(r"```python(.*?)```", re.DOTALL)
  response_ptrn = re.compile(r"```response(.*?)```", re.DOTALL)

  MAX_RETRIES = 3
  max_retries = MAX_RETRIES
  while True:
    if user_turn:
      history.append(Message('user', get_input_from_user()))

    print(f"\033[93m{history[-1]}\033[0m")
    llm_res = llm_call("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", history, temperature=0.8)
    print("\033[95m" + str(llm_res) + "\033[0m")

    # check if tool is called?
    match = re.search(tool_name_ptrn, llm_res)
    if match:
      tool_name = match.group(1)
      if tool_name == 'python_interpreter':
        code_match = re.search(code_ptrn, llm_res)
        if code_match:
          code = code_match.group(1).strip()
          # call python interpreter
          exec_output, exec_err = python_interpreter_tool(container_name='python_interpreter', code=code, env_name='python_interpreter_env')
          history.extend([Message('assistant', llm_res), Message('user', f'TOOL_OUTPUT:\n\nOutput:\n"""\n{exec_output}\n"""\n\nError:\n"""\n{exec_err}\n"""')])
          user_turn = False
          max_retries = MAX_RETRIES
          continue
          pass
        else:
          # TODO: (rohan): handle code not found error
          user_turn = False
          continue
          pass
      else:
        # TODO: (rohan) handle wrong tool_name
        user_turn = False
        continue
        pass

    # check if responding to user
    match = re.search(response_ptrn, llm_res)
    if match:
      # responding back to user
      response = match.group(1).strip()
      history.append(Message('assistant', llm_res))
      user_turn = True
      max_retries = MAX_RETRIES
      continue

    else:
      user_turn = False
      max_retries -= 1
      continue


if __name__ == '__main__':
  brain()
  '''
  workspace = './workspaces/hello_world'
  filename = 'hello_world.py'
  cmd = 'ADD'
  code = "def greet_user(name: str): print(f'Hello, {name}')"
  rewrite_file(workspace, filename, code, cmd)
  '''
