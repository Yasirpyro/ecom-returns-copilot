from __future__ import annotations

from app.llm.openrouter import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import GraphState

SYSTEM = """You are a support-ops assistant generating the FINAL outcome after a human decision.

You MUST output valid JSON only (no markdown, no extra text).

You are given:
- enriched order facts (includes items with sku, qty, product fields)
- prior AI decision JSON
- human decision (approved/denied/more_info_requested)
- human notes
- photo URLs (may exist)
- policy excerpts

Policy logic to apply for next actions when human_decision == "approved":
- Preferred: issue_replacement of the exact SKU(s) affected
- If replacement is not possible due to out-of-stock, issue_refund instead
For this demo: assume replacement IS possible unless human_notes contains "out of stock".

When human_decision == "denied":
- Do not promise a refund/replacement.
- Provide a concise explanation and, if applicable, mention standard return option (only if within return window is already indicated by the AI decision; if not sure, say it requires review).

When human_decision == "more_info_requested":
- Ask specifically for what info is missing (photos, angles, order_id, sku, care details).

Output JSON schema:
{
  "customer_reply": "string",
  "next_actions": [
    {
      "type": "issue_replacement|issue_refund|request_more_info|manual_agent_followup",
      "summary": "string",
      "sku": "string or null",
      "qty": integer or null,
      "refund_amount": number or null,
      "refund_method": "original_payment|store_credit or null"
    }
  ]
}
"""


def finalize_case_node(state: GraphState) -> GraphState:
    profile = state.get("llm_profile")
    llm = get_llm("repair" if profile == "repair" else "finalize")

    docs = (state.get("policy_docs") or [])[:2]
    policy_text = "\n\n".join([f"SOURCE: {d.metadata.get('source')}\n{d.page_content}" for d in docs])

    if state.get("force_minimal_prompt"):
      prompt = f"""
  order:
  {state.get("order")}

  ai_decision:
  {state.get("decision")}

  human_decision:
  {state.get("human_decision")}

  human_notes:
  {state.get("human_notes")}

  photo_urls:
  {state.get("photo_urls")}
  """.strip()
    else:
      prompt = f"""
order:
{state.get("order")}

ai_decision:
{state.get("decision")}

human_decision:
{state.get("human_decision")}

human_notes:
{state.get("human_notes")}

photo_urls:
{state.get("photo_urls")}

policy_excerpts:
{policy_text}
""".strip()

    system = SYSTEM
    if state.get("force_json_only"):
        system = SYSTEM + "\n\nSTRICT JSON ONLY. Return only valid JSON without any markdown or prose."

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    state["finalize_output_raw"] = (resp.content or "").strip()
    return state