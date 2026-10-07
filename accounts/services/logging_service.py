import logging

from accounts.models import AuditLog


application_logger = logging.getLogger("accounts")
ai_logger = logging.getLogger("ai")
security_logger = logging.getLogger("security")


class LoggingService:

    @staticmethod
    def log_application(message, level="info"):
        log_method = getattr(
            application_logger,
            level,
            application_logger.info,
        )
        log_method(message)

    @staticmethod
    def log_ai_event(message, level="info"):
        log_method = getattr(
            ai_logger,
            level,
            ai_logger.info,
        )
        log_method(message)
    @staticmethod
    def log_ai_call_event(
        event,
        session_id=None,
        message="",
        metadata=None,
    ):
        log_message = (
            f"AI_EVENT | "
            f"event={event} | "
            f"session_id={session_id} | "
            f"message={message} | "
            f"metadata={metadata or {}}"
        )

        ai_logger.info(log_message)

    @staticmethod
    def log_security_event(message, level="warning"):
        log_method = getattr(
            security_logger,
            level,
            security_logger.warning,
        )
        log_method(message)

    @staticmethod
    def create_audit_log(
        admin=None,
        actor_type="ADMIN",
        action="",
        target_type="",
        target_id=None,
        description="",
        ip_address=None,
        metadata=None,
    ):
        return AuditLog.objects.create(
            admin=admin,
            actor_type=actor_type,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            ip_address=ip_address,
            metadata=metadata or {},
        )
    @staticmethod
    def log_failure(
        component,
        message,
        exception=None,
        metadata=None,
    ):
        error_message = (
            f"FAILURE | "
            f"component={component} | "
            f"message={message}"
        )

        if exception:
            error_message += (
                f" | exception={type(exception).__name__}"
                f" | error={str(exception)}"
            )

        application_logger.error(
            f"{error_message} | metadata={metadata or {}}"
        )