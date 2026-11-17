package com.medexpert.domain

import kotlin.test.Test
import kotlin.test.assertEquals

class DosingRegimenTest {

    @Test
    fun rendersAgeBadgesForAllSupportedRangeShapes() {
        assertEquals("Все возрасты", regimen(null, null).ageBadge)
        assertEquals("с рождения", regimen(0, null).ageBadge)
        assertEquals("до 6 мес.", regimen(null, 6).ageBadge)
        assertEquals("с 1 года", regimen(12, null).ageBadge)
        assertEquals("до 1 года", regimen(0, 12).ageBadge)
        assertEquals("3–6 лет", regimen(36, 72).ageBadge)
        assertEquals("1–3 года", regimen(12, 36).ageBadge)
        assertEquals("с 1 мес. до 1 года", regimen(1, 12).ageBadge)
    }

    private fun regimen(minMonths: Int?, maxMonths: Int?) = DosingRegimen(
        ageMinMonths = minMonths,
        ageMaxMonths = maxMonths,
        regimenText = "Тестовый режим",
    )
}
