import string
import random


class CodeGenerator:
    @classmethod
    def generate_code(cls, length=7, include_alpha=False):
        if include_alpha:
            chars = string.ascii_letters + string.digits
        else:
            chars = string.digits
        return "".join(random.choice(chars) for _ in range(length))
