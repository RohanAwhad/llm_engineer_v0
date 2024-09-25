from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from jupyter_client import KernelManager

app = FastAPI()
sessions: Dict[str, KernelManager] = {}


class CreateSessionResponse(BaseModel):  # type: ignore
  session_id: str


class ExecuteCodeRequest(BaseModel):  # type: ignore
  code: str
  session_id: str


@app.post("/create_session", response_model=CreateSessionResponse)  # type: ignore
def create_session() -> CreateSessionResponse:
  session_id = str(uuid4())
  km = KernelManager()
  km.start_kernel()
  sessions[session_id] = km
  return CreateSessionResponse(session_id=session_id)


@app.post("/execute_code")  # type: ignore
def execute_code(request: ExecuteCodeRequest) -> str:
  session_id = request.session_id
  code = request.code
  if session_id not in sessions:
    raise HTTPException(status_code=404, detail="Session not found")
  km = sessions[session_id]
  client = km.client()
  msg_id = client.execute(code, timeout=None)
  result = ''
  while True:
    reply = client.get_iopub_msg(timeout=None)
    if reply['msg_type'] == 'status' and reply['content']['execution_state'] == 'idle':
      break
    elif reply['msg_type'] == 'execute_result':
      result = reply['content']
    elif reply['msg_type'] == 'stream':
      result = reply['content'].get('name', '')
      if 'text' in reply['content']:
        result = reply['content']['text']
  return result


@app.on_event("shutdown")  # type: ignore
def shutdown_event() -> None:
  for session_id, km in sessions.items():
    km.shutdown_kernel()
