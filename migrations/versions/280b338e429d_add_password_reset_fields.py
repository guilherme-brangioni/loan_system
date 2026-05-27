"""add password reset fields

Revision ID: 280b338e429d
Revises: 8c2e15fac124
Create Date: 2026-05-27 13:46:37.294597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '280b338e429d'
down_revision = '8c2e15fac124'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("system_users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "temporary_password_generated_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "password_changed_at",
                sa.DateTime(),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("system_users", schema=None) as batch_op:
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("temporary_password_generated_at")
        batch_op.drop_column("must_change_password")
    # ### end Alembic commands ###
