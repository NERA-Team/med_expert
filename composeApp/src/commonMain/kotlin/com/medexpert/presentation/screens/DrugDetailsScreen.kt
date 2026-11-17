package com.medexpert.presentation.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.medexpert.domain.DosingRegimen
import com.medexpert.domain.DrugProduct
import com.medexpert.presentation.DrugDetailsUiState
import com.medexpert.presentation.DrugDetailsViewModel
import com.medexpert.presentation.components.BrandMark
import com.medexpert.presentation.components.InfoNotice
import com.medexpert.presentation.components.StateMessage
import com.medexpert.presentation.components.Tag
import com.medexpert.presentation.icons.AppIcons

@Composable
fun DrugDetailsScreen(
    viewModel: DrugDetailsViewModel,
    drugId: Long,
    onBack: () -> Unit,
) {
    val state by viewModel.uiState.collectAsState()
    val currentState = state

    LaunchedEffect(drugId) {
        viewModel.load(drugId)
    }

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.075f),
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.background,
                    ),
                ),
            ),
    ) {
        val horizontalPadding = if (maxWidth > 600.dp) 28.dp else 18.dp

        Column(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxHeight()
                .fillMaxWidth()
                .widthIn(max = 920.dp)
                .windowInsetsPadding(WindowInsets.safeDrawing),
        ) {
            DetailsTopBar(
                onBack = onBack,
                horizontalPadding = horizontalPadding,
            )

            when {
                currentState.isLoading -> Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(34.dp),
                            strokeWidth = 3.dp,
                        )
                        Spacer(Modifier.height(16.dp))
                        Text(
                            text = "Открываем карточку…",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }

                currentState.errorMessage != null -> Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    contentAlignment = Alignment.Center,
                ) {
                    StateMessage(
                        title = "Карточка недоступна",
                        message = currentState.errorMessage,
                        icon = AppIcons.Warning,
                        actionLabel = "Повторить",
                        onAction = viewModel::retry,
                    )
                }

                currentState.drug != null -> DetailsContent(
                    drug = currentState.drug,
                    horizontalPadding = horizontalPadding,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun DetailsTopBar(
    onBack: () -> Unit,
    horizontalPadding: androidx.compose.ui.unit.Dp,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = horizontalPadding, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            onClick = onBack,
            shape = CircleShape,
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        ) {
            Box(
                modifier = Modifier.size(42.dp),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = AppIcons.ArrowBack,
                    contentDescription = "Назад",
                    modifier = Modifier.size(21.dp),
                    tint = MaterialTheme.colorScheme.onSurface,
                )
            }
        }

        Spacer(Modifier.width(12.dp))

        Text(
            text = "Карточка препарата",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier.weight(1f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )

        BrandMark(size = 34.dp)
    }
}

