import { createRouter, createWebHistory } from "vue-router"
import routes from "@/routes"

const router = createRouter({
    history: createWebHistory(),
    routes: routes,
})

export function goToRepository(id: string) {
    router.push(`/repositories/${id}`)
}

export default router
