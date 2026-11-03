import asyncio
import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app import models
from parser.regex_patterns import DOSE_REGEX, AGE_REGEX, GROUP_REGEX, MNN_REGEX, detect_table_type
from parser.db_utils import get_or_create_group, get_or_create_substance, get_or_create_trade_name

def iter_block_items(parent):
    """
    Генератор для чтения параграфов и таблиц строго в том порядке,
    в котором они находятся в документе Word.
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("unsupported parent")
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def clean_text(text):
    """Удаляет лишние пробелы и переносы строк."""
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

async def main():
    file_path = "parser/Справочник Педиатрия 2017_2024.docx"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Make sure it is in the parser directory.")
        return

    print("Starting advanced parser...")
    doc = Document(file_path)
    
    current_section = "Раздел 2. Справочник"
    current_group = None
    current_substance = None
    current_trade_name = None
    
    table_count = 0
    saved_products = 0

    async with AsyncSessionLocal() as session:
        try:
            for block in iter_block_items(doc):
                if isinstance(block, Paragraph):
                    text = clean_text(block.text)
                    if not text:
                        continue
                    
                    if re.match(r'^2\.\d+\.', text) or "Раздел 4" in text or "Раздел 5" in text:
                        current_section = text
                        print(f"[*] Section: {current_section}")
                        current_group = None
                        current_substance = None

                elif isinstance(block, Table):
                    table_count += 1
                    if len(block.rows) < 2:
                        continue
                    
                    headers = [clean_text(c.text).lower() for c in block.rows[0].cells]
                    table_type = detect_table_type(headers)
                    
                    if table_type == "skip":
                        print(f"    [-] Skipping table #{table_count} (prescription examples/abbreviations)")
                        continue
                    
                    if table_type == "unknown":
                        continue
                    
                    print(f"    [+] Processing table #{table_count} of type '{table_type}'")

                    try:
                        idx_trade = next(i for i, h in enumerate(headers) if "торговое" in h or "препарат" in h or "мнн" in h)
                        idx_form = next(i for i, h in enumerate(headers) if "форма" in h)
                        idx_regimen = next(i for i, h in enumerate(headers) if "режим" in h or "дозиров" in h)
                        idx_course = next((i for i, h in enumerate(headers) if "курс" in h), None)
                    except StopIteration:
                        continue

                    for row in block.rows[1:]:
                        cells = [clean_text(c.text) for c in row.cells]
                        unique_texts = list(dict.fromkeys(cells))
                        
                        if len(unique_texts) == 1:
                            text = unique_texts[0]
                            if GROUP_REGEX.match(text) and 3 < len(text) < 60:
                                current_group = await get_or_create_group(session, text)
                                current_substance = None
                                current_trade_name = None
                                continue

                        trade_text = cells[idx_trade] if idx_trade < len(cells) else ""
                        form_text = cells[idx_form] if idx_form < len(cells) else ""
                        
                        if len(trade_text) > 255 or "Расчет суточной дозы" in trade_text or "Rp.:" in trade_text:
                            continue

                        mnn_match = MNN_REGEX.search(trade_text)
                        if mnn_match and (not form_text or form_text == trade_text):
                            name_ru = mnn_match.group(1).strip()
                            name_lat = mnn_match.group(2).strip()
                            current_substance = await get_or_create_substance(session, name_ru, name_lat)
                            continue

                        if not form_text or form_text == trade_text:
                            continue
                        
                        if not trade_text:
                            if not current_trade_name:
                                continue
                        else:
                            current_trade_name = await get_or_create_trade_name(session, trade_text)

                        dosage_form = models.DosageForm(
                            name_ru=form_text,
                            name_short=form_text[:50],
                            route="enteral" if "внутрь" in form_text or "табл" in form_text else "other"
                        )
                        session.add(dosage_form)
                        await session.flush()

                        dose_match = DOSE_REGEX.search(form_text)
                        strength_val = float(dose_match.group(1).replace(',', '.')) if dose_match else None
                        strength_unit = dose_match.group(2) if dose_match else None

                        product = models.DrugProduct(
                            trade_name_id=current_trade_name.id,
                            dosage_form_id=dosage_form.id,
                            strength_value=strength_val,
                            strength_unit=strength_unit,
                            notes=form_text
                        )
                        session.add(product)
                        await session.flush()
                        saved_products += 1

                        if current_substance:
                            session.add(models.ProductActiveSubstance(
                                drug_product_id=product.id,
                                active_substance_id=current_substance.id,
                                is_primary=True
                            ))
                        
                        if current_group:
                            session.add(models.ProductGroup(
                                drug_product_id=product.id,
                                pharmacotherapeutic_group_id=current_group.id,
                                is_primary=True
                            ))

                        regimen_text = cells[idx_regimen] if idx_regimen < len(cells) else ""
                        course_text = cells[idx_course] if idx_course is not None and idx_course < len(cells) else ""
                        
                        age_match = AGE_REGEX.search(regimen_text)
                        min_age = None
                        if age_match:
                            try:
                                age_val = float(age_match.group(2).replace(',', '.'))
                                if 'мес' in age_match.group(3):
                                    min_age = int(age_val)
                                else:
                                    min_age = int(age_val * 12)
                            except ValueError:
                                pass

                        session.add(models.DosingRegimen(
                            drug_product_id=product.id,
                            regimen_text=regimen_text,
                            course_note=course_text,
                            age_min_months=min_age
                        ))

            await session.commit()
            print("\n✅ Parsing completed successfully!")
            print(f"Tables processed: {table_count}")
            print(f"Products saved (SKU): {saved_products}")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error during parsing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())