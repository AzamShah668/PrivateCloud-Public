# =============================================================================
# backend/app/routes/ai_routes.py
# =============================================================================

from fastapi import APIRouter, Depends, BackgroundTasks, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.models.user import UserInDB
from app.services.llm_agent import CloudAgentService

router = APIRouter(prefix="/ai", tags=["Artificial Intelligence Operations"])
agent_instance = CloudAgentService()

class ChatRequestPayload(BaseModel):
    prompt: str

class ChatResponsePayload(BaseModel):
    response: str
    tool_called: str | None
    execution_status: str
    data: dict | list | None = None

@router.post(
    "/chat",
    response_model=ChatResponsePayload,
    status_code=status.HTTP_200_OK,
    summary="Dispatch a natural language instruction set to the cloud infrastructure orchestrator layer"
)
async def process_ai_command(
    payload: ChatRequestPayload,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Accepts text strings, routes them via JSON tool configurations down into 
    active Proxmox client structures, executes processes synchronously or as 
    background threads, and outputs human-readable actions.
    """
    result = await agent_instance.execute_agent_loop(
        user_prompt=payload.prompt,
        current_user=current_user,
        background_tasks=background_tasks
    )
    return result