from langgraph.graph import StateGraph, END
from app.agents.state import EpisodeState, EpisodeStatus

def transcription_node(state: EpisodeState) -> EpisodeState:
    """
    Transcription node: processes the raw audio source and produces a transcript.
    Does NOT auto-generate metadata (titles, notes, social snippets).
    Halts execution by setting status to PENDING_REVIEW, awaiting explicit user triggers.
    """
    print("Executing transcription_node...")
    transcript = state.get("transcript")
    word_timeline = state.get("word_timeline")

    if not transcript:
        print("No transcript available in state. Setting status to DRAFT.")
        return {
            "raw_audio_url": state.get("raw_audio_url"),
            "transcript": "",
            "generated_content": state.get("generated_content") or {"titles": [], "notes": "", "social_snippets": []},
            "status": EpisodeStatus.DRAFT,
            "human_feedback": state.get("human_feedback"),
            "word_timeline": word_timeline or [],
            "edit_decision_list": state.get("edit_decision_list") or [],
            "selected_llm_config": state.get("selected_llm_config") or {}
        }

    return {
        "raw_audio_url": state.get("raw_audio_url"),
        "transcript": transcript,
        "generated_content": state.get("generated_content") or {"titles": [], "notes": "", "social_snippets": []},
        "status": EpisodeStatus.PENDING_REVIEW,
        "human_feedback": state.get("human_feedback"),
        "word_timeline": word_timeline or [],
        "edit_decision_list": state.get("edit_decision_list") or [],
        "selected_llm_config": state.get("selected_llm_config") or {}
    }

# Build workflow: transcription → PENDING_REVIEW (awaiting human trigger)
workflow = StateGraph(EpisodeState)
workflow.add_node("transcription", transcription_node)
workflow.set_entry_point("transcription")
workflow.add_edge("transcription", END)

# Compile graph
app_graph = workflow.compile()
