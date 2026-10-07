from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:

        message = "An error occurred."

        if response.status_code == 400:
            message = "Validation failed."

        elif response.status_code == 401:
            message = "Authentication failed."

        elif response.status_code == 403:
            message = "Permission denied."

        elif response.status_code == 404:
            message = "Resource not found."

        elif response.status_code == 500:
            message = "Internal server error."

        response.data = {
            "success": False,
            "message": message,
            "errors": response.data,
        }

    return response