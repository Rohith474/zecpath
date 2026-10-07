import re


def validate_phone_number(phone_number):
    """
    Validate the candidate's phone number.
    """

    if not phone_number:
        return {
            "success": False,
            "message": "Candidate phone number is required.",
        }

    cleaned_number = re.sub(r"[\s()-]", "", phone_number)

    if not re.fullmatch(r"\+?[0-9]{10,15}", cleaned_number):
        return {
            "success": False,
            "message": "Invalid candidate phone number.",
        }

    return {
        "success": True,
        "phone_number": cleaned_number,
    }


def get_voice_settings(ai_call):
    """
    Get voice and language settings from AI interview configuration.
    """

    config = ai_call.config

    return {
        "voice_type": config.voice_type,
        "language": config.language,
        "speaking_speed": str(config.speaking_speed),
        "tone": config.tone,
    }


def prepare_outbound_call(ai_call):
    """
    Prepare an outbound AI voice call request.

    This prepares the call information but does not
    place an actual phone call.
    """

    if not ai_call:
        return {
            "success": False,
            "message": "AI call is required.",
        }

    try:
        candidate = ai_call.application.candidate.user
    except AttributeError:
        return {
            "success": False,
            "message": "Candidate information is not available.",
        }

    phone_result = validate_phone_number(
        candidate.phone_number
    )

    if not phone_result["success"]:
        return phone_result

    voice_settings = get_voice_settings(ai_call)

    return {
        "success": True,
        "message": "Outbound AI call request prepared successfully.",
        "ai_call_id": ai_call.id,
        "phone_number": phone_result["phone_number"],
        "voice": voice_settings,
    }
def trigger_outbound_call(ai_call):
    """
    Trigger the outbound AI voice call.

    This function prepares the call request for a
    future telephony provider. It does not place
    a real phone call.
    """

    call_request = prepare_outbound_call(ai_call)

    if not call_request["success"]:
        return call_request

    return {
        "success": True,
        "message": "Outbound AI voice call triggered successfully.",
        "ai_call_id": call_request["ai_call_id"],
        "phone_number": call_request["phone_number"],
        "voice": call_request["voice"],
        "provider": "Not configured",
        "call_status": "Prepared",
    }