import re


def to_camel_case(string: str) -> str:
    string = re.sub(r"^[\-_\.]", "", string.lower())
    if not string:
        return string
    return string[0].lower() + re.sub(r"[\-_\.\s]([a-z])", lambda matched: matched.group(1).upper(), string[1:])


def to_pascal_case(string: str) -> str:
    return to_camel_case(string).title()


def to_snake_case(string: str) -> str:
    string = re.sub(r"[\-\.\s]", "_", str(string))
    if not string:
        return string
    return string[0].lower() + re.sub(r"[A-Z]", lambda matched: "_" + matched.group(0).lower(), string[1:])


def to_sentence_case(string: str) -> str:
    joiner = " "
    string = re.sub(r"[\-_\.\s]", joiner, str(string))
    if not string:
        return string
    return (re.sub(r"[A-Z]", lambda matched: joiner + matched.group(0).lower(), string)).strip().title()
