class ErrorMessage:
    # ---------- Auth / Access ----------
    SERVER_ERROR = "Internal server error"
    DATABASE_FAILURE = "Database operation failed"
    AUTH_CONTEXT_MISSING = "Authentication context missing"
    USER_NOT_AUTHENTICATED = "User is not authenticated"
    USER_ID_MISSING = "Authenticated user id missing"

    ADMIN_ACCESS_REQUIRED = "Admin access required"
    END_USER_ACCESS_REQUIRED = "End-user access required"
    DRIVER_ACCESS_REQUIRED = "Driver access required"
    PUBLIC_ACCESS_ONLY = "Public access only"

    # ---------- Generic ----------
    INVALID_AUTH_CONTEXT = "Invalid authentication context"

    # app/api/auth/messages.py

    SIGNUP_SUCCESS = "Signup successful"
    LOGIN_SUCCESS = "Login successful"
    OTP_SENT = "OTP sent successfully"
    PHONE_VERIFIED = "Phone number verified successfully"
    PHONE_VALIDATED = "Phone number validated successfully"
    OTP_INVALID = "Invalid or expired OTP"
    PHONE_NOT_VERIFIED = "Phone number not verified"

    USER_ALREADY_EXISTS = "User already exists"
    USER_NOT_FOUND = "User not found"
    INVALID_CREDENTIALS = "Invalid credentials"
    ACCESS_DENIED = "Access denied"

    GOOGLE_TOKEN_INVALID = "Invalid Google token"
    PROVIDER_NOT_SUPPORTED = "Auth provider not supported"
