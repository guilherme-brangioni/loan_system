import os
from datetime import datetime

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from database.database import db
from models.loan_item import LoanItem


class ImageUploadService:
    """
    Serviço responsável por validar e salvar imagens de equipamentos
    vinculadas aos itens do empréstimo.
    """

    @staticmethod
    def allowed_file(filename: str) -> bool:
        if not filename or "." not in filename:
            return False

        extension = filename.rsplit(".", 1)[1].lower()

        return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]

    @staticmethod
    def save_loan_item_image(
        loan_item: LoanItem,
        file_storage: FileStorage,
    ) -> LoanItem:
        """
        Salva imagem do item do empréstimo.

        A imagem fica em:
        generated/equipment_images/loan_<id>/
        """

        if not file_storage:
            return loan_item

        if not file_storage.filename:
            return loan_item

        if not ImageUploadService.allowed_file(file_storage.filename):
            raise ValueError(
                "Formato de imagem inválido. Use PNG, JPG, JPEG ou WEBP."
            )

        upload_root = current_app.config["EQUIPMENT_IMAGE_UPLOAD_DIR"]

        loan_folder = os.path.join(
            upload_root,
            f"loan_{loan_item.loan_id}",
        )

        os.makedirs(loan_folder, exist_ok=True)

        original_filename = secure_filename(file_storage.filename)

        extension = original_filename.rsplit(".", 1)[1].lower()

        filename = (
            f"loan_item_{loan_item.id}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        )

        file_path = os.path.join(loan_folder, filename)

        file_storage.save(file_path)

        loan_item.image_path = file_path
        loan_item.image_original_filename = original_filename

        db.session.commit()

        return loan_item