from flask import current_app
from itsdangerous import URLSafeTimedSerializer


class ApprovalService:
    """
    Serviço de geração e validação de tokens.

    O token evita links simples como /aprovar?id=1.
    """

    SALT = "loan-approval"

    @staticmethod
    def _serializer():
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    @staticmethod
    def generate_token(loan_id: int) -> str:
        serializer = ApprovalService._serializer()

        return serializer.dumps(
            {"loan_id": loan_id},
            salt=ApprovalService.SALT,
        )

    @staticmethod
    def validate_token(token: str):
        serializer = ApprovalService._serializer()

        max_age = current_app.config["APPROVAL_TOKEN_MAX_AGE_SECONDS"]

        try:
            return serializer.loads(
                token,
                salt=ApprovalService.SALT,
                max_age=max_age,
            )
        except Exception:
            return None