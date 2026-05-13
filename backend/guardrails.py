# guardrails.py

# ── BANNED QUESTION KEYWORDS ──────────────────────
BANNED_QUESTION_KEYWORDS = [
    "delete", "drop", "remove", "truncate",
    "os.system", "subprocess", "format",
    "password", "secret", "credentials",
    "hack", "exploit", "inject",
    "__import__", "eval(", "exec("
]

# ── BANNED CODE PATTERNS ──────────────────────────
BANNED_CODE_PATTERNS = [
    "os.system",
    "os.remove",
    "os.rmdir",
    "subprocess",
    "shutil.rmtree",
    "__import__",
    "importlib",
    "sys.exit",
    "drop(",
    "rm -rf",
    "os.unlink",
    "open('/etc",
    "open('C:\\\\Windows",
]

# ── MAX QUESTION LENGTH ───────────────────────────
MAX_QUESTION_LENGTH = 500

# ─────────────────────────────────────────────────
def check_question(question: str) -> tuple[bool, str]:
    """
    Check if the user's question is safe.
    Returns (is_safe, reason)
    """

    # 1. length check
    if len(question) > MAX_QUESTION_LENGTH:
        return False, f"Question too long ({len(question)} chars). Max is {MAX_QUESTION_LENGTH}."

    # 2. empty check
    if not question.strip():
        return False, "Question is empty."

    # 3. banned keyword check
    question_lower = question.lower()
    for keyword in BANNED_QUESTION_KEYWORDS:
        if keyword.lower() in question_lower:
            return False, f"Banned keyword detected: '{keyword}'"

    return True, "OK"


def check_code(code: str) -> tuple[bool, str]:
    """
    Check if the code GPT generated is safe to run.
    Returns (is_safe, reason)
    """

    # 1. empty check
    if not code.strip():
        return False, "Empty code."

    # 2. banned pattern check
    code_lower = code.lower()
    for pattern in BANNED_CODE_PATTERNS:
        if pattern.lower() in code_lower:
            return False, f"Dangerous code pattern detected: '{pattern}'"

    return True, "OK"


def log_block(reason: str, question: str = None, code: str = None):
    """
    Print a clear block message
    """
    print(f"\n🚫 BLOCKED by guardrails!")
    print(f"   Reason: {reason}")
    if question:
        print(f"   Question: {question[:100]}")
    if code:
        print(f"   Code: {code[:100]}")
    print()