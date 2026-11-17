package com.medexpert.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.medexpert.domain.DrugProduct
import com.medexpert.domain.DrugRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DrugDetailsUiState(
    val drugId: Long? = null,
    val drug: DrugProduct? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

class DrugDetailsViewModel(
    private val repository: DrugRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DrugDetailsUiState())
    val uiState: StateFlow<DrugDetailsUiState> = _uiState.asStateFlow()

    private var loadJob: Job? = null

    fun load(drugId: Long) {
        if (_uiState.value.drugId == drugId && _uiState.value.drug != null) return

        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            _uiState.value = DrugDetailsUiState(drugId = drugId, isLoading = true)

            try {
                val drug = repository.getDrug(drugId)
                _uiState.value = if (drug == null) {
                    DrugDetailsUiState(
                        drugId = drugId,
                        isLoading = false,
                        errorMessage = "Препарат не найден в справочнике.",
                    )
                } else {
                    DrugDetailsUiState(
                        drugId = drugId,
                        drug = drug,
                        isLoading = false,
                    )
                }
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (_: Exception) {
                _uiState.value = DrugDetailsUiState(
                    drugId = drugId,
                    isLoading = false,
                    errorMessage = "Не удалось открыть карточку препарата.",
                )
            }
        }
    }

    fun retry() {
        _uiState.value.drugId?.let { id ->
            _uiState.value = _uiState.value.copy(drug = null)
            load(id)
        }
    }
}
