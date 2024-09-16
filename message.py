import dataclasses


@dataclasses.dataclass
class Message:
    role: str
    content: str

    def __str__(self) -> str:
        return f"[{self.role}]: {self.content}"

    def __repr__(self) -> str:
        return str(self)

@dataclasses.dataclass
class MessageToPrint:
    title: str
    content: str
    color: str

