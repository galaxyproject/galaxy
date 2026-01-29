<script setup lang="ts">
import { computed, ref, watch } from "vue";

interface Props {
    miscInfo: string;
}

const showErrorHelp = ref(false);
const sharingError = ref(false);

// old sharable error: Attempted to create shared output datasets in objectstore with sharing disabled
// new sharable error: Job attempted to create sharable output datasets in a Galaxy storage with sharing disabled
const sharingErrorRex: RegExp = /with sharing disabled/g;
const knownErrors = [{ regex: sharingErrorRex, modalRef: sharingError }];

const props = defineProps<Props>();

const fixable = computed(() => {
    return knownErrors.some((error) => error.modalRef.value);
});

function checkForKnownErrors() {
    for (const knownError of knownErrors) {
        const regex = knownError.regex;
        if (props.miscInfo.match(regex)) {
            knownError.modalRef.value = true;
        }
    }
}

watch(props, checkForKnownErrors, { immediate: true });

function showHelp() {
    showErrorHelp.value = true;
}
</script>

<template>
    <div class="info">
        <b-modal v-if="sharingError" v-model="showErrorHelp" title="Dataset Sharing Misconfigured" ok-only>
            <p>
                This error message indicates that your history is setup to allow sharing but your job was run in a
                configuration to target a Galaxy storage that explicitly disables sharing.
            </p>
            <p>
                To fix this configure your history so that new datasets are private or target a different storage
                location.
            </p>
            <p>
                To re-configure your history, click the history menu and go to the "Set Permissions" option in the
                dropdown. This should result in a toggle that allows you to configure the history so that new datasets
                are created as private datasets.
            </p>
            <p>
                There are many ways to instead target different storage for your job. This can be selected in the tool
                or workflow form right before you execute your job or a different default for your history or user can
                be chosen that allows for sharing.
            </p>
        </b-modal>
        <span class="value">{{ miscInfo }} <a v-if="fixable" href="#" @click="showHelp">How do I fix this?</a></span>
    </div>
</template>
