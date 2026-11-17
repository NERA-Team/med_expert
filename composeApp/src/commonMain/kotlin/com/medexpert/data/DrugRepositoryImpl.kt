package com.medexpert.data

import com.medexpert.domain.ActiveSubstance
import com.medexpert.domain.DosingRegimen
import com.medexpert.domain.DrugProduct
import com.medexpert.domain.DrugRepository
import com.medexpert.domain.DrugSummary
import com.medexpert.domain.SearchMode
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json

class DrugRepositoryImpl(
    private val databaseProvider: DatabaseProvider,
    private val json: Json,
) : DrugRepository {

    override suspend fun search(query: String, mode: SearchMode): List<DrugSummary> =
        withContext(Dispatchers.Default) {
            val normalizedQuery = query.trim()
            val database = databaseProvider.get()

            if (normalizedQuery.isEmpty()) {
                return@withContext database.drugQueries
                    .selectAll()
                    .executeAsList()
                    .map { row ->
                        summary(
                            id = row.id,
                            tradeName = row.trade_name,
                            dosageForm = row.dosage_form,
                            strengthValue = row.strength_value,
                            strengthUnit = row.strength_unit,
                            groupName = row.group_name,
                            activeSubstances = row.active_substances,
                        )
                    }
            }

            val titleCaseQuery = normalizedQuery.toTitleCaseVariant()

            when (mode) {
                SearchMode.TradeName -> database.drugQueries
                    .selectByTradeName(normalizedQuery, titleCaseQuery)
                    .executeAsList()
                    .map { row ->
                        summary(
                            id = row.id,
                            tradeName = row.trade_name,
                            dosageForm = row.dosage_form,
                            strengthValue = row.strength_value,
                            strengthUnit = row.strength_unit,
                            groupName = row.group_name,
                            activeSubstances = row.active_substances,
                        )
                    }

                SearchMode.Mnn -> database.drugQueries
                    .selectByMnn(normalizedQuery, titleCaseQuery)
                    .executeAsList()
                    .map { row ->
                        summary(
                            id = row.id,
                            tradeName = row.trade_name,
                            dosageForm = row.dosage_form,
                            strengthValue = row.strength_value,
                            strengthUnit = row.strength_unit,
                            groupName = row.group_name,
                            activeSubstances = row.active_substances,
                        )
                    }
            }
        }

    override suspend fun getDrug(id: Long): DrugProduct? = withContext(Dispatchers.Default) {
        val database = databaseProvider.get()
        val row = database.drugQueries.selectById(id).executeAsOneOrNull()
            ?: return@withContext null

        val substances = database.drugQueries
            .selectActiveSubstances(id)
            .executeAsList()
            .map { substance ->
                ActiveSubstance(
                    nameRu = substance.name_ru,
                    nameLatin = substance.name_latin,
                    atcCode = substance.atc_code,
                )
            }

        DrugProduct(
            id = row.id,
            tradeName = row.trade_name,
            tradeNameLatin = row.name_latin,
            isOriginal = row.is_original == 1L,
            dosageForm = row.dosage_form,
            strengthValue = row.strength_value,
            strengthUnit = row.strength_unit,
            groupName = row.group_name,
            activeSubstances = substances,
            regimens = decodeRegimens(row.dosing_regimen),
        )
    }

    private fun decodeRegimens(rawJson: String?): List<DosingRegimen> {
        if (rawJson.isNullOrBlank()) return emptyList()

        // A malformed row must not take down the whole reference book. Empty
        // regimen lists are rendered with a friendly placeholder in the UI.
        return runCatching { json.decodeFromString<List<DosingRegimen>>(rawJson) }
            .getOrDefault(emptyList())
            .sortedBy { it.ageMinMonths ?: 0 }
    }

    private fun summary(
        id: Long,
        tradeName: String,
        dosageForm: String?,
        strengthValue: Double?,
        strengthUnit: String?,
        groupName: String?,
        activeSubstances: String?,
    ): DrugSummary = DrugSummary(
        id = id,
        tradeName = tradeName,
        dosageForm = dosageForm,
        strengthValue = strengthValue,
        strengthUnit = strengthUnit,
        groupName = groupName,
        activeSubstances = activeSubstances
            .orEmpty()
            .split(',')
            .map(String::trim)
            .filter(String::isNotEmpty)
            .distinct(),
    )
}

/**
 * SQLite's LIKE is case-insensitive only for ASCII. Reference data is stored
 * in title case, so lowercase Cyrillic input is additionally matched with its
 * title-cased variant.
 */
private fun String.toTitleCaseVariant(): String =
    lowercase().replaceFirstChar { character -> character.titlecase() }
