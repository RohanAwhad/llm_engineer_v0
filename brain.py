import os
import re
from typing import Callable
from message import Message, MessageToPrint
from llm_functions import get_input_from_user, llm_call, rewrite_file, search_brave


class Brain:
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.history = []
        self.MAX_RETRIES = 3
        self.max_retries = self.MAX_RETRIES
        self.user_turn = True

        self.tool_name_ptrn = re.compile(r"TOOL_NAME: ([\d\w]+)", re.DOTALL)
        self.diff_ptrn = re.compile(r"<\|DIFF_START\|>(.*?)<\|DIFF_END\|>", re.DOTALL)
        self.response_ptrn = re.compile(r"<\|RESPONSE_START\|>(.*?)<\|RESPONSE_END\|>", re.DOTALL)
        self.filename_ptrn = re.compile(r"<\|FILENAME_START\|>(.*?)<\|FILENAME_END\|>", re.DOTALL)
        self.query_ptrn = re.compile(r"<\|QUERY_START\|>(.*?)<\|QUERY_END\|>", re.DOTALL)

        # Initialize system prompt
        self.load_system_prompt()

    def load_system_prompt(self):
        with open("prompts/brain.txt", "r") as f:
            sys_prompt = f.read()
        self.history.append(Message("system", sys_prompt))

    def process_file_reader(self, filename: str, llm_res: str):
        absolute_fp = f"{self.workspace}/{filename}"
        if os.path.exists(absolute_fp):
            with open(absolute_fp, "r") as f:
                file_contents = f.read()
            self.history.extend(
                [
                    Message("assistant", llm_res),
                    Message("user", f"File Contents:\n\n```\n{file_contents}\n```"),
                ]
            )
        else:
            self.history.extend(
                [
                    Message("assistant", llm_res),
                    Message(
                        "user",
                        "File does not exist. If you want to add content just call file writer. It will handle creation",
                    ),
                ]
            )

    def process_file_writer(self, filename: str, diff: str, llm_res: str, update_logs: Callable | None = None):
        out = rewrite_file(self.workspace, filename, diff, update_logs)
        self.history.extend(
            [
                Message("assistant", llm_res),
                Message("user", f"TOOL_OUTPUT:\n\n{out}"),
            ]
        )

    def process_search_google(self, query: str, llm_res: str, api_key: str, update_logs: Callable | None = None):
        # Use the search_brave function as a template for Google Search
        results = search_brave(query, api_key)  # Assuming search_brave can be adapted or replaced with a Google-specific function
        formatted_results = "\n\n".join(str(result) for result in results)

        # Append the search results to the history
        self.history.extend(
            [
                Message("assistant", llm_res),
                Message("user", f"SEARCH_RESULTS:\n\n{formatted_results}"),
            ]
        )
        if update_logs:
            update_logs(MessageToPrint(f'Search results for query: "{query}"', formatted_results, "grey85"))

    def run(self, user_msg: Message, update_logs: Callable | None = None) -> str | None:
        self.history.append(user_msg)
        user_turn = False
        max_retries = self.MAX_RETRIES
        llm_res = None
        api_key = os.environ['BRAVE_SEARCH_AI_API_KEY']

        while not user_turn:
            print(f"\033[93m{self.history[-1]}\033[0m")
            llm_res = llm_call("gpt-4o-2024-08-06", self.history, temperature=0.8)
            print("\033[95m" + str(llm_res) + "\033[0m")
            if update_logs:
                update_logs(MessageToPrint('Brain Raw Response', llm_res, "light_yellow3"))

            tool_name_match = re.search(self.tool_name_ptrn, llm_res)
            if tool_name_match:
                tool_name = tool_name_match.group(1)

                # New Google Search Tool handling
                if tool_name == "google_search":
                    query_match = re.search(self.query_ptrn, llm_res)
                    if query_match:
                        query = query_match.group(1).strip()
                        self.process_search_google(query, llm_res, api_key, update_logs)
                        user_turn = False
                        max_retries = self.MAX_RETRIES
                    else:
                        user_turn = False
                        max_retries -= 1

                elif tool_name == "file_reader":
                    filename_match = re.search(self.filename_ptrn, llm_res)
                    if filename_match:
                        filename = filename_match.group(1).strip()
                        self.process_file_reader(filename, llm_res)
                        if update_logs:
                            update_logs(MessageToPrint(f'Contents of: "{filename}"', self.history[-1].content, "grey85"))
                        user_turn = False
                        max_retries = self.MAX_RETRIES
                    else:
                        user_turn = False
                        max_retries -= 1

                elif tool_name == "file_writer":
                    filename_match = re.search(self.filename_ptrn, llm_res)
                    diff_match = re.search(self.diff_ptrn, llm_res)
                    if filename_match and diff_match:
                        filename = filename_match.group(1).strip()
                        diff = diff_match.group(1).strip()
                        self.process_file_writer(filename, diff, llm_res, update_logs)
                        user_turn = False
                        max_retries = self.MAX_RETRIES
                    else:
                        user_turn = False
                        max_retries -= 1

                else:
                    user_turn = False
                    max_retries -= 1

            else:
                response_match = re.search(self.response_ptrn, llm_res)
                if response_match:
                    response = response_match.group(1).strip()
                    self.history.append(Message("assistant", llm_res))
                    print("\033[92m" + response + "\033[0m")
                    return response
                    user_turn = True
                    max_retries = self.MAX_RETRIES
                else:
                    user_turn = True
                    max_retries -= 1

        return llm_res

if __name__ == '__main__':
    brain = Brain('../hello_world')
    while True:
        user_msg = get_input_from_user()
        brain.run(user_msg)
