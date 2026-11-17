import re

DOSE_REGEX = re.compile(r'(\d+[\.,]?\d*)\s*(мг|мкг|г|мл|ЕД|млн|тыс|%)(?:/(\d+[\.,]?\d*)\s*(мл|г))?', re.IGNORECASE)
AGE_REGEX = re.compile(r'(до|с|старше)\s*(\d+[\.,]?\d*)\s*(лет|года|год|мес|месяцев|месяца)', re.IGNORECASE)
MNN_REGEX = re.compile(r'([А-ЯЁ\s\-]+)\s*([A-Z][a-z]+)', re.UNICODE)
GROUP_REGEX = re.compile(r'^[А-ЯЁ\s\-,()]+$')

def detect_table_type(headers):
    h_str = " ".join(headers).lower()
    
    if "расчет дозировки" in h_str or "принципы дозирования" in h_str:
        return "skip"
    if "сокращение" in h_str or "единица измерения" in h_str:
        return "skip"
    if "рецептурный бланк" in h_str:
        return "skip"

    if "взаимодействующие" in h_str or "результат взаимодействия" in h_str:
        return "interaction"
    
    has_form = "форма" in h_str
    has_name = "торговое" in h_str or "препарат" in h_str or "мнн" in h_str
    
    if has_form and has_name:
        return "drug"
    return "unknown"