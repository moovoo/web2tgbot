"""initial

Revision ID: 86b923a8b686
Revises: 
Create Date: 2022-08-28 15:15:49.165157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86b923a8b686'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('media_sources',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('media_source', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_sources_media_source'), 'media_sources', ['media_source'], unique=True)
    op.create_table('conversations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('conversation', sa.String(), nullable=True),
    sa.Column('media_source_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['media_source_id'], ['media_sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_conversation'), 'conversations', ['conversation'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_conversations_conversation'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_media_sources_media_source'), table_name='media_sources')
    op.drop_table('media_sources')
    # ### end Alembic commands ###
