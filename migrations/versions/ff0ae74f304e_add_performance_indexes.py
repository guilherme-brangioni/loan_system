"""add performance indexes

Revision ID: ff0ae74f304e
Revises: a79a33e1e576
Create Date: 2026-05-26 16:22:01.575804

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff0ae74f304e'
down_revision = 'a79a33e1e576'
branch_labels = None
depends_on = None


def upgrade():
    # Loans
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_numero_controle ON loans (numero_controle)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_status ON loans (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_created_at ON loans (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_data_emprestimo ON loans (data_emprestimo)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_data_prevista_devolucao ON loans (data_prevista_devolucao)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_user_id ON loans (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loans_approver_id ON loans (approver_id)")

    # Loan items
    op.execute("CREATE INDEX IF NOT EXISTS ix_loan_items_loan_id ON loan_items (loan_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loan_items_equipment_id ON loan_items (equipment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_loan_items_status ON loan_items (status)")

    # Equipment
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_codigo_interno ON equipments (codigo_interno)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_codigo_equipamento ON equipments (codigo_equipamento)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_serial ON equipments (serial)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_status ON equipments (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_nome_normalizado ON equipments (nome_normalizado)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_equipment_patrimonio ON equipments (patrimonio)")

    # Users / solicitantes
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_nome ON users (nome)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_matricula ON users (matricula)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_gerencia ON users (gerencia)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_regional ON users (regional)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_equipe ON users (equipe)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_loans_numero_controle")
    op.execute("DROP INDEX IF EXISTS ix_loans_status")
    op.execute("DROP INDEX IF EXISTS ix_loans_created_at")
    op.execute("DROP INDEX IF EXISTS ix_loans_data_emprestimo")
    op.execute("DROP INDEX IF EXISTS ix_loans_data_prevista_devolucao")
    op.execute("DROP INDEX IF EXISTS ix_loans_user_id")
    op.execute("DROP INDEX IF EXISTS ix_loans_approver_id")

    op.execute("DROP INDEX IF EXISTS ix_loan_items_loan_id")
    op.execute("DROP INDEX IF EXISTS ix_loan_items_equipment_id")
    op.execute("DROP INDEX IF EXISTS ix_loan_items_status")

    op.execute("DROP INDEX IF EXISTS ix_equipment_codigo_interno")
    op.execute("DROP INDEX IF EXISTS ix_equipment_codigo_equipamento")
    op.execute("DROP INDEX IF EXISTS ix_equipment_serial")
    op.execute("DROP INDEX IF EXISTS ix_equipment_status")
    op.execute("DROP INDEX IF EXISTS ix_equipment_nome_normalizado")
    op.execute("DROP INDEX IF EXISTS ix_equipment_patrimonio")

    op.execute("DROP INDEX IF EXISTS ix_users_nome")
    op.execute("DROP INDEX IF EXISTS ix_users_matricula")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("DROP INDEX IF EXISTS ix_users_gerencia")
    op.execute("DROP INDEX IF EXISTS ix_users_regional")
    op.execute("DROP INDEX IF EXISTS ix_users_equipe")
