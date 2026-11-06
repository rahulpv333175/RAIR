import re

# 1. Update query_planner.py
with open("src/rair/query_planner.py", "r", encoding="utf-8") as f:
    qp_text = f.read()

# Replace user_prompt construction and payload parsing in query_planner.py
target_qp = """        user_prompt = (
            f"Original question:\\n"
            f"{state.question}\\n\\n"
            f"Current gap:\\n"
            f"{gap.gap_id}: "
            f"{gap.description}\\n\\n"
            f"Verified facts:\\n"
            f"{verified_facts}\\n\\n"
            f"Previous query attempts:\\n"
            f"{query_history}\\n\\n"
            "Generate exactly one new BM25 "
            "search query for the current gap."
        )

        response = self.client.chat(
            RAIR_QUERY_PLANNER_SYSTEM_PROMPT,
            user_prompt,
            schema=RAIR_QUERY_PLANNER_SCHEMA,
            temperature=0.0,
        )

        payload = response.json_object()

        previous_queries = [
            attempt.query
            for attempt in state.query_history
        ]"""

replacement_qp = """        previous_queries = [
            attempt.query
            for attempt in state.query_history
        ]

        forbidden_section = ""
        if previous_queries:
            forbidden_list = "\\n".join(f"- {q}" for q in sorted(set(previous_queries)))
            forbidden_section = f"Forbidden queries (DO NOT repeat these or close variations):\\n{forbidden_list}\\n\\n"

        user_prompt = (
            f"Original question:\\n"
            f"{state.question}\\n\\n"
            f"Current gap:\\n"
            f"{gap.gap_id}: "
            f"{gap.description}\\n\\n"
            f"Verified facts:\\n"
            f"{verified_facts}\\n\\n"
            f"Previous query attempts:\\n"
            f"{query_history}\\n\\n"
            f"{forbidden_section}"
            "Generate exactly one new BM25 "
            "search query for the current gap."
        )

        response = self.client.chat(
            RAIR_QUERY_PLANNER_SYSTEM_PROMPT,
            user_prompt,
            schema=RAIR_QUERY_PLANNER_SCHEMA,
            temperature=0.0,
        )

        payload = response.json_object()"""

# Normalize CRLF for match
qp_norm = qp_text.replace("\r\n", "\n")
if target_qp in qp_norm:
    qp_norm = qp_norm.replace(target_qp, replacement_qp)
    with open("src/rair/query_planner.py", "w", encoding="utf-8", newline="\n") as f:
        f.write(qp_norm)
    print("query_planner.py patched successfully!")
else:
    print("ERROR: target_qp not found in query_planner.py!")

# 2. Update controller.py
with open("src/rair/controller.py", "r", encoding="utf-8") as f:
    ctrl_text = f.read()

target_ctrl = """            while state.current_round < state.max_rounds and not state.is_complete():
                if not any(g.gap_id not in stalled_gaps for g in state.actionable_gaps()):"""

replacement_ctrl = """            while state.current_round < state.max_rounds and not state.is_complete():
                if self.client.budget is not None:
                    remaining_non_final = (self.client.budget.max_llm_calls - 1) - self.client.budget.llm_calls
                    if remaining_non_final < 4 and state.verified_facts:
                        stop_reason = "budget_exhausted"
                        break
                if not any(g.gap_id not in stalled_gaps for g in state.actionable_gaps()):"""

ctrl_norm = ctrl_text.replace("\r\n", "\n")
if target_ctrl in ctrl_norm:
    ctrl_norm = ctrl_norm.replace(target_ctrl, replacement_ctrl)
    with open("src/rair/controller.py", "w", encoding="utf-8", newline="\n") as f:
        f.write(ctrl_norm)
    print("controller.py patched successfully!")
else:
    print("ERROR: target_ctrl not found in controller.py!")

