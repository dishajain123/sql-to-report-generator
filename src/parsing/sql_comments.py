"""Remove SQL comments without changing literals or source coordinates."""


def executable_sql(source: str) -> str:
    text = str(source or "")
    result = list(text)
    i = 0
    while i < len(text):
        if text[i] in "'\"[":
            close = "]" if text[i] == "[" else text[i]
            i += 1
            while i < len(text):
                if text[i:i + 2] == close * 2:
                    i += 2
                elif text[i] == close:
                    i += 1
                    break
                else:
                    i += 1
            continue
        start = i
        if text[i:i + 2] == "--":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
        elif text[i:i + 2] == "/*":
            depth = 1
            i += 2
            while i < len(text) and depth:
                pair = text[i:i + 2]
                if pair == "/*":
                    depth += 1
                    i += 2
                elif pair == "*/":
                    depth -= 1
                    i += 2
                else:
                    i += 1
        else:
            i += 1
            continue
        for index in range(start, i):
            if text[index] not in "\r\n":
                result[index] = " "
    return "".join(result)
