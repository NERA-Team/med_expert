
<script>

    import { useRoute } from 'vue-router';

    const route = useRoute();
    

</script>

<template>
    <main>

        <section class="search"></section>

        <section class="sections">

            <router-link to="/cures" class="routes">
                <section class="route">

                    <img class="icon" src="../media/svg/pill.svg" alt="Лекарства">

                    <section>

                        <h2>Лекарства</h2>
                        <p>Поиск препаратов: <br>по группе, международному названию и торговому названию</p>

                    </section>

                    <img class="sec_icon" src="../media/svg/section.svg" alt="section">

                </section>
            </router-link>

            <router-link to="/Calculator" class="routes">
                <section class="route">

                    <img class="icon" src="../media/svg/calculator.svg" alt="Калькулятор">

                    <section>

                        <h2>Калькулятор</h2>
                        <p>Расчет дозы по весу и возрасту ребенка</p>

                    </section>

                    <img class="sec_icon" src="../media/svg/section.svg" alt="section">

                </section>
            </router-link>

            <router-link to="/train" class="routes">
                <section class="route">

                    <img class="icon" src="../media/svg/dumbbell.svg" alt="Упражнения">

                    <section>

                        <h2>Упражнения</h2>
                        <p>Тесты и клинические задачи</p>

                    </section>

                    <img class="sec_icon" src="../media/svg/section.svg" alt="section">

                </section>
            </router-link>

        </section>

    </main>

    <footer>

        <h4>Этот справочник содержит информацию для медицинских специалистов. 
           Данные носят информационный характер и не заменяют клиническое решение врача.</h4>

        
        <section>
            <router-link to="/about"></router-link>
            <router-link to="/contacts"></router-link>
        </section>

    </footer>
</template>

<style scoped>

    main {
        width: 100vw;
        height: 70vh;
        display: flex;

        flex-direction: column;
        
        align-items: center;
        justify-content: center;
    }

    .search {
        height: 20%;
        width: 60%;
    }

    .sections {

        display: flex;
        flex-direction: column;

        justify-content: space-between;

        height: 80%;
        width: 80%;

        margin-bottom: 5%;
        text-decoration: none;
    }

    .routes {

        height: 30%;
        width: 100%;

        display: flex;
        justify-content: center;
        align-items: center;

        border: 0.25vh solid rgba(128, 128, 128, 0.4);
        border-radius: 1.5vh;

        text-decoration: none;
    }

    .route {

        width: 90%;
        height: 100%;

        display: flex;
        align-items: center;
        justify-content: space-between;

    }

    .route > section {
        width: 70%;
    }

    section > h2 {
        color: rgba(0, 0, 0, 0.8);
        font-size: 2.5vw;
        font-weight: 800;
    }

    section > p {
        color: #c4c4c4;
        font-size: 2vw;
    }

    .icon {
        width: 10vw;
        height: 10vh;
    }

    .sec_icon {
        width: 2.5vw;
        height: 2.5vh;
    }


    footer {
        border-top: 0.5vh solid #0F766E;

        display: flex;
        flex-direction: column;

        justify-content: center;
        align-items: center;
        text-align: center;
    }
</style>