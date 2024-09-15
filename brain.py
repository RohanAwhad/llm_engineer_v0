import os
import re
from message import Message
from llm_engineer import get_input_from_user, llm_call, rewrite_file


class Brain:
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.history = []
        self.MAX_RETRIES = 3
        self.max_retries = self.MAX_RETRIES
        self.user_turn = True

        self.tool_name_ptrn = re.compile(r"TOOL_NAME: ([\d\w]+)", re.DOTALL)
        self.diff_ptrn = re.compile(r"```diff(.*?)```", re.DOTALL)
        self.response_ptrn = re.compile(r"```response(.*?)```", re.DOTALL)
        self.filename_ptrn = re.compile(r"```filename(.*?)```", re.DOTALL)

        # Initialize system prompt
        self.load_system_prompt()

    def load_system_prompt(self):
        with open("prompts/brain.txt", "r") as f:
            sys_prompt = f.read()
        self.history.append(Message("system", sys_prompt))

    def process_file_reader(self, filename):
        absolute_fp = f"{self.workspace}/{filename}"
        if os.path.exists(absolute_fp):
            with open(absolute_fp, "r") as f:
                file_contents = f.read()
            self.history.extend(
                [
                    Message("assistant", self.llm_res),
                    Message("user", f"File Contents:\n\n```\n{file_contents}\n```"),
                ]
            )
        else:
            self.history.extend(
                [
                    Message("assistant", self.llm_res),
                    Message(
                        "user",
                        "File does not exist. If you want to add content just call file writer. It will handle creation",
                    ),
                ]
            )

    def process_file_writer(self, filename, diff):
        out = rewrite_file(self.workspace, filename, diff)
        self.history.extend(
            [
                Message("assistant", self.llm_res),
                Message("user", f"TOOL_OUTPUT:\n\n{out}"),
            ]
        )

    def run(self, user_msg: Message):

        self.history.append(user_msg)
        user_turn = False
        max_retries = self.MAX_RETRIES
        while not user_turn:
            print(f"\033[93m{self.history[-1]}\033[0m")
            self.llm_res = llm_call("gpt-4o-2024-08-06", self.history, temperature=0.8)
            print("\033[95m" + str(self.llm_res) + "\033[0m")

            # Check if tool is called
            tool_name_match = re.search(self.tool_name_ptrn, self.llm_res)
            if tool_name_match:
                tool_name = tool_name_match.group(1)

                if tool_name == "file_reader":
                    filename_match = re.search(self.filename_ptrn, self.llm_res)
                    if filename_match:
                        filename = filename_match.group(1).strip()
                        self.process_file_reader(filename)
                        user_turn = False
                        max_retries = self.MAX_RETRIES
                    else:
                        user_turn = False
                        max_retries -= 1

                elif tool_name == "file_writer":
                    filename_match = re.search(self.filename_ptrn, self.llm_res)
                    diff_match = re.search(self.diff_ptrn, self.llm_res)
                    if filename_match and diff_match:
                        filename = filename_match.group(1).strip()
                        diff = diff_match.group(1).strip()
                        self.process_file_writer(filename, diff)
                        user_turn = False
                        max_retries = self.MAX_RETRIES
                    else:
                        user_turn = False
                        max_retries -= 1

                else:
                    user_turn = False
                    max_retries -= 1

            # Check if responding to user
            else:
                response_match = re.search(self.response_ptrn, self.llm_res)
                if response_match:
                    response = response_match.group(1).strip()
                    self.history.append(Message("assistant", self.llm_res))
                    user_turn = True
                    max_retries = self.MAX_RETRIES
                    print("\033[92m" + response + "\033[0m")
                else:
                    user_turn = True
                    max_retries -= 1


if __name__ == '__main__':
    brain = Brain('../hello_world')
    while True:
        user_msg = get_input_from_user()
        brain.run(user_msg)
