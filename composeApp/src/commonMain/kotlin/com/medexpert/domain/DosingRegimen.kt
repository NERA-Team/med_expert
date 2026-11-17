package com.medexpert.domain

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * One age-specific dosing instruction. Instances are decoded from the
 * `dosing_regimen` JSON column of `drug_product`.
 */
@Serializable
data class DosingRegimen(
    @SerialName("age_min_months") val ageMinMonths: Int? = null,
    @SerialName("age_max_months") val ageMaxMonths: Int? = null,
    @SerialName("regimen_text") val regimenText: String,
    @SerialName("course_note") val courseNote: String? = null,
) {
    val ageBadge: String
        get() = ageRangeLabel(ageMinMonths, ageMaxMonths)
}

internal fun ageRangeLabel(minMonths: Int?, maxMonths: Int?): String {
    fun ageValue(months: Int, genitive: Boolean = false): String {
        if (months < 12) return "$months мес."
        val years = months / 12
        val form = if (genitive) {
            when {
                years % 100 in 11..14 -> "лет"
                years % 10 == 1 -> "года"
                else -> "лет"
            }
        } else {
            when {
                years % 100 in 11..14 -> "лет"
                years % 10 == 1 -> "год"
                years % 10 in 2..4 -> "года"
                else -> "лет"
            }
        }
        return "$years $form"
    }

    fun yearsRangeWord(maxYears: Int): String = when {
        maxYears % 100 in 11..14 -> "лет"
        maxYears % 10 == 1 -> "год"
        maxYears % 10 in 2..4 -> "года"
        else -> "лет"
    }

    return when {
        minMonths == null && maxMonths == null -> "Все возрасты"
        minMonths == null && maxMonths != null -> "до ${ageValue(maxMonths, genitive = true)}"
        maxMonths == null && minMonths == 0 -> "с рождения"
        maxMonths == null && minMonths != null -> "с ${ageValue(minMonths, genitive = true)}"
        minMonths == 0 && maxMonths != null -> "до ${ageValue(maxMonths, genitive = true)}"
        minMonths != null && maxMonths != null -> {
            if (minMonths >= 12 && maxMonths >= 12 && minMonths % 12 == 0 && maxMonths % 12 == 0) {
                val minYears = minMonths / 12
                val maxYears = maxMonths / 12
                "$minYears–$maxYears ${yearsRangeWord(maxYears)}"
            } else {
                "с ${ageValue(minMonths, genitive = true)} до ${ageValue(maxMonths, genitive = true)}"
            }
        }
        else -> "Все возрасты"
    }
}
