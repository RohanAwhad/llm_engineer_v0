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
  client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])#, base_url="https://api.together.xyz/v1")
  res = client.chat.completions.create(model=model, messages=[dataclasses.asdict(x) for x in messages], temperature=temperature, max_tokens=4096)
  return res.choices[0].message.content



def get_input_from_user() -> str:
  print('User >')
  messages = []
  while True:
    user_input = input()
    messages.append(user_input)
    if END_OF_INPUT in user_input: break
  content = '\n'.join(messages).replace(END_OF_INPUT, '')
  return content.strip()




def rewrite_file(workspace: str, filename: str, diff: str) -> Optional[str]:
  '''
  Its job is to rewrite the file contents based on the cmd.
  The cmd would be either ADD or REMOVE.
    - ADD will be used to integreate the new code block into the current file
    - REMOVE will be used to remove a certain function from the current file

  If the filename does not exist or the file is empty, create a new file and add the contents to it directly
  If the file has content, then ask the llm to regenerate the whole file with either addition of the code or deletion.
  '''

  FILEPATH = f'{workspace}/{filename}'
  if not os.path.exists(FILEPATH):
      with open(FILEPATH, 'w') as f: pass

  # get the contents of the file
  with open('prompts/file_rewriter.txt', 'r') as f: sys_prompt = f.read()
  history = [Message('system', sys_prompt),]

  with open(FILEPATH, 'r') as f: file_contents = f.read()
  user_msg = f"CURRENT_FILE_CONTENTS:\n```python\n{file_contents.strip()}\n```\n\n"
  user_msg += f"DIFF:\n```diff\n{diff.strip()}\n```\n\n"

  history.append(Message('user', user_msg))
  print("\033[92m" + str(history[-1]) + "\033[0m")

  code_ptrn = re.compile(r"<\|UPDATED_FILE_START\|>(.*?)<\|UPDATED_FILE_END\|>", re.DOTALL)
  max_retries = 3
  while max_retries > 0:
    max_retries -= 1
    llm_res = llm_call("gpt-4o-mini", history, temperature=0.8)
    print('\033[94m' + f'Assistant:{llm_res}'+'\033[0m') 

    # check if python code exists
    match = re.search(code_ptrn, llm_res)
    if match:
      new_code = match.group(1).strip()
      with open(FILEPATH, 'w') as f: f.write(new_code)
      return None

  return "Error: was unable to modify the contents"


def brain(workspace):
  with open('prompts/brain.txt', 'r') as f: sys_prompt = f.read()
  history = [Message('system', sys_prompt), ]
  user_turn = True

  tool_name_ptrn = re.compile(r'TOOL_NAME: ([\d\w]+)', re.DOTALL)
  diff_ptrn = re.compile(r"```diff(.*?)```", re.DOTALL)
  response_ptrn = re.compile(r"```response(.*?)```", re.DOTALL)
  filename_ptrn = re.compile(r"```filename(.*?)```", re.DOTALL)

  MAX_RETRIES = 3
  max_retries = MAX_RETRIES
  while True:
    if user_turn:
      history.append(Message('user', get_input_from_user()))

    print(f"\033[93m{history[-1]}\033[0m")
    llm_res = llm_call("gpt-4o-2024-08-06", history, temperature=0.8)
    print("\033[95m" + str(llm_res) + "\033[0m")

    # check if tool is called?
    match = re.search(tool_name_ptrn, llm_res)
    if match:
      tool_name = match.group(1)

      if tool_name == 'file_reader':
        filename_match = re.search(filename_ptrn, llm_res)
        if filename_match:
          filename = filename_match.group(1).strip()
          absolute_fp = f'{workspace}/{filename}'
          if os.path.exists(absolute_fp):
            with open(absolute_fp, 'r') as f: file_contents = f.read()
            history.extend([Message('assistant', llm_res), Message('user', f'File Contents:\n\n```\n{file_contents}\n```'), ])
          else:
            history.extend([Message('assistant', llm_res), Message('user', f'File does not exist. If you want to add content just call file writer. It will handle creation'), ])

          user_turn = False
          max_retries = MAX_RETRIES
        else:
          user_turn = False
          max_retries -= 1
          continue

      elif tool_name == 'file_writer':
        filename_match = re.search(filename_ptrn, llm_res)
        diff_match = re.search(diff_ptrn, llm_res)
        if filename_match and diff_match:
          filename = filename_match.group(1).strip()
          diff = diff_match.group(1).strip()
          out = rewrite_file(workspace, filename, diff)
          history.extend([Message('assistant', llm_res), Message('user', f'TOOL_OUTPUT:\n\n{out}') ])
          user_turn = False
          max_retries = MAX_RETRIES
        else:
          user_turn = False
          max_retries -= 1
          continue

      else:
        user_turn = False
        max_retries -= 1
        continue

    # check if responding to user
    else:
      match = re.search(response_ptrn, llm_res)
      if match:
        # responding back to user
        response = match.group(1).strip()
        history.append(Message('assistant', llm_res))
        user_turn = True
        max_retries = MAX_RETRIES
        print("\033[92m" + response + "\033[0m")
        continue

      else:
        user_turn = False
        max_retries -= 1
        continue


if __name__ == '__main__':
  import sys
  workspace = sys.argv[1]
  brain(workspace)
