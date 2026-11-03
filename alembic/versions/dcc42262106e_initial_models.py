"""Initial models

Revision ID: dcc42262106e
Revises: 
Create Date: 2026-11-01 19:49:28.162632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dcc42262106e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('active_substance',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('name_ru', sa.String(length=255), nullable=False),
    sa.Column('name_latin', sa.String(length=255), nullable=True),
    sa.Column('atc_code', sa.String(length=16), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dosage_form',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name_ru', sa.String(length=255), nullable=False),
    sa.Column('name_short', sa.String(length=128), nullable=True),
    sa.Column('route', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pharmacotherapeutic_group',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('parent_id', sa.UUID(), nullable=True),
    sa.Column('code', sa.String(length=96), nullable=False),
    sa.Column('name_ru', sa.String(length=255), nullable=False),
    sa.Column('level', sa.SmallInteger(), nullable=True),
    sa.Column('book_section', sa.String(length=16), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['pharmacotherapeutic_group.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('source_document',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('doc_type', sa.String(length=32), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('isbn', sa.String(length=32), nullable=True),
    sa.Column('year', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trade_name',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('name_latin', sa.String(length=255), nullable=True),
    sa.Column('manufacturer', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('adverse_reaction',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('active_substance_id', sa.UUID(), nullable=True),
    sa.Column('reaction_text', sa.Text(), nullable=False),
    sa.Column('adr_type', sa.String(length=8), nullable=True),
    sa.Column('frequency', sa.String(length=32), nullable=True),
    sa.Column('is_serious', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['active_substance_id'], ['active_substance.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dose_dependent_effect',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('active_substance_id', sa.UUID(), nullable=False),
    sa.Column('pharmacotherapeutic_group_id', sa.UUID(), nullable=True),
    sa.Column('effect_name_ru', sa.String(length=255), nullable=False),
    sa.Column('dose_min', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('dose_max', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('dose_unit', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['active_substance_id'], ['active_substance.id'], ),
    sa.ForeignKeyConstraint(['pharmacotherapeutic_group_id'], ['pharmacotherapeutic_group.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('drug_interaction',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('substance_a_id', sa.UUID(), nullable=True),
    sa.Column('group_a_id', sa.UUID(), nullable=True),
    sa.Column('substance_b_id', sa.UUID(), nullable=True),
    sa.Column('group_b_id', sa.UUID(), nullable=True),
    sa.Column('result_text', sa.Text(), nullable=False),
    sa.Column('effect_direction', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['group_a_id'], ['pharmacotherapeutic_group.id'], ),
    sa.ForeignKeyConstraint(['group_b_id'], ['pharmacotherapeutic_group.id'], ),
    sa.ForeignKeyConstraint(['substance_a_id'], ['active_substance.id'], ),
    sa.ForeignKeyConstraint(['substance_b_id'], ['active_substance.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('drug_product',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('trade_name_id', sa.UUID(), nullable=False),
    sa.Column('dosage_form_id', sa.UUID(), nullable=False),
    sa.Column('strength_value', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('strength_unit', sa.String(length=16), nullable=True),
    sa.Column('min_age_months', sa.SmallInteger(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['dosage_form_id'], ['dosage_form.id'], ),
    sa.ForeignKeyConstraint(['trade_name_id'], ['trade_name.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('search_alias',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('alias', sa.String(length=255), nullable=False),
    sa.Column('alias_normalized', sa.String(length=255), nullable=False),
    sa.Column('active_substance_id', sa.UUID(), nullable=True),
    sa.Column('trade_name_id', sa.UUID(), nullable=True),
    sa.Column('group_id', sa.UUID(), nullable=True),
    sa.Column('weight', sa.SmallInteger(), nullable=True),
    sa.ForeignKeyConstraint(['active_substance_id'], ['active_substance.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['pharmacotherapeutic_group.id'], ),
    sa.ForeignKeyConstraint(['trade_name_id'], ['trade_name.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_alias_alias_normalized'), 'search_alias', ['alias_normalized'], unique=False)
    op.create_table('contraindication',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('active_substance_id', sa.UUID(), nullable=True),
    sa.Column('drug_product_id', sa.UUID(), nullable=True),
    sa.Column('condition_text', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=True),
    sa.Column('min_age_months', sa.SmallInteger(), nullable=True),
    sa.ForeignKeyConstraint(['active_substance_id'], ['active_substance.id'], ),
    sa.ForeignKeyConstraint(['drug_product_id'], ['drug_product.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dosing_regimen',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('drug_product_id', sa.UUID(), nullable=False),
    sa.Column('route', sa.String(length=32), nullable=True),
    sa.Column('age_min_months', sa.SmallInteger(), nullable=True),
    sa.Column('age_max_months', sa.SmallInteger(), nullable=True),
    sa.Column('regimen_text', sa.Text(), nullable=True),
    sa.Column('course_min_days', sa.SmallInteger(), nullable=True),
    sa.Column('course_max_days', sa.SmallInteger(), nullable=True),
    sa.Column('course_note', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['drug_product_id'], ['drug_product.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('product_active_substance',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('drug_product_id', sa.UUID(), nullable=False),
    sa.Column('active_substance_id', sa.UUID(), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['active_substance_id'], ['active_substance.id'], ),
    sa.ForeignKeyConstraint(['drug_product_id'], ['drug_product.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('product_group',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('drug_product_id', sa.UUID(), nullable=False),
    sa.Column('pharmacotherapeutic_group_id', sa.UUID(), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['drug_product_id'], ['drug_product.id'], ),
    sa.ForeignKeyConstraint(['pharmacotherapeutic_group_id'], ['pharmacotherapeutic_group.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('product_group')
    op.drop_table('product_active_substance')
    op.drop_table('dosing_regimen')
    op.drop_table('contraindication')
    op.drop_index(op.f('ix_search_alias_alias_normalized'), table_name='search_alias')
    op.drop_table('search_alias')
    op.drop_table('drug_product')
    op.drop_table('drug_interaction')
    op.drop_table('dose_dependent_effect')
    op.drop_table('adverse_reaction')
    op.drop_table('trade_name')
    op.drop_table('source_document')
    op.drop_table('pharmacotherapeutic_group')
    op.drop_table('dosage_form')
    op.drop_table('active_substance')
