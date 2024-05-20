import { useRouter } from "vue-router/composables";

export function useInstanceRouting() {
    const router = useRouter();

    async function goToIndex(query: Record<"message", string>) {
        router.push({
            path: "/file_source_instances/index",
            query: query,
        });
    }

    return {
        goToIndex,
    };
}
