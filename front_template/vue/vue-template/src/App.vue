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
      <router-link to="/"><div class="Icon"></div></router-link>
      <h1 class="header_text">{{ title }}</h1>
    </nav>
  </header>
  <main><RouterView /></main>
</template>

<style scoped>

  

  header {
    width: 100vw;
    min-height: 15vh;
    background-color: #0F766E;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  header > nav {

    width: 60%;
    height: 100%;

    display: inline-flex;

    align-items: center;
    justify-content: space-between;
    
  }

  nav > h1 {
    font-size: 4vw;

    font-family: Arial, Helvetica, sans-serif;
    color: white;
  }
  
  .Icon {

    width: 8.5vw;
    height: 8.5vh;

    background-image: url("./media/svg/logo.svg");
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
  }

  main {
    width: 100vw;
    min-height: 85vh;
  }

</style>

<style>


    .main {
        width: 100%;
    }

</style>