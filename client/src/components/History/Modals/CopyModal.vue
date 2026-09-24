<script setup lang="ts">
import { BAlert, BFormRadioGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { type HistorySummary, userOwnsHistory } from "@/api";
import type { ComponentColor } from "@/components/BaseComponents/componentVariants";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import GForm from "@/components/BaseComponents/Form/GForm.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    history: HistorySummary;
    showModal?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showModal: false,
});

const emit = defineEmits<{
    (e: "update:show-modal", value: boolean): void;
    (e: "ok"): void;
}>();

const userStore = useUserStore();
const historyStore = useHistoryStore();

const { currentUser, isAnonymous } = storeToRefs(userStore);

const name = ref("");
const copyAll = ref(false);
const loading = ref(false);
const localShowModal = ref(props.showModal);

const datasetCopyOptions = [
    { text: "Copy only the active, non-deleted datasets.", value: false },
    { text: "Copy all datasets including deleted ones.", value: true },
];

const title = computed(() => {
    return `Copying History: ${props.history.name}`;
});
const saveTitle = computed(() => {
    return loading.value ? "Saving..." : "Copy History";
});
const saveColor = computed<ComponentColor>(() => {
    return loading.value ? "grey" : formValid.value ? "blue" : "grey";
});
const isOwner = computed(() => {
    return userOwnsHistory(currentUser.value, props.history);
});
const newNameValid = computed(() => {
    if (isOwner.value && name.value == props.history.name) {
        return false;
    }
    return name.value.length > 0;
});
const formValid = computed(() => {
    return newNameValid.value;
});

watch(
    () => props.showModal,
    (newVal) => {
        localShowModal.value = newVal;
    },
);
watch(
    () => localShowModal.value,
    (newVal) => {
        emit("update:show-modal", newVal);
    },
);
watch(
    () => props.history,
    (newHistory) => {
        name.value = `Copy of '${newHistory.name}'`;
    },
    {
        immediate: true,
    },
);

async function copy() {
    if (loading.value || !formValid.value) {
        return;
    }
    loading.value = true;
    await historyStore.copyHistory(props.history, name.value, copyAll.value);
    loading.value = false;
    localShowModal.value = false;
    emit("ok");
}
</script>

<template>
    <GModal
        :show.sync="localShowModal"
        size="small"
        :title="title"
        confirm
        :ok-text="localize(saveTitle)"
        :ok-color="saveColor"
        :ok-disabled="loading || !formValid"
        :close-on-ok="false"
        @ok="copy">
        <transition name="fade">
            <BAlert v-localize :show="isAnonymous" variant="warning">
                As an anonymous user, unless you log in or register, you will lose your current history after copying
                this history. You can <a href="/login/start">log in or register here</a>.
            </BAlert>
        </transition>

        <transition name="fade">
            <BAlert v-if="loading" show>
                <LoadingSpan message="Copying History" />
            </BAlert>
        </transition>

        <transition>
            <GForm v-if="!loading" @submit.native.prevent="copy">
                <GFormLabel
                    title="Enter a title for the new history"
                    invalid-feedback="Please enter a valid history title."
                    :state="newNameValid">
                    <GFormInput v-model="name" :state="newNameValid" required />
                </GFormLabel>

                <GFormLabel title="Choose which datasets from the original history to include.">
                    <BFormRadioGroup
                        v-model="copyAll"
                        :options="datasetCopyOptions"
                        name="copy-datasets-options"
                        stacked />
                </GFormLabel>
            </GForm>
        </transition>
    </GModal>
</template>

<style lang="scss">
@import "@/style/scss/transitions.scss";
</style>
