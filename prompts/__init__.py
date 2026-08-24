"""
prompts package
-----------------
All LLM system/user prompt content lives here as YAML, never as
hardcoded Python string literals in the agent modules. `prompt_loader.py`
is the single, centralized entry point every agent uses to load prompts.

    logic_extraction.yaml -> LogicExtractionAgent
    rule_synthesis.yaml   -> RuleSynthesizerAgent
"""