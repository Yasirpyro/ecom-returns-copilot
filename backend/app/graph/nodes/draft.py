from __future__ import annotations
from app.llm.openrouter import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import GraphState


SYSTEM = """You write customer support replies for an ecommerce brand.

Hard rules:
- Do not invent policies or steps not present in the provided policy excerpts.
- Keep the reply short and actionable (max ~8 lines).
- If photos are required, clearly request: photo of defect + order_id + SKU.
- If a fee applies, explain it as "deducted from the refund" (not paid upfront), unless policy explicitly says otherwise.
- Do not mention internal policy IDs; those are for internal audit only.
"""

def draft_node(state: GraphState) -> GraphState:
    profile = state.get("llm_profile", "draft")

    if profile == "repair":
        llm = get_llm("repair")
    else:
        llm = get_llm(
            "draft",
            temperature=state.get("draft_temperature"),
            max_tokens=state.get("draft_max_tokens"),
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