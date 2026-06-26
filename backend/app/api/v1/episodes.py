from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional
from app.agents.state import EpisodeState, EpisodeStatus
from app.agents.graph import app_graph
from app.models.episode import EpisodeResponse

router = APIRouter()

@router.post("/ingest", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def ingest_episode(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Ingest an episode by providing either an audio file or an audio URL.
    This initializes the EpisodeState and triggers the transcription flow.
    """
    if not file and not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either an audio file or a URL must be provided."
        )

    audio_path_or_url = url
    if file:
        audio_path_or_url = f"file://{file.filename}"
        # In a production system, we would save the uploaded file to storage (e.g. S3 or a local temp file)
        # for processing by transcription nodes.

    # 1. Initialize EpisodeState
    initial_state = EpisodeState(
        raw_audio_url=audio_path_or_url,
        transcript=None,
        generated_content={"titles": [], "notes": "", "social_snippets": []},
        status=EpisodeStatus.DRAFT,
        human_feedback=None
    )

    # 2. Trigger the LangGraph execution graph
    try:
        result = await app_graph.ainvoke(initial_state)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution failed: {str(e)}"
        )
