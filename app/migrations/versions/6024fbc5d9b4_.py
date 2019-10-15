"""empty message

Revision ID: 6024fbc5d9b4
Revises: 5cbc24143619
Create Date: 2019-09-15 11:12:23.827644

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6024fbc5d9b4'
down_revision = '5cbc24143619'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transfer_account', sa.Column('balance', sa.BigInteger(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transfer_account', 'balance')
    # ### end Alembic commands ###