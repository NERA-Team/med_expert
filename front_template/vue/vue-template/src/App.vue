<script setup>
    import { ref } from 'vue';
    import { storage } from './preload.js';

    const page = ref(storage.getPage() ?? "1");

</script>

<template>

    <h1>Hello</h1>
    <header>
        <nav>
            <RouterLink to="/" v-on:click="handle">Справочник педиатра</RouterLink>

            <div class="header_text">
                <h1 v-if="page === 0">Справочник педиатра</h1>
                <h1 v-if="page === 1">Лекарства</h1>
                <h1 v-if="page === 2">Лекарство</h1>
                <h1 v-if="page === 4"></h1>
            </div>
        </nav>
    </header>

    <main>
        <RouterView />
    </main>
</template>

<style scoped>


    header {
        width: 100vh;
        height: 15vh;
            
        background-color: #0F766E;
            
        display: inline-flex;
        justify-content: space-between;
    }

    

</style>
