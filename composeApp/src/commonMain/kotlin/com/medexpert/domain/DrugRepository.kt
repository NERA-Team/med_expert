package com.medexpert.domain

interface DrugRepository {
    /**
     * @param query empty string returns every drug in the reference book.
     * @param mode selects whether trade names or active substances (INN) are matched.
     */
    suspend fun search(query: String, mode: SearchMode): List<DrugSummary>

    suspend fun getDrug(id: Long): DrugProduct?
}
