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

export function contentsLocation(id: string, revision?: string | null, file?: string | null): string {
    const query: Record<string, string> = {}
    if (revision) {
        query.revision = revision
    }
    if (file) {
        query.file = file
    }
    return router.resolve({ path: `/repositories/${id}/contents`, query }).fullPath
}

export default router
