import dataclasses
import openai
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
    user_msg = f"CURRENT_FILE_CONTENTS:\n```\n{file_contents.strip()}\n```\n\n"
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

        # check if python code exists
        matches = list(re.finditer(code_ptrn, llm_res))

        if matches:
            # Get the last match
            last_match = matches[-1]
            new_code = last_match.group(1).strip()
            
            with open(FILEPATH, "w") as f:
                f.write(new_code)
            
            return None

    return "Error: was unable to modify the contents"


if __name__ == '__main__':
    # Example usage:
    import os
    api_key = os.environ['BRAVE_SEARCH_AI_API_KEY']
    results = search_brave("What is the fastest way to sort a large dataset in Python?", api_key)
    for result in results:
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Description: {result.description}")
        if result.extra_snippets:
            print("Extra Snippets:")
            for snippet in result.extra_snippets:
                print(snippet)
        print("\n")

