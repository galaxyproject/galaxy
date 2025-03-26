import { ref } from "vue";

import { type HistoryItemSummary } from "@/api";
import STATES from "@/mvc/dataset/states";
import localize from "@/utils/localization";

import { useExtensionFiltering } from "./useExtensionFilter";

interface CommonCollectionBuilderProps {
    extensions?: string[];
    defaultHideSourceItems?: boolean;
}

export function useCollectionCreator(props: CommonCollectionBuilderProps) {
    const removeExtensions = ref(true);
    const hideSourceItems = ref(props.defaultHideSourceItems || false);

    const { hasInvalidExtension, showElementExtension } = useExtensionFiltering(props);

    function onUpdateHideSourceItems(newHideSourceItems: boolean) {
        hideSourceItems.value = newHideSourceItems;
    }

    /** describe what is wrong with a particular element if anything */
    function isElementInvalid(element: HistoryItemSummary): string | null {
        if (element.history_content_type === "dataset_collection") {
            return localize("is a collection, this is not allowed");
        }

        const validState = STATES.VALID_INPUT_STATES.includes(element.state as string);

        if (!validState) {
            return localize("has errored, is paused, or is not accessible");
        }

        if (element.deleted || element.purged) {
            return localize("has been deleted or purged");
        }

        // is the element's extension not a subtype of any of the required extensions?
        if (hasInvalidExtension(element)) {
            return localize(`has an invalid format: ${element.extension}`);
        }
        return null;
    }

    return {
        removeExtensions,
        hideSourceItems,
        hasInvalidExtension,
        onUpdateHideSourceItems,
        isElementInvalid,
        showElementExtension,
    };
}
