from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Limite les tentatives de connexion par IP."""
    scope = 'login'


class OtpThrottle(AnonRateThrottle):
    """Limite les soumissions / vérifications OTP par IP."""
    scope = 'otp'


class OtpResendThrottle(AnonRateThrottle):
    """Limite le renvoi de code OTP — plus strict que la vérification."""
    scope = 'otp_resend'


class ForgotPasswordThrottle(AnonRateThrottle):
    """Limite les demandes de réinitialisation de mot de passe par IP."""
    scope = 'forgot_password'


class RegistrationThrottle(AnonRateThrottle):
    """Limite les créations de compte et les vérifications de code."""
    scope = 'registration'
