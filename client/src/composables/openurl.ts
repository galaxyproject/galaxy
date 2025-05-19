import { useRouter } from "vue-router/composables";

function withPrefix(url: string): string {
    return url.startsWith("/") ? url : `/${url}`;
}

export function useOpenUrl() {
    const router = useRouter();

    function openUrl(url: string, target: string | null = null): void {
        if (!target) {
            router.push(url);
        } else {
            const prefixedUrl = withPrefix(url);
            if (target === "_blank") {
                window.open(prefixedUrl, "_blank");
            } else {
                window.location.href = prefixedUrl;
            }
        }
    }

    return { openUrl };
}
