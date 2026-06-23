import { defineStore } from "pinia";
import { computed, type Ref, ref } from "vue";

import { hasHelp as hasHelpTextFromYaml, help as helpTextFromYaml } from "@/components/Help/terms";

import { useDatatypeStore } from "./datatypeStore";

interface DatatypeDescription {
    ext: string;
    description: string | null;
    descriptionUrl: string | null;
}

interface RawDatatypeDescription {
    id: string;
    text: string;
    description: string | unknown | null;
    description_url: string | unknown | null;
    upload_warning: string | unknown | null;
}

export const useHelpTermsStore = defineStore("helpTermsStore", () => {
    const initialized = ref(false);
    const datatypeDescriptions = ref<DatatypeDescription[] | null>(null as DatatypeDescription[] | null);
    const datatypeStore = useDatatypeStore();

    function datatypeDescriptionForExtension(extension: string): DatatypeDescription | null {
        if (!datatypeDescriptions.value) {
            return null;
        }
        for (const description of datatypeDescriptions.value) {
            if (description.ext == extension) {
                return description;
            }
        }
        return null;
    }

    function moreInformationFromUrlMarkdown(ext: string, url: string) {
        return `More information on the datatype ${ext} can be found at [${url}](${url}).`;
    }

    function datatypeDescriptionToMarkdown(datatypeDescription: DatatypeDescription): string {
        const ext = datatypeDescription.ext;
        let description = datatypeDescription.description?.trimEnd();
        const url = datatypeDescription.descriptionUrl;
        if (!description && !url) {
            return `${ext} is a registered Galaxy datatype.`;
        } else if (!description) {
            return moreInformationFromUrlMarkdown(ext, url as string);
        } else if (!url) {
            return description;
        } else {
            if (description.charAt(description.length - 1) != ".") {
                description += ".";
            }
            return `${description}\n\n${moreInformationFromUrlMarkdown(ext, url)}`;
        }
    }

    async function ensureInitialized() {
        if (!initialized.value) {
            await datatypeStore.fetchUploadDatatypes();
            const rawDatatypes = datatypeStore.getUploadDatatypes as RawDatatypeDescription[];
            datatypeDescriptions.value = rawDatatypes.map((datatype: RawDatatypeDescription) => {
                return {
                    ext: datatype.id,
                    description: datatype.description || null,
                    descriptionUrl: datatype.description_url || null,
                } as DatatypeDescription;
            });
            initialized.value = true;
        }
    }

    const loading = computed(() => {
        return !initialized.value;
    });

    function hasHelpText(term: string): boolean {
        if (term.startsWith("galaxy.datatypes.extensions.")) {
            const extension = term.substring("galaxy.datatypes.extensions.".length);
            return datatypeDescriptionForExtension(extension) != null;
        } else {
            return hasHelpTextFromYaml(term);
        }
    }

    function helpText(term: string): string | null {
        if (term.startsWith("galaxy.datatypes.extensions.")) {
            const extension = term.substring("galaxy.datatypes.extensions.".length);
            const description = datatypeDescriptionForExtension(extension);
            if (!description) {
                return null;
            }
            return datatypeDescriptionToMarkdown(description);
        } else {
            return helpTextFromYaml(term);
        }
    }

    return {
        ensureInitialized,
        hasHelpText,
        helpText,
        loading,
    };
});

export function useHelpForTerm(uri: Ref<string>) {
    const termsStore = useHelpTermsStore();
    termsStore.ensureInitialized();

    const loading = computed(() => {
        return termsStore.loading;
    });
    const hasHelp = computed(() => {
        return termsStore.hasHelpText(uri.value);
    });
    const help = computed(() => {
        return termsStore.helpText(uri.value);
    });

    return {
        loading,
        hasHelp,
        help,
    };
}
