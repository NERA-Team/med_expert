import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, ForeignKey, DateTime, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class SourceDocument(Base):
    __tablename__ = "source_document"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_type = Column(String(32), nullable=False)
    title = Column(Text, nullable=False)
    isbn = Column(String(32))
    year = Column(SmallInteger)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class PharmacotherapeuticGroup(Base):
    __tablename__ = "pharmacotherapeutic_group"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"))
    code = Column(String(96), unique=True, nullable=False)
    name_ru = Column(String(255), nullable=False)
    level = Column(SmallInteger, default=1)
    book_section = Column(String(16))

class ActiveSubstance(Base):
    __tablename__ = "active_substance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(32), nullable=False)
    name_ru = Column(String(255), nullable=False)
    name_latin = Column(String(255))
    atc_code = Column(String(16))

class TradeName(Base):
    __tablename__ = "trade_name"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    name_latin = Column(String(255))
    manufacturer = Column(String(255))

class DosageForm(Base):
    __tablename__ = "dosage_form"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_ru = Column(String(255), nullable=False)
    name_short = Column(String(128))
    route = Column(String(32), nullable=False)

class DrugProduct(Base):
    __tablename__ = "drug_product"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_name_id = Column(UUID(as_uuid=True), ForeignKey("trade_name.id"), nullable=False)
    dosage_form_id = Column(UUID(as_uuid=True), ForeignKey("dosage_form.id"), nullable=False)
    strength_value = Column(Numeric(10, 3))
    strength_unit = Column(String(16))
    min_age_months = Column(SmallInteger)
    notes = Column(Text)

class ProductActiveSubstance(Base):
    __tablename__ = "product_active_substance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_product_id = Column(UUID(as_uuid=True), ForeignKey("drug_product.id"), nullable=False)
    active_substance_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"), nullable=False)
    is_primary = Column(Boolean, default=False)

class ProductGroup(Base):
    __tablename__ = "product_group"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_product_id = Column(UUID(as_uuid=True), ForeignKey("drug_product.id"), nullable=False)
    pharmacotherapeutic_group_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"), nullable=False)
    is_primary = Column(Boolean, default=False)

class DosingRegimen(Base):
    __tablename__ = "dosing_regimen"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_product_id = Column(UUID(as_uuid=True), ForeignKey("drug_product.id"), nullable=False)
    route = Column(String(32))
    age_min_months = Column(SmallInteger)
    age_max_months = Column(SmallInteger)
    regimen_text = Column(Text)
    course_min_days = Column(SmallInteger)
    course_max_days = Column(SmallInteger)
    course_note = Column(String(255))

class DoseDependentEffect(Base):
    __tablename__ = "dose_dependent_effect"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_substance_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"), nullable=False)
    pharmacotherapeutic_group_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"))
    effect_name_ru = Column(String(255), nullable=False)
    dose_min = Column(Numeric(10, 3), nullable=False)
    dose_max = Column(Numeric(10, 3))
    dose_unit = Column(String(16), nullable=False)

class DrugInteraction(Base):
    __tablename__ = "drug_interaction"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    substance_a_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"))
    group_a_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"))
    substance_b_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"))
    group_b_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"))
    result_text = Column(Text, nullable=False)
    effect_direction = Column(String(32))

class AdverseReaction(Base):
    __tablename__ = "adverse_reaction"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_substance_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"))
    reaction_text = Column(Text, nullable=False)
    adr_type = Column(String(8))
    frequency = Column(String(32))
    is_serious = Column(Boolean, default=False)

class SearchAlias(Base):
    __tablename__ = "search_alias"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alias = Column(String(255), nullable=False)
    alias_normalized = Column(String(255), nullable=False, index=True)
    active_substance_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"))
    trade_name_id = Column(UUID(as_uuid=True), ForeignKey("trade_name.id"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("pharmacotherapeutic_group.id"))
    weight = Column(SmallInteger, default=100)

class Contraindication(Base):
    __tablename__ = "contraindication"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_substance_id = Column(UUID(as_uuid=True), ForeignKey("active_substance.id"))
    drug_product_id = Column(UUID(as_uuid=True), ForeignKey("drug_product.id"))
    condition_text = Column(Text, nullable=False)
    category = Column(String(32))
    min_age_months = Column(SmallInteger)