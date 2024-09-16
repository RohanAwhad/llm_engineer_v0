from textual.app import App, ComposeResult
from textual.widgets import Button, Header, TextArea
from brain import Brain
from message import Message
from tui.brain_widget import BrainWidget
from textual.containers import Container, Horizontal


class LLMEngineer(App):
    CSS_PATH = "./styles.tcss"

    def __init__(self, workspace: str):
        super().__init__()
        self.workspace = workspace
        self.brain = Brain(workspace)

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Header(name=self.workspace)
            yield BrainWidget(self.brain)
            with Horizontal(id="chatbar"):
                yield TextArea(tooltip="Please enter your command...", id="input")
                yield Button("Submit", id="submit_button")

    def on_mount(self) -> None:
        self.brain_widget = self.query_one(BrainWidget)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_button":
            await self.process_input()

    async def process_input(self) -> None:
        user_input = self.query_one("#input", TextArea).text.strip()
        if user_input:
            self.brain.history.append(Message("user", user_input))
            self.brain.run()
            await self.brain_widget.update_messages()
            self.query_one("#input", TextArea).clear()
