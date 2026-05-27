"""add user profile fields

Revision ID: 737bb1e0b1ea
Revises: 280b338e429d
Create Date: 2026-05-27 14:51:42.341533

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '737bb1e0b1ea'
down_revision = '280b338e429d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("system_users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("matricula", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("telefone", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("gerencia", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("regional", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("equipe", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("system_users", schema=None) as batch_op:
        batch_op.drop_column("equipe")
        batch_op.drop_column("regional")
        batch_op.drop_column("gerencia")
        batch_op.drop_column("telefone")
        batch_op.drop_column("matricula")

    # ### end Alembic commands ###
