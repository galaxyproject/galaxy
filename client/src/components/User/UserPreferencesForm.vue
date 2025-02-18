<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import {
    getUserPreferencesModel,
    type UserPreferencesKey,
    type UserPreferencesModel,
} from "@/components/User/UserPreferencesModel";
import { useUserStore } from "@/stores/userStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FormGeneric from "@/components/Form/FormGeneric.vue";

interface Props {
    formId: UserPreferencesKey;
}

const props = defineProps<Props>();

const title = computed(() => formConfig.value?.title || "User Preference");

const breadcrumbItems = computed(() => [{ title: "User Preferences", to: "/user" }, { title: title.value }]);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const model = computed<UserPreferencesModel | undefined>(() => {
    if (!currentUser.value?.isAnonymous) {
        return getUserPreferencesModel(currentUser.value?.id);
    } else {
        return undefined;
    }
});

const formConfig = computed(() => {
    return model.value?.[props.formId];
});
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <FormGeneric v-if="formConfig" v-bind="formConfig" :trim-inputs="true" />
    </div>
</template>
