from dotenv import load_dotenv
load_dotenv()
from agents.synthesizer import SynthesizerAgent


def test_synthesize_basic():
    agent = SynthesizerAgent()
    fake_extraction = [{
        "conditions": ["overdue_days <= 90 -> STANDARD", "overdue_days > 90 -> SUBSTANDARD"],
        "tables_read": [{"table": "LOAN_ACCOUNT", "columns": ["overdue_days"],
                          "condition": "account_id = p_account_id"}],
        "tables_written": [{"table": "LOAN_ACCOUNT", "operation": "update",
                             "condition": "account_id = p_account_id"}],
        "calculations": [],
        "loops": [],
        "notes": ""
    }]
    result = agent.synthesize(
        "classify_npa_and_provision", "procedure", ["p_account_id"], fake_extraction
    )
    assert "purpose_summary" in result
    assert len(result["purpose_summary"]) > 0


if __name__ == '__main__':
    test_synthesize_basic()
    print("Synthesizer test passed (requires GROQ_API_KEY in .env)")
