"""cascades

Revision ID: 572740b7511b
Revises: 86b923a8b686
Create Date: 2022-10-14 13:54:51.813666

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '572740b7511b'
down_revision = '86b923a8b686'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('conversations_media_source_id_fkey', 'conversations', type_='foreignkey')
    op.create_foreign_key(None, 'conversations', 'media_sources', ['media_source_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    op.create_foreign_key('conversations_media_source_id_fkey', 'conversations', 'media_sources', ['media_source_id'], ['id'])
    # ### end Alembic commands ###