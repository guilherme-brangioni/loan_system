from itsdangerous import BadSignature, URLSafeSerializer
from flask import current_app


class VerificationTokenService:
    """
    Gera e valida token assinado para verificação pública do comprovante.

    Esse token serve apenas para consultar a autenticidade do documento.
    Não permite aprovar, devolver, editar ou executar ações.
    """

    SALT = "loan-document-verification"

    @staticmethod
    def _serializer() -> URLSafeSerializer:
        return URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=VerificationTokenService.SALT,
        )

    @staticmethod
    def generate_token(loan_id: int) -> str:
        serializer = VerificationTokenService._serializer()

        return serializer.dumps(
            {
                "loan_id": loan_id,
            }
        )

    @staticmethod
    def validate_token(token: str) -> dict:
        serializer = VerificationTokenService._serializer()

        try:
            data = serializer.loads(token)

            if not isinstance(data, dict):
                raise ValueError("Token inválido.")

            if not data.get("loan_id"):
                raise ValueError("Token inválido.")

            return data

        except BadSignature:
            raise ValueError("Token de verificação inválido.")