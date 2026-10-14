<script setup lang="ts">
import { faUserLock, faUsersCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

interface Props {
    miscInfo: string;
    historyId: string;
}

const router = useRouter();

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

function goToHistoryAccessibility() {
    router.push(`/histories/sharing?id=${props.historyId}`);
    showErrorHelp.value = false;
}

function showHelp() {
    showErrorHelp.value = true;
}
</script>

<template>
    <div class="info">
        <GModal
            v-if="sharingError"
            :show="showErrorHelp"
            title="Dataset Sharing Misconfigured"
            size="small"
            @close="showErrorHelp = false">
            <p>
                This error message indicates that your history is setup to allow sharing but your job was run in a
                configuration to target a Galaxy storage that explicitly disables sharing.
            </p>
            <p>
                To fix this configure your history so that new datasets are private or target a different storage
                location.
            </p>
            <p>
                To re-configure your history, click on the manage access link below which will take you to the
                <i>"Share & Manage Access"</i>
                view for this dataset's history. Switch to the
                <i>"Set Permissions"</i>
                (<FontAwesomeIcon :icon="faUserLock" />) tab in this view which has a toggle that allows you to
                configure the history so that new datasets are created as private datasets.
            </p>
            <p>
                <GLink @click="goToHistoryAccessibility">
                    <FontAwesomeIcon :icon="faUsersCog" />
                    Click here to manage access for this dataset's history
                </GLink>
            </p>
            <p>
                There are many ways to instead target different storage for your job. This can be selected in the tool
                or workflow form right before you execute your job or a different default for your history or user can
                be chosen that allows for sharing.
            </p>
        </GModal>
        <span class="value">{{ miscInfo }} <GLink v-if="fixable" @click="showHelp">How do I fix this?</GLink></span>
    </div>
</template>
