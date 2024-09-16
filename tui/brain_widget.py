from textual.app import ComposeResult
from textual.containers import VerticalScroll
from brain import Brain
from textual.widgets import Static
from message import Message
from textual.geometry import Size


class MessageLabel(Static):
    def __init__(self, message: Message):
        super().__init__(str(message))
        self.styles.width = "100%"
        self.styles.padding = (1, 2)
        self.styles.border = ("heavy", "white")
        self.styles.margin = (0, 0, 1, 0)


class BrainWidget(VerticalScroll):
    def __init__(self, brain: Brain):
        super().__init__()
        self.brain = brain
        self.styles.height = "1fr"
        self.styles.width = "100%"
        self.virtual_size = Size(0, 8)

    def compose(self) -> ComposeResult:
        for i, message in enumerate(self.brain.history):
            if i == 0:
                # don't show the prompt
                yield MessageLabel(Message("system", "Please enter your prompt..."))
                continue
            yield MessageLabel(message)

    async def update_messages(self) -> None:
        self.remove_children()
        for i, message in enumerate(self.brain.history):
            if i == 0:
                # don't show the prompt
                self.mount(
                    MessageLabel(Message("system", "Please enter your prompt..."))
                )
                continue
            self.mount(MessageLabel(message))
