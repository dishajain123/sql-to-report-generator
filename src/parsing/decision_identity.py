"""SQL identity normalization that preserves literals and decision order."""
import re


def decision_text_key(value):
    parts = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\[(?:\]\]|[^\]])*\])", str(value or ''))
    return ''.join(part if index % 2 else re.sub(r'\s+', ' ', part).casefold()
                   for index, part in enumerate(parts)).strip()
