
import {createMemoryHistory, createRouter} from 'vue-router'

import ChooseView from './modules/ChooseView.vue'
import NotFound from './modules/NotFound.vue'

const routes = [

    { path: '/', component: ChooseView, meta: { title: 'Справочник педиатора' } },


    {

        path: '/:pathMatch(.*)*',
        component: NotFound,
        meta: {title: "Not Found!"}

    }

]

export const router = createRouter(
    {
        history: createMemoryHistory(),
        routes,
    }
)