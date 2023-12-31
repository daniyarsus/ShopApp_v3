"""Add initial tables

Revision ID: b1bd8c6b78fc
Revises: 148c4ef3c7e3
Create Date: 2023-12-30 14:09:18.497080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1bd8c6b78fc'
down_revision: Union[str, None] = '148c4ef3c7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('assortments', sa.Column('type', sa.String(), nullable=True))
    op.add_column('assortments', sa.Column('image_url', sa.String(), nullable=True))
    op.create_index(op.f('ix_assortments_type'), 'assortments', ['type'], unique=False)
    op.add_column('employees', sa.Column('position', sa.String(), nullable=True))
    op.create_index(op.f('ix_employees_position'), 'employees', ['position'], unique=False)
    op.drop_constraint('employees_owner_id_fkey', 'employees', type_='foreignkey')
    op.drop_column('employees', 'owner_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('employees', sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('employees_owner_id_fkey', 'employees', 'users', ['owner_id'], ['id'])
    op.drop_index(op.f('ix_employees_position'), table_name='employees')
    op.drop_column('employees', 'position')
    op.drop_index(op.f('ix_assortments_type'), table_name='assortments')
    op.drop_column('assortments', 'image_url')
    op.drop_column('assortments', 'type')
    # ### end Alembic commands ###
