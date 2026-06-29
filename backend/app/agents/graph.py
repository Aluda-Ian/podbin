from langgraph.graph import StateGraph, END
from app.agents.state import EpisodeState

def transcription_node(state: EpisodeState) -> EpisodeState:
    """
    Transcription node that processes the raw audio source.
    In the initial setup, it updates the state and provides placeholder data.
    """
    print("Executing transcription_node...")
    return {
        "raw_audio_url": state.get("raw_audio_url"),
        "transcript": state.get("transcript") or "This is a placeholder transcript simulated by the transcription node.",
        "generated_content": {
            "titles": ["Default Episode Title"],
            "notes": "Default show notes generated from the transcript.",
            "social_snippets": ["Snippet 1 from the episode.", "Snippet 2 from the episode."]
        },
        "status": state.get("status"),
        "human_feedback": state.get("human_feedback"),
        "word_timeline": state.get("word_timeline") or [],
        "edit_decision_list": state.get("edit_decision_list") or [],
        "selected_llm_config": state.get("selected_llm_config") or {}
    }

# Build workflow
workflow = StateGraph(EpisodeState)
workflow.add_node("transcription", transcription_node)
workflow.set_entry_point("transcription")
workflow.add_edge("transcription", END)

# Compile graph
app_graph = workflow.compile()
