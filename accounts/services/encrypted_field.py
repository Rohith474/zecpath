from django.db import models

from accounts.services.encryption_service import EncryptionService


class EncryptedTextField(models.TextField):

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value

        try:
            return EncryptionService.decrypt(value)
        except Exception:
            # Allows existing plaintext values to remain readable
            # until they are encrypted by the data migration.
            return value

    def to_python(self, value):
        if value is None or value == "":
            return value

        if not isinstance(value, str):
            return value

        try:
            return EncryptionService.decrypt(value)
        except Exception:
            # Existing plaintext values are returned unchanged.
            return value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value

        if not isinstance(value, str):
            value = str(value)

        try:
            EncryptionService.decrypt(value)
            return value
        except Exception:
            return EncryptionService.encrypt(value)