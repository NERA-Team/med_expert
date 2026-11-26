<script setup>
import { ref } from 'vue';

const page = ref(parseInt(localStorage.getItem("page"), 10) || 1);
</script>

<template>
    <header>
        <nav>
            <RouterLink to="/">Справочник педиатра</RouterLink>

            <div class="header_text">
                <h1 v-if="page === 0">Справочник педиатра</h1>
            </div>
        </nav>
    </header>

    <main>
        <RouterView />
    </main>
</template>
