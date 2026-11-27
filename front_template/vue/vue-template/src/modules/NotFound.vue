<script>

import { useRoute } from 'vue-router';
const router = useRoute();

</script>

<template>

    
    <section>

        
        <div class="img" alt="404 NOTFOUND"></div>
        <h1>Ой!</h1>

    </section>
    <section><h2>Кажется, такой страницы нет!</h2>
    <p>Вернемся на <router-link to="/" class="pp">главную страницу?</router-link></p></section>
    

</template>

<style scoped>

    section {
        display: flex;
        
        flex-direction: column;
        align-items: center;
        
    }

    .img {
        width: 35vw;
        height: 35vh;

        background-image: url("../media/png/404.png");

        background-repeat: no-repeat;
        background-size: contain;
    }

    * {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 4vw;
        color: black;
    }

    p > .pp {
        color: #0F766E;
    }

</style>