@Composable
private fun DetailsContent(
    drug: DrugProduct,
    horizontalPadding: androidx.compose.ui.unit.Dp,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(
            start = horizontalPadding,
            end = horizontalPadding,
            top = 2.dp,
            bottom = 30.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            DrugHeroCard(drug)
        }

        item {
            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "Режимы дозирования",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier.weight(1f),
                )
                Tag(
                    text = drug.regimens.size.toString(),
                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                )
            }
            Spacer(Modifier.height(3.dp))
            Text(
                text = "Возрастные дозы из инструкции по медицинскому применению",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        if (drug.regimens.isEmpty()) {
            item {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                ) {
                    Row(
                        modifier = Modifier.padding(18.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Icon(
                            imageVector = AppIcons.Info,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp),
                            tint = MaterialTheme.colorScheme.primary,
                        )
                        Text(
                            text = "Для этого препарата не указаны возрастные режимы дозирования. Уточните дозу в официальной инструкции.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        } else {
            items(
                items = drug.regimens,
                key = { it.ageMinMonths.toString() + ":" + it.ageMaxMonths.toString() + ":" + it.regimenText },
            ) { regimen ->
                RegimenCard(regimen)
            }
        }

        item {
            Spacer(Modifier.height(8.dp))
            InfoNotice(
                text = "Дозирование подбирает врач с учётом диагноза, массы тела и индивидуальных особенностей пациента. Перед применением ознакомьтесь с полной инструкцией.",
            )
        }
    }
}

@Composable
private fun DrugHeroCard(drug: DrugProduct) {
    val shape = RoundedCornerShape(24.dp)
    val contentColor = MaterialTheme.colorScheme.onPrimaryContainer

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.primaryContainer,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.9f),
                    ),
                ),
            )
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.75f), shape),
    ) {
        // Decorative medical cross, clipped by the card bounds.
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .offset(x = 46.dp, y = (-28).dp)
                .size(136.dp),
        ) {
            Box(
                Modifier
                    .align(Alignment.Center)
                    .width(116.dp)
                    .height(34.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(contentColor.copy(alpha = 0.055f)),
            )
            Box(
                Modifier
                    .align(Alignment.Center)
                    .width(34.dp)
                    .height(116.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(contentColor.copy(alpha = 0.055f)),
            )
        }

        Column(modifier = Modifier.padding(22.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Tag(
                    text = drug.groupName ?: "Лекарственный препарат",
                    icon = AppIcons.MedicalBag,
                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.62f),
                    contentColor = contentColor,
                )

                Spacer(Modifier.weight(1f))

                if (drug.isOriginal) {
                    Tag(
                        text = "Оригинальный препарат",
                        containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                        contentColor = MaterialTheme.colorScheme.onTertiaryContainer,
                    )
                }
            }

            Spacer(Modifier.height(16.dp))
            Text(
                text = drug.tradeName,
                style = MaterialTheme.typography.headlineMedium,
                color = contentColor,
                fontWeight = FontWeight.Bold,
            )
            val latinName = drug.tradeNameLatin
            if (!latinName.isNullOrBlank()) {
                Spacer(Modifier.height(2.dp))
                Text(
                    text = latinName,
                    style = MaterialTheme.typography.bodySmall,
                    color = contentColor.copy(alpha = 0.72f),
                    fontStyle = FontStyle.Italic,
                )
            }

            Spacer(Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                drug.dosageForm?.let { dosageForm ->
                    Tag(
                        text = dosageForm,
                        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.62f),
                        contentColor = contentColor,
                    )
                }
                drug.strengthLabel?.let { strength ->
                    Tag(
                        text = strength,
                        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.62f),
                        contentColor = contentColor,
                    )
                }
            }

            if (drug.activeSubstances.isNotEmpty()) {
                Spacer(Modifier.height(18.dp))
                Text(
                    text = "ДЕЙСТВУЮЩИЕ ВЕЩЕСТВА",
                    style = MaterialTheme.typography.labelSmall,
                    color = contentColor.copy(alpha = 0.65f),
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(8.dp))
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    drug.activeSubstances.forEach { substance ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = substance.nameRu,
                                style = MaterialTheme.typography.bodyMedium,
                                color = contentColor,
                                fontWeight = FontWeight.Medium,
                                modifier = Modifier.weight(1f, fill = false),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            substance.nameLatin?.takeIf { it.isNotBlank() }?.let {
                                Spacer(Modifier.width(7.dp))
                                Text(
                                    text = it,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = contentColor.copy(alpha = 0.62f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            substance.atcCode?.takeIf { it.isNotBlank() }?.let {
                                Spacer(Modifier.width(8.dp))
                                Tag(
                                    text = "ATC $it",
                                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                                    contentColor = contentColor,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RegimenCard(regimen: DosingRegimen) {
    val shape = RoundedCornerShape(18.dp)
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = shape,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(modifier = Modifier.padding(17.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Tag(
                    text = regimen.ageBadge,
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                )
                regimen.courseNote?.takeIf { it.isNotBlank() }?.let { course ->
                    Spacer(Modifier.weight(1f))
                    Tag(
                        text = course,
                        icon = AppIcons.Schedule,
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(12.dp))
            Text(
                text = regimen.regimenText,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface,
            )

            regimen.courseNote?.takeIf { it.isNotBlank() }?.let { course ->
                Spacer(Modifier.height(13.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.65f))
                Spacer(Modifier.height(11.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    Icon(
                        imageVector = AppIcons.Schedule,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = "Курс лечения: $course",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
