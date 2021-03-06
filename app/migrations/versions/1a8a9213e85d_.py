"""empty message

Revision ID: 1a8a9213e85d
Revises: 132ea53022f1
Create Date: 2019-10-07 20:07:29.224336

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1a8a9213e85d'
down_revision = '132ea53022f1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ussd_menus',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('authorising_user_id', sa.Integer(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('display_text_en', sa.String(), nullable=False),
    sa.Column('display_text_sw', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ussd_menus_name'), 'ussd_menus', ['name'], unique=True)
    op.create_table('ussd_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('authorising_user_id', sa.Integer(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('session_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('service_code', sa.String(), nullable=False),
    sa.Column('msisdn', sa.String(), nullable=False),
    sa.Column('user_input', sa.String(), nullable=True),
    sa.Column('ussd_menu_id', sa.Integer(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('sessions_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ussd_sessions_session_id'), 'ussd_sessions', ['session_id'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_ussd_sessions_session_id'), table_name='ussd_sessions')
    op.drop_table('ussd_sessions')
    op.drop_index(op.f('ix_ussd_menus_name'), table_name='ussd_menus')
    op.drop_table('ussd_menus')
    # ### end Alembic commands ###
