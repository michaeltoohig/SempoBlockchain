"""Make custom attributes plain old ordinary strings

Revision ID: 917051c561c8
Revises: 2c3f97929457
Create Date: 2020-09-03 16:05:10.156853

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '917051c561c8'
down_revision = '2c3f97929457'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('custom_attribute_user_storage', 'value',
               existing_type=sa.JSON(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute('ALTER TABLE custom_attribute_user_storage ALTER COLUMN value TYPE json USING to_json(value)')
