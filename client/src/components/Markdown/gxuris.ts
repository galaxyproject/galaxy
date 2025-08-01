import { type Ref, ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

import type { HelpElementReference } from "./gxuris-types";

import MarkdownHelpPopovers from "./MarkdownHelpPopovers.vue";

function rewriteGxUris(ref: Ref<HTMLDivElement | undefined>, internalHelpReferences: Ref<HelpElementReference[]>) {
    internalHelpReferences.value.length = 0;
    if (ref.value) {
        const links = ref.value.getElementsByTagName("a");
        Array.from(links).forEach((link: HTMLAnchorElement) => {
            if (link.href.startsWith("gxhelp://")) {
                const uri = link.href.substr("gxhelp://".length);
                internalHelpReferences.value.push({ element: link, term: uri });
                link.href = `${getAppRoot()}help/terms/${uri}`;
                link.style.color = "inherit";
                link.style.textDecorationLine = "underline";
                link.style.textDecorationStyle = "dashed";
            }
        });
        const imgs = ref.value.getElementsByTagName("img");
        Array.from(imgs).forEach((img) => {
            if (img.src.startsWith("gxstatic://")) {
                const rest = img.src.substr("gxstatic://".length);
                img.src = `${getAppRoot()}static/${rest}`;
            }
            if (img.src.startsWith("gxdatasetasimage://")) {
                const historyDatasetId = img.src.substr("gxdatasetasimage://".length);
                const imageUrl = `${getAppRoot()}dataset/display?dataset_id=${historyDatasetId}`;
                img.src = imageUrl;
            }
        });
    }
}

export function useGxUris(divRef: Ref<HTMLDivElement | undefined>) {
    const internalHelpReferences = ref<HelpElementReference[]>([]);

    function refresh() {
        rewriteGxUris(divRef, internalHelpReferences);
    }

    watch(divRef, refresh, { immediate: true });

    return {
        internalHelpReferences,
        MarkdownHelpPopovers,
    };
}
