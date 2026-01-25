from __future__ import annotations
import os
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import GraphState


load_dotenv()

FAST_MODEL = os.getenv("FAST_MODEL", "qwen2.5:3b-instruct")
QUALITY_MODEL = os.getenv("QUALITY_MODEL", "qwen2.5:7b-instruct")


SYSTEM = """You write customer support replies for an ecommerce brand.

Hard rules:
- Do not invent policies or steps not present in the provided policy excerpts.
- Keep the reply short and actionable (max ~8 lines).
- If photos are required, clearly request: photo of defect + order_id + SKU.
- If a fee applies, explain it as "deducted from the refund" (not paid upfront), unless policy explicitly says otherwise.
- Do not mention internal policy IDs; those are for internal audit only.
"""


def _model_for_profile(profile: str) -> str:
    if profile == "quality":
        return QUALITY_MODEL
    return FAST_MODEL


def draft_node(state: GraphState) -> GraphState:
    profile = state.get("llm_profile", "fast")
    model_name = _model_for_profile(profile)

    # Speed/quality knobs for CPU:
    # - low temperature reduces rambling and latency
    # - num_predict caps output length (big speed win)
    # Note: exact parameter names depend on Ollama; "num_predict" is commonly supported.
    llm = ChatOllama(
        model=model_name,
        temperature=0.25 if profile == "quality" else 0.2,
        top_p=0.9,
        repeat_penalty=1.1,
        num_predict=220 if profile == "quality" else 180,
    )

    # Only pass the top 2 policy docs (keeps prompt small)
    docs = state.get("policy_docs", [])[:2]
    policy_text = "\n\n".join(
        [f"SOURCE: {d.metadata.get('source')}\n{d.page_content}" for d in docs]
    )

    decision = state.get("decision", {})

    prompt = f"""
Order ID: {state.get("order_id")}
Reason: {state.get("reason")}
Customer message: {state.get("customer_message") or ""}

Decision JSON:
{decision}

Policy excerpts:
{policy_text}

Write the customer reply.
""".strip()

    resp = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=prompt)])
    state["customer_reply"] = resp.content.strip()
    return state