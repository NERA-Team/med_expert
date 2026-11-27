
<script>

    import { useRoute } from 'vue-router';

    const route = useRoute();
    

</script>

<template>
    <main>

        <search></search>

        <section>

            <router-link to="/cures">
                <section class="route">

                    <img src="../media/svg/pill.svg" alt="Лекарства">

                </section>
            </router-link>

            <router-link to="/Calculator">
                <section class="route">

                    <img src="../media/svg/calculator.svg" alt="Калькулятор">

                </section>
            </router-link>

            <router-link >
                <section class="route">

                    <img src="../media/svg/dumbbell.svg" alt="Упражнения">

                </section>
            </router-link>

        </section>

    </main>
</template>