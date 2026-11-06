with open("src/rair/synthesizer.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        user_prompt = (
            f"Original question:\\n"
            f"{question}\\n\\n"
            f"Verified facts:\\n"
            f"{verified_facts}\\n\\n"
            f"Unresolved gaps:\\n"
            f"{unresolved_gaps}\\n\\n"
            "Answer only if the verified facts "
            "are sufficient. Unresolved gaps are planning hints, not a veto: answer "
            "if the facts already support the complete answer. Never fill a missing link."
        )"""

replacement = """        user_prompt = (
            f"Original question:\\n"
            f"{question}\\n\\n"
            f"Verified facts:\\n"
            f"{verified_facts}\\n\\n"
            f"Unresolved gaps:\\n"
            f"{unresolved_gaps}\\n\\n"
            "Answer if the verified facts identify the requested entity or provide the answer. "
            "Unresolved gaps are planning hints, not a veto: if a fact answers the question, output the answer. Never fill a missing link."
        )"""

text_norm = text.replace("\r\n", "\n")
if target in text_norm:
    text_norm = text_norm.replace(target, replacement)
    with open("src/rair/synthesizer.py", "w", encoding="utf-8", newline="\n") as f:
        f.write(text_norm)
    print("synthesizer.py updated successfully!")
else:
    print("ERROR: target not found in synthesizer.py")

