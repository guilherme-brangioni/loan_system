import os
from datetime import datetime
from typing import Any

from flask import current_app
from reportlab.graphics.barcode.qr import QrCodeWidget


from services.verification_token_service import VerificationTokenService
from services.app_setting_service import AppSettingService

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class PDFService:
    """
    Serviço responsável por gerar o comprovante PDF do empréstimo.

    Esta versão gera:
    - cabeçalho com logo opcional;
    - dados organizados em tabelas;
    - lista de equipamentos;
    - campos de assinatura;
    - páginas extras com imagens dos equipamentos, limitadas a 60% da largura.
    """

    @staticmethod
    def generate_loan_pdf(loan) -> str:
        pdf_dir = current_app.config["GENERATED_PDF_DIR"]
        os.makedirs(pdf_dir, exist_ok=True)

        filename = f"{loan.numero_controle}.pdf"
        path = os.path.join(pdf_dir, filename)

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )

        elements: list[Any] = []

        styles = PDFService._build_styles()

        elements.extend(PDFService._build_header(loan, styles))
        elements.append(Spacer(1, 12))

        elements.extend(PDFService._build_summary_section(loan, styles))
        elements.append(Spacer(1, 10))

        elements.extend(PDFService._build_verification_section(loan, styles))
        elements.append(Spacer(1, 10))

        elements.extend(PDFService._build_people_section(loan, styles))
        elements.append(Spacer(1, 10))

        elements.extend(PDFService._build_equipment_section(loan, styles))
        elements.append(Spacer(1, 14))

        elements.extend(PDFService._build_signature_section(loan, styles))
        elements.append(Spacer(1, 12))

        elements.append(
            Paragraph(
                "Este comprovante foi gerado automaticamente pelo Sistema de Empréstimos.",
                styles["small_center"],
            )
        )

        elements.extend(PDFService._build_equipment_image_pages(loan, styles))

        doc.build(
            elements,
            onFirstPage=PDFService._draw_footer,
            onLaterPages=PDFService._draw_footer,
        )

        return path

    @staticmethod
    def _build_styles() -> dict:
        base_styles = getSampleStyleSheet()

        return {
            "title": ParagraphStyle(
                "CustomTitle",
                parent=base_styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=18,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#064e3b"),
                spaceAfter=8,
            ),
            "subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=13,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#111827"),
            ),
            "section": ParagraphStyle(
                "Section",
                parent=base_styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#064e3b"),
                spaceBefore=6,
                spaceAfter=6,
            ),
            "normal": ParagraphStyle(
                "NormalCustom",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                alignment=TA_LEFT,
            ),
            "small": ParagraphStyle(
                "Small",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9,
            ),
            "small_center": ParagraphStyle(
                "SmallCenter",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#4b5563"),
            ),
            "table_header": ParagraphStyle(
                "TableHeader",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.white,
            ),
            "table_cell": ParagraphStyle(
                "TableCell",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10,
            ),
        }

    @staticmethod
    def _build_header(loan, styles: dict) -> list[Any]:
        elements: list[Any] = []

        logo_path = AppSettingService.get(
            "LOGO_PATH",
            current_app.config.get("LOGO_PATH"),
        )

        document_title = PDFService._get_document_title(loan)

        title_block = [
            Paragraph(document_title, styles["title"]),
            Paragraph(
                f"Número de controle: <b>{PDFService._safe(loan.numero_controle)}</b>",
                styles["subtitle"],
            ),
            Paragraph(
                f"Status atual: <b>{PDFService._safe(loan.status)}</b>",
                styles["subtitle"],
            ),
        ]

        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(
                    logo_path,
                    width=140,
                    height=35,
                )

                logo.drawWidth = 140
                logo.drawHeight = 35

                header_table = Table(
                    [
                        [
                            logo,
                            title_block,
                        ]
                    ],
                    colWidths=[4.2 * cm, 13.0 * cm],
                )

                header_table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ALIGN", (0, 0), (0, 0), "LEFT"),
                            ("ALIGN", (1, 0), (1, 0), "CENTER"),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                            ("PADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )

                elements.append(header_table)
                return elements

            except Exception:
                pass

        elements.append(Paragraph(document_title, styles["title"]))
        elements.append(
            Paragraph(
                f"Número de controle: <b>{PDFService._safe(loan.numero_controle)}</b>",
                styles["subtitle"],
            )
        )
        elements.append(
            Paragraph(
                f"Status atual: <b>{PDFService._safe(loan.status)}</b>",
                styles["subtitle"],
            )
        )

        return elements

    @staticmethod
    def _build_summary_section(loan, styles: dict) -> list[Any]:
        elements: list[Any] = [
            Paragraph("Resumo do empréstimo", styles["section"]),
        ]

        data = [
            [
                PDFService._cell("Data do empréstimo", styles),
                PDFService._cell(PDFService._format_date(loan.data_emprestimo), styles),
                PDFService._cell("Previsão de devolução", styles),
                PDFService._cell(PDFService._format_date(loan.data_prevista_devolucao), styles),
            ],
            [
                PDFService._cell("Data real de devolução", styles),
                PDFService._cell(PDFService._format_date(loan.data_real_devolucao), styles),
                PDFService._cell("Local de utilização", styles),
                PDFService._cell(PDFService._safe(loan.local_utilizacao, "Não informado"), styles),
            ],
        ]

        table = Table(
            data,
            colWidths=[3.4 * cm, 4.2 * cm, 3.8 * cm, 5.8 * cm],
        )

        table.setStyle(PDFService._default_table_style())

        elements.append(table)

        return elements

    @staticmethod
    def _build_people_section(loan, styles: dict) -> list[Any]:
        elements: list[Any] = [
            Paragraph("Envolvidos", styles["section"]),
        ]

        user = getattr(loan, "user", None)
        approver = getattr(loan, "approver", None)

        data = [
            [
                PDFService._header_cell("Papel", styles),
                PDFService._header_cell("Nome", styles),
                PDFService._header_cell("Matrícula", styles),
                PDFService._header_cell("E-mail", styles),
            ],
            [
                PDFService._cell("Solicitante", styles),
                PDFService._cell(getattr(user, "nome", ""), styles),
                PDFService._cell(getattr(user, "matricula", ""), styles),
                PDFService._cell(getattr(user, "email", ""), styles),
            ],
            [
                PDFService._cell("Aprovador", styles),
                PDFService._cell(getattr(approver, "nome", ""), styles),
                PDFService._cell(getattr(approver, "matricula", ""), styles),
                PDFService._cell(getattr(approver, "email", ""), styles),
            ],
            [
                PDFService._cell("Responsável pela coleta/entrega", styles),
                PDFService._cell(getattr(loan, "responsavel_entrega_nome", ""), styles),
                PDFService._cell(getattr(loan, "responsavel_entrega_matricula", ""), styles),
                PDFService._cell(getattr(loan, "responsavel_entrega_email", ""), styles),
            ],
        ]

        table = Table(
            data,
            colWidths=[4.2 * cm, 4.6 * cm, 3.0 * cm, 5.4 * cm],
            repeatRows=1,
        )

        table.setStyle(PDFService._default_table_style(header=True))

        elements.append(table)

        user_area_data = [
            [
                PDFService._cell("Gerência", styles),
                PDFService._cell(getattr(user, "gerencia", "") if user else "", styles),
                PDFService._cell("Regional", styles),
                PDFService._cell(getattr(user, "regional", "") if user else "", styles),
                PDFService._cell("Equipe", styles),
                PDFService._cell(getattr(user, "equipe", "") if user else "", styles),
            ]
        ]

        area_table = Table(
            user_area_data,
            colWidths=[2.4 * cm, 3.5 * cm, 2.3 * cm, 3.4 * cm, 2.0 * cm, 3.6 * cm],
        )

        area_table.setStyle(PDFService._default_table_style())

        elements.append(Spacer(1, 6))
        elements.append(area_table)

        return elements

    @staticmethod
    def _build_equipment_section(loan, styles: dict) -> list[Any]:
        elements: list[Any] = [
            Paragraph("Equipamentos / materiais", styles["section"]),
        ]

        data = [
            [
                PDFService._header_cell("Tipo", styles),
                PDFService._header_cell("Fabricante / Modelo", styles),
                PDFService._header_cell("Patrimônio", styles),
                PDFService._header_cell("Cód. Equip.", styles),
                PDFService._header_cell("Série", styles),
                PDFService._header_cell("Status item", styles),
            ]
        ]

        for item in PDFService._get_loan_items(loan):
            equipment = getattr(item, "equipment", None)

            if equipment is None:
                continue

            data.append(
                [
                    PDFService._cell(getattr(equipment, "tipo_equipamento", ""), styles),
                    PDFService._cell(
                        f"{PDFService._safe(getattr(equipment, 'fabricante', ''))} "
                        f"{PDFService._safe(getattr(equipment, 'modelo', ''))}",
                        styles,
                    ),
                    PDFService._cell(getattr(equipment, "patrimonio", ""), styles),
                    PDFService._cell(getattr(equipment, "codigo_equipamento", ""), styles),
                    PDFService._cell(getattr(equipment, "serial", ""), styles),
                    PDFService._cell(getattr(item, "status", ""), styles),
                ]
            )

        if len(data) == 1:
            data.append(
                [
                    PDFService._cell("-", styles),
                    PDFService._cell("Nenhum equipamento encontrado.", styles),
                    PDFService._cell("-", styles),
                    PDFService._cell("-", styles),
                    PDFService._cell("-", styles),
                    PDFService._cell("-", styles),
                ]
            )

        table = Table(
            data,
            colWidths=[3.0 * cm, 4.6 * cm, 2.6 * cm, 2.7 * cm, 2.7 * cm, 1.9 * cm],
            repeatRows=1,
        )

        table.setStyle(PDFService._default_table_style(header=True))

        elements.append(table)

        return elements

    @staticmethod
    def _build_signature_section(loan, styles: dict) -> list[Any]:
        elements: list[Any] = [
            Paragraph("Assinaturas", styles["section"]),
            Spacer(1, 14),
        ]

        data = [
            [
                PDFService._signature_cell("Solicitante", styles),
                PDFService._signature_cell("Responsável pela entrega/coleta", styles),
            ],
            [
                PDFService._signature_line(styles),
                PDFService._signature_line(styles),
            ],
            [
                PDFService._signature_name(
                    getattr(getattr(loan, "user", None), "nome", ""),
                    styles,
                ),
                PDFService._signature_name(
                    getattr(loan, "responsavel_entrega_nome", ""),
                    styles,
                ),
            ],
        ]

        if getattr(loan, "data_real_devolucao", None):
            data.extend(
                [
                    [
                        PDFService._signature_cell("Responsável pela devolução", styles),
                        PDFService._signature_cell("Observações", styles),
                    ],
                    [
                        PDFService._signature_line(styles),
                        PDFService._cell(
                            PDFService._safe(getattr(loan, "observacoes", ""), "Sem observações."),
                            styles,
                        ),
                    ],
                    [
                        PDFService._signature_name(
                            PDFService._get_last_returned_by(loan),
                            styles,
                        ),
                        PDFService._cell("", styles),
                    ],
                ]
            )

        table = Table(
            data,
            colWidths=[8.4 * cm, 8.4 * cm],
        )

        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)

        return elements

    @staticmethod
    def _build_equipment_image_pages(loan, styles: dict) -> list[Any]:
        elements: list[Any] = []

        page_width, page_height = A4
        max_image_width = page_width * 0.60
        max_image_height = page_height * 0.60

        for item in PDFService._get_loan_items(loan):
            image_path = getattr(item, "image_path", None)

            if not image_path or not os.path.exists(image_path):
                continue

            equipment = getattr(item, "equipment", None)

            elements.append(PageBreak())

            elements.append(
                Paragraph(
                    "Imagem do equipamento",
                    styles["title"],
                )
            )

            if equipment:
                elements.append(
                    Paragraph(
                        (
                            f"<b>{PDFService._safe(getattr(equipment, 'tipo_equipamento', 'Equipamento'))}</b> "
                            f"{PDFService._safe(getattr(equipment, 'fabricante', ''))} "
                            f"{PDFService._safe(getattr(equipment, 'modelo', ''))}"
                        ),
                        styles["subtitle"],
                    )
                )

                elements.append(
                    Paragraph(
                        (
                            f"Patrimônio: <b>{PDFService._safe(getattr(equipment, 'patrimonio', '-'))}</b> | "
                            f"Cód. Equipamento: <b>{PDFService._safe(getattr(equipment, 'codigo_equipamento', '-'))}</b> | "
                            f"Série: <b>{PDFService._safe(getattr(equipment, 'serial', '-'))}</b>"
                        ),
                        styles["small_center"],
                    )
                )

                elements.append(Spacer(1, 20))

            try:
                reader = ImageReader(image_path)
                original_width, original_height = reader.getSize()

                scale = min(
                    max_image_width / original_width,
                    max_image_height / original_height,
                    1,
                )

                draw_width = original_width * scale
                draw_height = original_height * scale

                img = Image(
                    image_path,
                    width=draw_width,
                    height=draw_height,
                )

                img.hAlign = "CENTER"

                elements.append(img)

            except Exception as exc:
                elements.append(
                    Paragraph(
                        f"Não foi possível carregar a imagem: {exc}",
                        styles["normal"],
                    )
                )

        return elements

    @staticmethod
    def _draw_footer(canvas, doc):
        canvas.saveState()

        width, _ = A4

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))

        canvas.drawString(
            1.5 * cm,
            0.8 * cm,
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        )

        canvas.drawRightString(
            width - 1.5 * cm,
            0.8 * cm,
            f"Página {doc.page}",
        )

        canvas.restoreState()

    @staticmethod
    def _default_table_style(header: bool = False) -> TableStyle:
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]

        if header:
            style.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#064e3b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ]
            )

        return TableStyle(style)

    @staticmethod
    def _get_document_title(loan) -> str:
        status = str(getattr(loan, "status", "") or "").upper()

        if status == "FINALIZADO":
            return "COMPROVANTE DE DEVOLUÇÃO DE EQUIPAMENTOS"

        if getattr(loan, "data_real_devolucao", None):
            return "COMPROVANTE ATUALIZADO DE EMPRÉSTIMO"

        return "COMPROVANTE DE EMPRÉSTIMO DE EQUIPAMENTOS"

    @staticmethod
    def _get_loan_items(loan: Any) -> list:
        items = getattr(loan, "items", None)

        if not items:
            return []

        return list(items)

    @staticmethod
    def _get_last_returned_by(loan) -> str:
        names = []

        for item in PDFService._get_loan_items(loan):
            returned_by = getattr(item, "devolvido_por", None)

            if returned_by and returned_by not in names:
                names.append(returned_by)

        if not names:
            return "Não informado"

        return ", ".join(names)

    @staticmethod
    def _format_date(value) -> str:
        if not value:
            return "Não informado"

        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y")

        return str(value)

    @staticmethod
    def _safe(value, default: str = "-") -> str:
        text = str(value or "").strip()

        if not text:
            return default

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _cell(value, styles: dict):
        return Paragraph(PDFService._safe(value), styles["table_cell"])

    @staticmethod
    def _header_cell(value, styles: dict):
        return Paragraph(PDFService._safe(value), styles["table_header"])

    @staticmethod
    def _signature_cell(value, styles: dict):
        return Paragraph(f"<b>{PDFService._safe(value)}</b>", styles["table_cell"])

    @staticmethod
    def _signature_line(styles: dict):
        return Paragraph("_" * 42, styles["table_cell"])

    @staticmethod
    def _signature_name(value, styles: dict):
        return Paragraph(PDFService._safe(value, "Nome: __________________________"), styles["small"])
    
    @staticmethod
    def _build_verification_section(loan, styles: dict) -> list[Any]:
        """
        Cria seção com QR Code de verificação do comprovante.
        """

        elements: list[Any] = [
            Paragraph("Verificação do comprovante", styles["section"]),
        ]

        verification_url = PDFService._build_verification_url(loan)

        qr_drawing = PDFService._build_qr_code_drawing(
            verification_url,
            size=2.8 * cm,
        )

        text = Paragraph(
            (
                "Escaneie o QR Code para verificar a autenticidade deste comprovante."
                "<br/>"
                f"<font size='7'>{PDFService._safe(verification_url)}</font>"
            ),
            styles["table_cell"],
        )

        table = Table(
            [
                [
                    qr_drawing,
                    text,
                ]
            ],
            colWidths=[3.2 * cm, 14.0 * cm],
        )

        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)

        return elements

    @staticmethod
    def _build_verification_url(loan) -> str:
        """
        Monta a URL de verificação usada no QR Code.

        Agora usa APP_BASE_URL salvo na tela de Configurações.
        Se não houver valor no banco, usa o valor padrão do config.py.
        """

        token = VerificationTokenService.generate_token(loan.id)

        base_url = AppSettingService.get(
            "APP_BASE_URL",
            current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
        )

        base_url = str(base_url or "http://127.0.0.1:5000").strip().rstrip("/")

        return f"{base_url}/emprestimos/verificar/{token}"

    @staticmethod
    def _build_qr_code_drawing(data: str, size: float) -> Drawing:
        """
        Cria um QR Code como Drawing do ReportLab.
        """

        qr_code = QrCodeWidget(data)

        bounds = qr_code.getBounds()

        qr_width = bounds[2] - bounds[0]
        qr_height = bounds[3] - bounds[1]

        drawing = Drawing(
            size,
            size,
            transform=[
                size / qr_width,
                0,
                0,
                size / qr_height,
                0,
                0,
            ],
        )

        drawing.add(qr_code)

        return drawing