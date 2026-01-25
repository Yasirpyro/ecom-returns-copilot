from __future__ import annotations
import os
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import GraphState

load_dotenv()

FAST_MODEL = os.getenv("FAST_MODEL", "qwen2.5:3b-instruct")
QUALITY_MODEL = os.getenv("QUALITY_MODEL", "qwen2.5:7b-instruct")


SYSTEM = """You are assisting an ecommerce support agent AFTER a human review decision.
You must:
1) Produce a customer-facing message.
2) Produce a JSON array of next actions for the internal system.

Rules:
- Use only the provided order facts, decision, human decision, and policy excerpts.
- Keep customer message concise and respectful.
- If more info is requested, list exactly what is needed (e.g., photos, close-up, label).
- Do not mention internal IDs.

Output format (MUST be valid JSON):
{
  "customer_reply": "...",
  "next_actions": [
    { "type": "...", "summary": "...", "sku": "...", "qty": 1, "refund_amount": 0, "refund_method": "original_payment", "return_shipping_fee_waived": false }
  ]
}
"""


def finalize_case_node(state: GraphState) -> GraphState:
    # Choose model based on complexity
    complexity = int(state.get("complexity") or 3)
    model_name = QUALITY_MODEL if complexity >= 4 else FAST_MODEL

    llm = ChatOllama(
        model=model_name,
        temperature=0.2,
        top_p=0.9,
        repeat_penalty=1.1,
        num_predict=260 if model_name == QUALITY_MODEL else 200,
    )

    docs = state.get("policy_docs", [])[:2]
    policy_text = "\n\n".join([f"SOURCE: {d.metadata.get('source')}\n{d.page_content}" for d in docs])

    prompt = f"""
Order facts:
{state.get("order")}

AI Decision JSON:
{state.get("decision")}

Human decision:
{state.get("human_decision")}  # one of approved/denied/more_info_requested
Human notes:
{state.get("human_notes")}

Photo URLs:
{state.get("photo_urls")}

Policy excerpts:
{policy_text}
""".strip()

    resp = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=prompt)])
    state["finalize_output_raw"] = resp.content
    return state