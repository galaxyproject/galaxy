import { useRouter } from "vue-router/composables";

export function buildInstanceRoutingComposable(index: string) {
    return () => {
        const router = useRouter();

        async function goToIndex(query: Record<"message", string>) {
            router.push({
                path: index,
                query: query,
            });
        }

        return {
            goToIndex,
        };
    };
}
