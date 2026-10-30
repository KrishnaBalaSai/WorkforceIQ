
"""
WorkforceIQ - HR Analytics Authorization Helper.
"""

import hmac
import logging
import os

logger = logging.getLogger("workforceiq.auth")

_HR_ANALYTICS_TOKEN = os.environ.get("HR_ANALYTICS_TOKEN", "")


def verify_hr_token(provided_token: str, request_path: str = "") -> bool:
    """Verify an HR analytics token using constant-time comparison."""

    if not _HR_ANALYTICS_TOKEN:
        logger.warning(
            "HR access denied: authorization token is not configured. Path: %s",
            request_path,
        )
        return False

    if not provided_token:
        logger.warning(
            "HR access denied: empty token provided. Path: %s",
            request_path,
        )
        return False

    authorized = hmac.compare_digest(
        provided_token.encode("utf-8"),
        _HR_ANALYTICS_TOKEN.encode("utf-8"),
    )

    if authorized:
        logger.info("HR access granted. Path: %s", request_path)
    else:
        logger.warning("HR access denied: token mismatch. Path: %s", request_path)

    return authorized
