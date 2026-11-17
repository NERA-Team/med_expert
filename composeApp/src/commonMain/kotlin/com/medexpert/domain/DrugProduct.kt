package com.medexpert.domain

data class ActiveSubstance(
    val nameRu: String,
    val nameLatin: String? = null,
    val atcCode: String? = null,
)

/**
 * A single trade-name / dosage-form combination shown in search results.
 */
data class DrugSummary(
    val id: Long,
    val tradeName: String,
    val dosageForm: String?,
    val strengthValue: Double?,
    val strengthUnit: String?,
    val groupName: String?,
    val activeSubstances: List<String>,
) {
    val strengthLabel: String? = formatStrength(strengthValue, strengthUnit)

    val primarySubstance: String?
        get() = activeSubstances.firstOrNull()
}

/**
 * Full drug card. [regimens] is decoded from `drug_product.dosing_regimen`.
 */
data class DrugProduct(
    val id: Long,
    val tradeName: String,
    val tradeNameLatin: String?,
    val isOriginal: Boolean,
    val dosageForm: String?,
    val strengthValue: Double?,
    val strengthUnit: String?,
    val groupName: String?,
    val activeSubstances: List<ActiveSubstance>,
    val regimens: List<DosingRegimen>,
) {
    val strengthLabel: String? = formatStrength(strengthValue, strengthUnit)
}

enum class SearchMode(val label: String) {
    TradeName("По названию"),
    Mnn("По МНН"),
}

internal fun formatStrength(value: Double?, unit: String?): String? {
    if (value == null) return unit?.let { "Дозировка: $it" }
    val number = if (value % 1.0 == 0.0) {
        value.toLong().toString()
    } else {
        value.toString().trimEnd('0').trimEnd('.').replace('.', ',')
    }
    return if (unit.isNullOrBlank()) number else "$number $unit"
}
