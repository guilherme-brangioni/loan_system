from flask import Blueprint, render_template, request

from models.equipment import Equipment
from models.loan import Loan
from models.user import User

from utils.query_options import loan_full_options


search_bp = Blueprint(
    "search_bp",
    __name__,
    url_prefix="/busca",
)


@search_bp.route("/")
def global_search():
    """
    Busca global do sistema.

    Pesquisa em:
    - empréstimos;
    - equipamentos;
    - solicitantes.
    """

    q = request.args.get("q", "").strip()

    loans = []
    equipments = []
    users = []

    if q:
        pattern = f"%{q}%"

        loans = (
            Loan.query
            .options(*loan_full_options())
            .outerjoin(User, Loan.user_id == User.id)
            .filter(
                (Loan.numero_controle.ilike(pattern))
                | (Loan.status.ilike(pattern))
                | (User.nome.ilike(pattern))
                | (User.matricula.ilike(pattern))
                | (User.email.ilike(pattern))
            )
            .order_by(Loan.created_at.desc())
            .limit(20)
            .all()
        )

        equipments = (
            Equipment.query
            .filter(
                (Equipment.codigo_interno.ilike(pattern))
                | (Equipment.tipo_equipamento.ilike(pattern))
                | (Equipment.fabricante.ilike(pattern))
                | (Equipment.modelo.ilike(pattern))
                | (Equipment.patrimonio.ilike(pattern))
                | (Equipment.codigo_equipamento.ilike(pattern))
                | (Equipment.serial.ilike(pattern))
                | (Equipment.status.ilike(pattern))
                | (Equipment.regional.ilike(pattern))
                | (Equipment.local_armazenagem.ilike(pattern))
            )
            .order_by(Equipment.codigo_interno.asc())
            .limit(30)
            .all()
        )

        users = (
            User.query
            .filter(
                (User.nome.ilike(pattern))
                | (User.matricula.ilike(pattern))
                | (User.email.ilike(pattern))
                | (User.gerencia.ilike(pattern))
                | (User.regional.ilike(pattern))
                | (User.equipe.ilike(pattern))
            )
            .order_by(User.nome.asc())
            .limit(20)
            .all()
        )

    return render_template(
        "global_search.html",
        q=q,
        loans=loans,
        equipments=equipments,
        users=users,
    )