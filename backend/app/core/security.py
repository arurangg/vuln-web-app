import bcrypt

# Work factor for bcrypt. Spec NFR-01 requires >= 12.
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (per-hash random salt, cost = BCRYPT_ROUNDS).

    Returns the bcrypt hash as a str (begins with "$2b$"). Replaces the former
    unsalted MD5 implementation — closes Vulnerability #5.
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True iff `plain` matches the bcrypt `hashed` value.

    Wrapped in try/except so a stored value that is NOT a valid bcrypt hash
    (e.g. a legacy 32-char MD5 digest) returns False instead of raising.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
