import dataclasses
import difflib
import json
import openai
import anthropic
import os
import re
import requests  # Importing requests library for making HTTP requests
from typing import Optional, Callable, List
from message import Message, MessageToPrint


END_OF_INPUT = "<|ROHAN_OUT|>"

@dataclasses.dataclass
class SearchResult:
    """
    Dataclass to represent the search results from Brave Search API.
    
    :param title: The title of the search result.
    :param url: The URL of the search result.
    :param description: A brief description of the search result.
    :param extra_snippets: Additional snippets related to the search result.
    """
    title: str
    url: str
    description: str
    extra_snippets: list

    def __str__(self) -> str:
        """
        Returns a string representation of the search result.

        :return: A string representation of the search result.
        """
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"Description: {self.description}\n"
            f"Extra Snippets: {', '.join(self.extra_snippets)}"
        )


def llm_call(model: str, messages: list[Message], temperature: float, provider: str = 'openai', stop_tokens: str | list[str] | None = None, max_tokens: int = 4096) -> str:
    """
    Calls the OpenAI API to get a response based on the model and messages provided.

    :param model: The name of the model to call.
    :param messages: A list of Message objects containing the conversation history.
    :param temperature: The temperature setting for randomness in the response.
    :return: The content of the response from the model.
    """
    # loop over messages, and see if consecutive user or assistant messages are present, if yes, then merge them into one with '\n\n' as sep
    merged_messages = []
    current_message = None

    for message in messages:
        if current_message is not None and message.role == current_message.role:
            if isinstance(current_message.content, list):
                if isinstance(message.content, list):
                    current_message.content += message.content
                else:
                    current_message.content += [dict(type='text', text=message.content),]
            else:
                if isinstance(message.content, list):
                    current_message.content = [dict(type='text', text=current_message.content),] + message.content
                else:
                    current_message.content += '\n' + message.content
        else:
            if current_message:
                merged_messages.append(current_message)
            current_message = message

    if current_message:
        merged_messages.append(current_message)
    messages = merged_messages

    if provider == 'anthropic':
        client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        if messages[0].role == 'system':
            system_msg = messages[0].content
            messages = messages[1:]
        # Send a message to Claude 3.5 Sonnet
        response = client.messages.create(
            model=model,
            system=system_msg,
            max_tokens=4096,
            messages=[dataclasses.asdict(x) for x in messages],
        )
        # Print the response
        return response.content[0].text
    if provider == 'openai':
        client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"]
        )  # Initialize OpenAI client
    elif provider == 'together':
        client = openai.OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url='https://api.together.xyz/v1'
        )
        new_messages = []
        for x in messages:
            content = []
            if isinstance(x.content, list):
                for c in x.content:
                    if c['type'] == 'image':
                        raise ValueError("Together doesn't have an image processor")
                    content.append(c['text'].strip())
                new_messages.append(Message(x.role, ('\n'.join(content)).strip()))
            else:
                new_messages.append(x)
        messages = new_messages

    if stop_tokens is None: stop_tokens = []
    elif isinstance(stop_tokens, str): stop_tokens = [stop_tokens, ]
    ret = ''
    for _ in range(3):
        res = client.chat.completions.create(
            model=model,
            messages=[dataclasses.asdict(x) for x in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_tokens,
        )
        # check for finish reason, and re-request, if needed
        finish_reason = res.choices[0].finish_reason
        if finish_reason == 'length':
            messages = messages + [Message(role='assistant', content=res.choices[0].message.content), ]
        else:
            return ret + res.choices[0].message.content


def search_brave(query: str, api_key: str, count: int = 10) -> List[SearchResult]:
    """
    Searches the web using Brave Search API and returns structured search results.

    :param query: The search query string.
    :param api_key: The API key for authentication with the Brave Search service.
    :param count: The number of search results to return.
    :return: A list of SearchResult objects containing the search results.
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "count": count
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raises an exception for HTTP errors
    results_json = response.json()
    
    results = []
    for item in results_json.get('web', {}).get('results', []):
        result = SearchResult(
            title=item.get('title', ''),
            url=item.get('url', ''),
            description=item.get('description', ''),
            extra_snippets=item.get('extra_snippets', [])
        )
        results.append(result)

    return results




def get_input_from_user() -> Message:
    """
    Collects input from the user until the END_OF_INPUT marker is encountered.
    Additionally, it checks for special markers to read content from a specified file and image.
    
    :return: The complete user input as a Message object with structured content.
    """
    print('User >')
    content_list = []
    read_plan_pattern = re.compile(r"<\|READ_PLAN_START\|>(.*?)<\|READ_PLAN_END\|>", re.DOTALL)
    read_image_pattern = re.compile(r"<\|READ_IMAGE_START\|>(.*?)<\|READ_IMAGE_END\|>", re.DOTALL)

    while True:
        user_input = input()
        
        # Check for <|READ_PLAN_START|> and <|READ_PLAN_END|> keywords
        plan_match = read_plan_pattern.search(user_input)
        if plan_match:
            # Extract the file path and read the content
            file_path = plan_match.group(1).strip()
            plan_content = ""
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    plan_content = f.read()
                print('PLAN:\n', plan_content)
            else:
                print(f"File at path {file_path} does not exist.")
            # Append the file content to content list
            content_list.append({"type": "text", "text": user_input.replace(plan_match.group(0), '').strip()})
            content_list.append({"type": "text", "text": plan_content})
            user_input = read_plan_pattern.sub('', user_input)

        # Check for <|READ_IMAGE_START|> and <|READ_IMAGE_END|> keywords
        image_match = read_image_pattern.search(user_input)
        if image_match:
            file_path = image_match.group(1).strip()
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    image_content = f.read()
                    import base64
                    base64_image = base64.b64encode(image_content).decode('utf-8')
                # Updated line to include the image data URL prefix
                content_list.append({"type": "image_url", "image_url": {'url': f"data:image/png;base64,{base64_image}"}})
                #print('IMAGE:\n', base64_image)
            else:
                print(f"File at path {file_path} does not exist.")
            user_input = read_image_pattern.sub('', user_input)

        if END_OF_INPUT in user_input: 
            if user_input.strip():
                content_list.append({"type": "text", "text": user_input.replace(END_OF_INPUT, '').strip()})
            break
        if user_input.strip():
            content_list.append({"type": "text", "text": user_input.strip()})


    
    return Message(role="user", content=content_list)


def rewrite_file(workspace: str, filename: str, diff: str, update_logs: Callable | None = None) -> Optional[str]:
    """
    Its job is to rewrite the file contents based on the cmd.
    The cmd would be either ADD or REMOVE.
      - ADD will be used to integrate the new code block into the current file
      - REMOVE will be used to remove a certain function from the current file

    If the filename does not exist or the file is empty, create a new file and add the contents to it directly.
    If the file has content, then ask the llm to regenerate the whole file with either addition of the code or deletion.
    """
    FILEPATH = f"{workspace}/{filename}"

    if not os.path.exists(os.path.dirname(FILEPATH)):
        os.makedirs(os.path.dirname(FILEPATH))

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
        init_file_contents = f.read()
    user_msg = f"CURRENT_FILE_CONTENTS:\n```\n{init_file_contents.strip()}\n```\n\n"
    user_msg += f"DIFF:\n```diff\n{diff.strip()}\n```\n\n"

    history.append(Message("user", user_msg))
    print("\033[92m" + str(history[-1]) + "\033[0m")
    if update_logs: update_logs(MessageToPrint('File Rewriter Input', str(history[-1]), "light_salmon3"))

    code_ptrn = re.compile(
        r"<\|UPDATED_FILE_START\|>(.*?)<\|UPDATED_FILE_END\|>", re.DOTALL
    )
    max_retries = 3
    while max_retries > 0:
        max_retries -= 1
        llm_res = llm_call("gpt-4o-mini", history, temperature=0.8)
        print("\033[94m" + f"Assistant:{llm_res}" + "\033[0m")
        if update_logs: update_logs(MessageToPrint('File Rewriter Output', llm_res, "light_sky_blue3"))
        matches = list(re.finditer(code_ptrn, llm_res))

        if matches:
            # Get the longest match
            longest_match = max(matches, key=lambda match: len(match.group(0)))
            new_code = longest_match.group(1).strip()
            if new_code.startswith('```'): new_code = '\n'.join(new_code.split('\n')[1:])
            if new_code.endswith('```'): new_code = '\n'.join(new_code.split('\n')[:-1])
            
            with open(FILEPATH, "w") as f:
                f.write(new_code)

            with open(FILEPATH, 'r') as f:
                post_file_contents = f.read()

            diff = difflib.unified_diff(
                init_file_contents.splitlines(),
                post_file_contents.splitlines(),
                fromfile="before",
                tofile="after",
            )
            print("\n".join(diff))
            return f"{filename} was successfully updated"


    return "Error: was unable to modify the contents"


# a funciton that will take in messages list and ask llm to summarize the conversation uptill now into 3 main sections: Main Objective, Completed Tasks, In-Progress Tasks
def summarize_conversation(model: str, messages: list[Message], provider: str = "openai") -> str:
    """
    Asks the LLM to summarize the conversation into 3 main sections: Main Objective, Completed Tasks, In-Progress Tasks.

    :param messages: A list of Message objects containing the conversation history.
    :return: The summary of the conversation from the LLM.
    """
    sys_prompt = '''
You are a language model. I need you to summarize a conversation between a user and an assistant which is also a LM. The reason to summarize is because of context length limit of the assistant model.

Keeping this in mind, I need you to summarize the conversation thats given by the current user. The conversation chain also includes the system prompt, and that is because I need you to summarize such that the task the assistant is performing doesn't get disturbed. There might also come a time, that the there is summarization already present, I need you to consider that too.

Because the conversation might go on for hours on end, I need you to summarize the conversation such that the older completed tasks take up less context, compared to the most recent ongoing ones.

Also, another important caveat, even with summarized context, the last 2 messages are still sent to the model, because they need to be concrete and detailed. So, when summarizing keep that in mind. You do not have to return those messages, the backend system will append them by itself. You need to just summarize.
'''
    history = [
        Message("system", sys_prompt.strip()),
        Message("user", json.dumps([dataclasses.asdict(x) for x in messages])),
    ]

    max_retries = 3
    while max_retries > 0:
        max_retries -= 1
        llm_res = llm_call(model, history, temperature=0.8, provider=provider, max_tokens=1024)
        print("\033[94m" + f"Summarization Assistant:{llm_res}" + "\033[0m")
        return llm_res

    return "Error: was unable to summarize the conversation"


if __name__ == '__main__':
    # Example usage:
    with open('conversationData.json', 'r') as f:
        chat = json.load(f)
    messages = [Message('system', 'you are a helpful assistant. Help users with their queries'), ] + [Message(x['role'], x['content']) for x in chat]
    print(summarize_conversation('gpt-4o', messages))
