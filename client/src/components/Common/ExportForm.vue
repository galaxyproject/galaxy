<script setup lang="ts">
import { computed, ref } from "vue";

import { GButton, GCol, GFormGroup, GInput, GRow } from "@/component-library";
import localize from "@/utils/localization";

import FilesInput from "@/components/FilesDialog/FilesInput.vue";

interface Props {
    what?: string;
    clearInputAfterExport?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    what: "archive",
    clearInputAfterExport: false,
});

const emit = defineEmits<{
    (e: "export", directory: string, name: string): void;
}>();

const directory = ref<string>("");
const name = ref<string>("");

const canExport = computed(() => name.value.length > 0 && directory.value.length > 0);

const directoryDescription = computed(() => localize(`Select a 'remote files' directory to export ${props.what} to.`));

const nameDescription = computed(() => localize("Give the exported file a name."));

const namePlaceholder = computed(() => localize("Name"));

const doExport = () => {
    emit("export", directory.value, name.value);
    if (props.clearInputAfterExport) {
        directory.value = "";
        name.value = "";
    }
};
</script>

<template>
    <div class="export-to-remote-file">
        <GFormGroup id="fieldset-directory" label-for="directory" :description="directoryDescription" class="mt-3">
            <FilesInput id="directory" v-model="directory" mode="directory" :require-writable="true" />
        </GFormGroup>
        <GFormGroup id="fieldset-name" label-for="name" :description="nameDescription" class="mt-3">
            <GInput id="name" v-model="name" :placeholder="namePlaceholder" required />
        </GFormGroup>
        <GRow align-h="end">
            <GCol>
                <GButton
                    v-localize
                    class="export-button"
                    variant="primary"
                    :disabled="!canExport"
                    @click.prevent="doExport">
                    Export
                </GButton>
            </GCol>
        </GRow>
    </div>
</template>