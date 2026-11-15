from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class HasherArgon2:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        self._dummy = self._hasher.hash("servichile-dummy-password")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verificar(self, password_hash: str | None, password: str) -> bool:
        try:
            self._hasher.verify(password_hash or self._dummy, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        return bool(password_hash)
