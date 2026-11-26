<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const title = computed(() => route.meta.title ?? 'Справочник педиатра');
const page = '/'

</script>

<template>
  <header>
    <nav>
      <RouterLink to={page} class="Icon"></RouterLink>
      <h1 class="header_text">{{ title }}</h1>
    </nav>
  </header>
  <main><RouterView /></main>
</template>

<style scoped>
header {
  width: 100%;
  min-height: 15vh;
  background-color: #0F766E;
  display: flex;
  align-items: center;
}
</style>