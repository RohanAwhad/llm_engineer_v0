import pickle  # Importing pickle to handle serialization
import os  # Importing os for file path operations
import re
import base64

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.geometry import Size
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Header, TextArea, Static, Pretty, ListView, ListItem
from rich import panel, text

from brain import Brain
from message import Message, MessageToPrint



class MessageLabel(Static):
    def __init__(self, message: MessageToPrint):
        super().__init__()
        self.msg = message

    def render(self):
        if isinstance(self.msg.content, list):
            content = []
            for item in self.msg.content:
                if item['type'] == 'text': content.append(item['text'])
                elif item['type'] == 'image_url': content.append('Image: ' + item['image_url']['url'][:50] + ' ...')
            content = '\n'.join(content)
        else:
            content = str(self.msg.content)
        return panel.Panel(
            f'[{self.msg.color}]{content}[/{self.msg.color}]',
            border_style=f"bold {self.msg.color}",
            title=self.msg.title,
        )


class BrainWidget(Widget):
    message_list = reactive([])

    def __init__(self):
        super().__init__()
        self.styles.height = "1fr"
        self.styles.width = "100%"
        self.virtual_size = Size(0, 8)

    def compose(self):
        with ScrollableContainer():
            yield ListView()

    def watch_message_list(self, new_msgs):
        list_view = self.query_one(ListView)
        list_view.clear()
        for msg in new_msgs:
            list_view.append(ListItem(MessageLabel(msg)))


class LLMEngineer(App):
    CSS_PATH = "./styles.tcss"

    def __init__(self, workspace: str):
        super().__init__()
        self.workspace = workspace
        self.brain = Brain(workspace)
        self.history_file = os.path.join(workspace, '.brain_history')  # Path to store brain history
        self.message_list_file = os.path.join(workspace, '.brain_message_list')  # Path to store message list

    def load_brain_history(self):
        """Load brain history from a file if it exists."""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'rb') as f:
                self.brain.history = pickle.load(f)

    def load_message_list(self):
        """Load message list from a file if it exists."""
        if os.path.exists(self.message_list_file):
            with open(self.message_list_file, 'rb') as f:
                self.brain_widget.message_list = pickle.load(f)
        else:
            self.brain_widget.message_list = []  # Initialize with an empty list if no file exists

    def compose(self) -> ComposeResult:
        self.brain_widget = BrainWidget()

        yield Header(name=self.workspace)
        yield self.brain_widget
        with Horizontal(id="chatbar"):
            yield TextArea(tooltip="Please enter your command...", id="input")
            yield Button("Submit", id="submit_button")

    def on_mount(self):
        self.load_brain_history()  # Load historical data on initialization
        self.load_message_list()  # Load previous messages on initialization
        self.log_container = self.query_one(BrainWidget).message_list

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_button":
            self.process_input()

    def update_message_list(self, new_item):
        self.brain_widget.message_list = self.brain_widget.message_list + [new_item,]

    def process_input(self) -> None:
        user_input = self.query_one("#input", TextArea).text.strip()
        if user_input:
            msg = Message('user', preprocess_user_input(user_input))
            self.update_message_list(MessageToPrint('User', msg.content, 'cyan'))
            res = self.brain.run(msg, update_logs=self.update_message_list)
            self.update_message_list(MessageToPrint('Brain', res, 'bright_green'))
            self.query_one("#input", TextArea).clear()
            self.save_brain_history()  # Save the brain history after processing input
            self.save_message_list()  # Save the message list after processing input

    def save_brain_history(self):
        """Save brain history to a file."""
        with open(self.history_file, 'wb') as f:
            pickle.dump(self.brain.history, f)

    def save_message_list(self):
        """Save message list to a file."""
        with open(self.message_list_file, 'wb') as f:
            pickle.dump(self.brain_widget.message_list, f)


def preprocess_user_input(user_input):
    # Post-processing step to handle READ_PLAN and READ_IMAGE tokens
    content_list = []
    read_plan_pattern = re.compile(r"<\|READ_PLAN_START\|>(.*?)<\|READ_PLAN_END\|>", re.DOTALL)
    read_image_pattern = re.compile(r"<\|READ_IMAGE_START\|>(.*?)<\|READ_IMAGE_END\|>", re.DOTALL)

    # Combine both patterns to match READ_PLAN and READ_IMAGE in order of appearance
    combined_pattern = re.compile(r"(<\|READ_PLAN_START\|>.*?<\|READ_PLAN_END\|>|<\|READ_IMAGE_START\|>.*?<\|READ_IMAGE_END\|>)", re.DOTALL)
    matches = combined_pattern.finditer(user_input)
    
    last_index = 0

    # Process matches sequentially as they appear in the text
    for match in matches:
        # Get the text before the current match
        before_match = user_input[last_index:match.start()].strip()
        if before_match:
            # Add any plain text before the matched tag
            content_list.append({"type": "text", "text": before_match})

        tag_content = match.group(1).strip()

        # Process READ_PLAN tag
        if tag_content.startswith("<|READ_PLAN_START|>"):
            plan_match = read_plan_pattern.search(tag_content)
            if plan_match:
                file_path = plan_match.group(1).strip()
                plan_content = ""
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        plan_content = f.read()
                # Add the plan content as a separate item
                content_list.append({"type": "text", "text": plan_content})
        
        # Process READ_IMAGE tag
        elif tag_content.startswith("<|READ_IMAGE_START|>"):
            image_match = read_image_pattern.search(tag_content)
            if image_match:
                file_path = image_match.group(1).strip()
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        image_content = f.read()
                        base64_image = base64.b64encode(image_content).decode('utf-8')
                    # Add the image content as a separate item
                    content_list.append({"type": "image_url", "image_url": {'url': f"data:image/png;base64,{base64_image}"}})

        # Update the last index to the end of the current match
        last_index = match.end()

    # Add any remaining text after the last tag
    after_last_match = user_input[last_index:].strip()
    if after_last_match:
        content_list.append({"type": "text", "text": after_last_match})

    return content_list
