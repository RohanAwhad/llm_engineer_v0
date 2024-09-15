import dataclasses
import openai
import os
import re
from typing import Optional
from message import Message


END_OF_INPUT = "<|ROHAN_OUT|>"


def llm_call(model: str, messages: list[Message], temperature: float) -> str:
    """
    Calls the OpenAI API to get a response based on the model and messages provided.

    :param model: The name of the model to call.
    :param messages: A list of Message objects containing the conversation history.
    :param temperature: The temperature setting for randomness in the response.
    :return: The content of the response from the model.
    """
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    )  # Initialize OpenAI client
    res = client.chat.completions.create(
        model=model,
        messages=[dataclasses.asdict(x) for x in messages],
        temperature=temperature,
        max_tokens=4096,
    )
    return res.choices[0].message.content


def get_input_from_user() -> str:
    """
    Collects input from the user until the END_OF_INPUT marker is encountered.
    Additionally, it checks for special markers to read content from a specified file.

    :return: The complete user input as a string.
    """
    print("User >")
    messages = []
    read_plan_pattern = re.compile(
        r"<\|READ_PLAN_START\|>(.*?)<\|READ_PLAN_END\|>", re.DOTALL
    )
    while True:
        user_input = input()
        # Check for <|READ_PLAN_START|> and <|READ_PLAN_END|> keywords
        match = read_plan_pattern.search(user_input)
        if match:
            # Extract the file path
            file_path = match.group(1).strip()
            if os.path.exists(file_path):
                # Read file contents
                with open(file_path, "r") as f:
                    file_content = f.read()
                # Append the file content to the user input
                user_input += "\n" + file_content
                print("PLAN:\n", file_content)
            else:
                print(f"File at path {file_path} does not exist.")
            # Remove the filepath and keywords from the content
            user_input = read_plan_pattern.sub("", user_input)

        messages.append(user_input)
        if END_OF_INPUT in user_input:
            break

    content = "\n".join(messages).replace(END_OF_INPUT, "")
    return content.strip()


def rewrite_file(workspace: str, filename: str, diff: str) -> Optional[str]:
    """
    Its job is to rewrite the file contents based on the cmd.
    The cmd would be either ADD or REMOVE.
      - ADD will be used to integrate the new code block into the current file
      - REMOVE will be used to remove a certain function from the current file

    If the filename does not exist or the file is empty, create a new file and add the contents to it directly.
    If the file has content, then ask the llm to regenerate the whole file with either addition of the code or deletion.
    """
    FILEPATH = f"{workspace}/{filename}"
    if not os.path.exists(FILEPATH):
        with open(FILEPATH, "w") as f:
            pass

    # get the contents of the file
    with open("prompts/file_rewriter.txt", "r") as f:
        sys_prompt = f.read()
    history = [
        Message("system", sys_prompt),
    ]

    with open(FILEPATH, "r") as f:
        file_contents = f.read()
    user_msg = f"CURRENT_FILE_CONTENTS:\n```python\n{file_contents.strip()}\n```\n\n"
    user_msg += f"DIFF:\n```diff\n{diff.strip()}\n```\n\n"

    history.append(Message("user", user_msg))
    print("\033[92m" + str(history[-1]) + "\033[0m")

    code_ptrn = re.compile(
        r"<\|UPDATED_FILE_START\|>(.*?)<\|UPDATED_FILE_END\|>", re.DOTALL
    )
    max_retries = 3
    while max_retries > 0:
        max_retries -= 1
        llm_res = llm_call("gpt-4o-mini", history, temperature=0.8)
        print("\033[94m" + f"Assistant:{llm_res}" + "\033[0m")

        # check if python code exists
        match = re.search(code_ptrn, llm_res)
        if match:
            new_code = match.group(1).strip()
            with open(FILEPATH, "w") as f:
                f.write(new_code)
            return None

    return "Error: was unable to modify the contents"
