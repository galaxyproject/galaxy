import { defineStore } from "pinia";
import { computed, type Ref, ref, watch } from "vue";

import { hasHelp as hasHelpTextFromYaml, help as helpTextFromYaml } from "@/components/Help/terms";
import { memoizeUntilRejected } from "@/utils/sharedPromise";

import { useDatatypeStore } from "./datatypeStore";

const DATATYPE_TERM_PREFIX = "galaxy.datatypes.extensions.";

function isDatatypeTerm(term: string): boolean {
    return term.startsWith(DATATYPE_TERM_PREFIX);
}

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
    const loadFailed = ref(false);
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

    async function loadDatatypeDescriptions() {
        loadFailed.value = false;
        try {
            await datatypeStore.fetchUploadDatatypes();
        } catch (err) {
            loadFailed.value = true;
            throw err;
        }
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

    /** Load datatype descriptions, needed only for `galaxy.datatypes.extensions.*` terms. Retried after a failure. */
    const ensureInitialized = memoizeUntilRejected(loadDatatypeDescriptions);

    /** True until datatype descriptions are loaded or the last load failed. */
    const loading = computed(() => {
        return !initialized.value && !loadFailed.value;
    });

    function hasHelpText(term: string): boolean {
        if (isDatatypeTerm(term)) {
            const extension = term.substring(DATATYPE_TERM_PREFIX.length);
            return datatypeDescriptionForExtension(extension) != null;
        } else {
            return hasHelpTextFromYaml(term);
        }
    }

    function helpText(term: string): string | null {
        if (isDatatypeTerm(term)) {
            const extension = term.substring(DATATYPE_TERM_PREFIX.length);
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

    watch(
        uri,
        (term) => {
            if (isDatatypeTerm(term)) {
                // A failure ends loading without help; the next datatype term retries.
                termsStore.ensureInitialized().catch((err) => {
                    console.log("Error: unable to load datatypes", err);
                });
            }
        },
        { immediate: true },
    );

    const loading = computed(() => {
        return isDatatypeTerm(uri.value) && termsStore.loading;
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
