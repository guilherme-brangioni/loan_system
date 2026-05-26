from database.database import db

from enums.equipment_status import EquipmentStatus
from models.equipment import Equipment
from utils.normalize import normalize_name


class EquipmentService:
    """
    Serviço responsável pelo cadastro e auto-cadastro de equipamentos.

    Regras:
    - Código do Equipamento NÃO é patrimônio.
    - Patrimônio continua existindo e pode ser N/A.
    - Se patrimônio for diferente de N/A, usamos patrimônio como identificador.
    - Se patrimônio for N/A, usamos serial ou código do equipamento.
    """

    @staticmethod
    def build_equipment_name(
        fabricante: str,
        modelo: str,
        tipo_equipamento: str,
    ) -> str:
        fabricante_norm = normalize_name(fabricante)
        modelo_norm = normalize_name(modelo)
        tipo_norm = normalize_name(tipo_equipamento)

        equipment_name = " ".join(
            part for part in [fabricante_norm, modelo_norm]
            if part
        )

        if tipo_norm and equipment_name:
            return f"{tipo_norm} - {equipment_name}"

        if tipo_norm:
            return tipo_norm

        return equipment_name

    @staticmethod
    def validate_identification(
        patrimonio: str,
        serial: str = "",
        codigo_equipamento: str = "",
    ) -> None:
        """
        Valida se o equipamento possui identificação mínima.

        Patrimônio é obrigatório, mas pode ser N/A.

        Se patrimônio for N/A, então precisamos de pelo menos:
        - número de série; ou
        - código do equipamento.
        """

        patrimonio_norm = normalize_name(patrimonio)
        serial_norm = normalize_name(serial)
        codigo_norm = normalize_name(codigo_equipamento)

        if not patrimonio_norm:
            raise ValueError(
                "O campo 'Patrimônio' é obrigatório. Use N/A se não houver."
            )

        if patrimonio_norm == "N/A" and not serial_norm and not codigo_norm:
            raise ValueError(
                "Quando o patrimônio for N/A, informe o Número de Série "
                "ou o Código do Equipamento."
            )

    @staticmethod
    def find_existing_equipment(
        patrimonio: str,
        serial: str = "",
        codigo_equipamento: str = "",
    ) -> Equipment | None:
        """
        Busca equipamento existente.

        Ordem de busca:
        1. patrimônio, se diferente de N/A;
        2. serial;
        3. código do equipamento.
        """

        patrimonio_norm = normalize_name(patrimonio)
        serial_norm = normalize_name(serial)
        codigo_norm = normalize_name(codigo_equipamento)

        if patrimonio_norm and patrimonio_norm != "N/A":
            existing = Equipment.query.filter_by(
                patrimonio=patrimonio_norm
            ).first()

            if existing:
                return existing

        if serial_norm:
            existing = Equipment.query.filter_by(
                serial=serial_norm
            ).first()

            if existing:
                return existing

        if codigo_norm:
            existing = Equipment.query.filter_by(
                codigo_equipamento=codigo_norm
            ).first()

            if existing:
                return existing

        return None

    @staticmethod
    def create_equipment(
        fabricante: str,
        modelo: str,
        tipo_equipamento: str,
        patrimonio: str,
        codigo_equipamento: str = "",
        categoria: str = "",
        serial: str = "",
        observacoes: str = "",
        validado: bool = False,
    ) -> Equipment:
        fabricante_norm = normalize_name(fabricante)
        modelo_norm = normalize_name(modelo)
        tipo_norm = normalize_name(tipo_equipamento)
        patrimonio_norm = normalize_name(patrimonio)
        codigo_norm = normalize_name(codigo_equipamento)
        serial_norm = normalize_name(serial)

        if not fabricante_norm:
            raise ValueError("O campo 'Fabricante' é obrigatório.")

        if not modelo_norm:
            raise ValueError("O campo 'Modelo' é obrigatório.")

        if not tipo_norm:
            raise ValueError("O campo 'Tipo de equipamento' é obrigatório.")

        EquipmentService.validate_identification(
            patrimonio=patrimonio_norm,
            serial=serial_norm,
            codigo_equipamento=codigo_norm,
        )

        nome = EquipmentService.build_equipment_name(
            fabricante=fabricante_norm,
            modelo=modelo_norm,
            tipo_equipamento=tipo_norm,
        )

        equipment = Equipment()

        equipment.codigo_interno = "TEMP"

        equipment.nome = nome
        equipment.nome_normalizado = normalize_name(nome)

        equipment.fabricante = fabricante_norm
        equipment.modelo = modelo_norm
        equipment.tipo_equipamento = tipo_norm

        equipment.patrimonio = patrimonio_norm
        equipment.codigo_equipamento = codigo_norm if codigo_norm else None
        equipment.serial = serial_norm if serial_norm else None

        equipment.categoria = normalize_name(categoria) if categoria else None
        equipment.observacoes = observacoes

        equipment.validado = validado
        equipment.status = EquipmentStatus.DISPONIVEL.value

        db.session.add(equipment)
        db.session.commit()

        equipment.codigo_interno = f"EQP-{equipment.id:04d}"

        db.session.commit()

        return equipment

    @staticmethod
    def get_or_create_equipment(
        fabricante: str,
        modelo: str,
        tipo_equipamento: str,
        patrimonio: str,
        codigo_equipamento: str = "",
        categoria: str = "",
        serial: str = "",
    ) -> Equipment:
        """
        Busca ou cria equipamento.

        Usado principalmente durante o cadastro de empréstimo.
        """

        EquipmentService.validate_identification(
            patrimonio=patrimonio,
            serial=serial,
            codigo_equipamento=codigo_equipamento,
        )

        existing = EquipmentService.find_existing_equipment(
            patrimonio=patrimonio,
            serial=serial,
            codigo_equipamento=codigo_equipamento,
        )

        if existing:
            return existing

        return EquipmentService.create_equipment(
            fabricante=fabricante,
            modelo=modelo,
            tipo_equipamento=tipo_equipamento,
            patrimonio=patrimonio,
            codigo_equipamento=codigo_equipamento,
            categoria=categoria,
            serial=serial,
            validado=False,
        )

    @staticmethod
    def low_stock_items():
        """
        Mantido apenas para compatibilidade temporária com o dashboard.
        """

        return []