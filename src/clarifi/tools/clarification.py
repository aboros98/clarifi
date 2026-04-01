"""Clarification tool — the agent asks the user structured questions with answer options.

When the agent needs more information, it calls this tool to present
a question with clickable options (rendered as buttons in the UI).
The user can pick an option or type a free-text answer.
"""

from langchain_core.tools import tool


@tool
async def ask_user(
    question: str,
    options: list[str] | None = None,
    allow_free_text: bool = True,
    context: str = "",
) -> dict:
    """Pune o întrebare utilizatorului cu opțiuni de răspuns.
    Folosește când ai nevoie de clarificări sau când utilizatorul trebuie să aleagă.
    Args:
        question — întrebarea (în română, natural)
        options — lista de opțiuni (ex: ["TechCorp", "RetailPlus", "StartupVibe"]) sau None dacă e text liber
        allow_free_text — True dacă utilizatorul poate scrie altceva decât opțiunile
        context — context suplimentar pentru UI (ex: "project_selection")

    Returnează structura pe care frontend-ul o va afișa ca butoane/chips.
    Agentul va primi răspunsul utilizatorului în mesajul următor.

    Exemple de utilizare:
    - "La ce proiect te referi?" options=["PRJ-001 Website TechCorp", "PRJ-002 Mobile RetailPlus"]
    - "Ce tip de document e?" options=["Factură", "Contract", "Extras bancar", "Altceva"]
    - "Cu ce salariu brut calculez?" options=None (text liber)
    """

    result = {
        "type": "clarification_request",
        "question": question,
        "allow_free_text": allow_free_text,
        "context": context,
    }

    if options:
        result["options"] = [
            {"label": opt, "value": opt} for opt in options
        ]

    return result
