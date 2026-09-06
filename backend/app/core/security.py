"""Password hashing — Argon2id. Never log or return hashes to clients."""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str = "", hashed_password: str = "") -> bool:
    return _pwd_context.verify(plain_password, hashed_password)
