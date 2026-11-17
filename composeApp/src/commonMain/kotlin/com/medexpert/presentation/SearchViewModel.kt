package com.medexpert.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.medexpert.domain.DrugRepository
import com.medexpert.domain.DrugSummary
import com.medexpert.domain.SearchMode
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SearchUiState(
    val query: String = "",
    val mode: SearchMode = SearchMode.TradeName,
    val results: List<DrugSummary> = emptyList(),
    val isLoading: Boolean = true,
    val errorMessage: String? = null,
    val hasLoadedOnce: Boolean = false,
) {
    val isEmpty: Boolean
        get() = hasLoadedOnce && !isLoading && errorMessage == null && results.isEmpty()
}

class SearchViewModel(
    private val repository: DrugRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SearchUiState())
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()

    private var searchJob: Job? = null

    init {
        executeSearch(immediate = true)
    }

    fun onQueryChange(query: String) {
        if (query == _uiState.value.query) return
        _uiState.update { it.copy(query = query) }
        executeSearch(immediate = false)
    }

    fun onModeChange(mode: SearchMode) {
        if (mode == _uiState.value.mode) return
        _uiState.update { it.copy(mode = mode) }
        executeSearch(immediate = true)
    }

    fun retry() {
        executeSearch(immediate = true)
    }

    private fun executeSearch(immediate: Boolean) {
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            if (!immediate) delay(SEARCH_DEBOUNCE_MS)

            val snapshot = _uiState.value
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }

            try {
                val results = repository.search(snapshot.query, snapshot.mode)
                _uiState.update {
                    it.copy(
                        results = results,
                        isLoading = false,
                        errorMessage = null,
                        hasLoadedOnce = true,
                    )
                }
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (_: Exception) {
                _uiState.update {
                    it.copy(
                        results = emptyList(),
                        isLoading = false,
                        errorMessage = "Не удалось загрузить справочник. Попробуйте ещё раз.",
                        hasLoadedOnce = true,
                    )
                }
            }
        }
    }

    private companion object {
        const val SEARCH_DEBOUNCE_MS = 180L
    }
}
