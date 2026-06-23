import { createRouter, createWebHistory } from "vue-router"
import routes from "@/routes"

const router = createRouter({
    history: createWebHistory(),
    routes: routes,
})

export function goToRepository(id: string) {
    router.push(`/repositories/${id}`)
}

export function goToMetadataInspector(id: string) {
    router.push(`/repositories/${id}/metadata-inspector`)
}

export default router
