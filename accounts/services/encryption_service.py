import os

from cryptography.fernet import Fernet


class EncryptionService:

    @staticmethod
    def get_key():
        key = os.getenv("FIELD_ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY is not configured."
            )

        return key.encode()

    @classmethod
    def encrypt(cls, value):
        if value is None or value == "":
            return value

        fernet = Fernet(cls.get_key())
        return fernet.encrypt(value.encode()).decode()

    @classmethod
    def decrypt(cls, value):
        if value is None or value == "":
            return value

        fernet = Fernet(cls.get_key())
        return fernet.decrypt(value.encode()).decode()