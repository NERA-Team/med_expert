
import {createMemoryHistory, createRouter} from 'vue-router'

import ChooseView from './modules/ChooseView.vue'

const routes = [

    { path: '/', component: ChooseView, meta: { title: 'Справочник педиатора' } }

]

export const router = createRouter(
    {
        history: createMemoryHistory(),
        routes,
    }
)