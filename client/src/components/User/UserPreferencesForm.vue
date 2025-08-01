<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watchEffect } from "vue";
import { useRouter } from "vue-router/composables";

import { isRegisteredUser } from "@/api";
import {
    getUserPreferencesModel,
    type UserPreferencesKey,
    type UserPreferencesModel,
} from "@/components/User/UserPreferencesModel";
import { useUserStore } from "@/stores/userStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FormGeneric from "@/components/Form/FormGeneric.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    formId: UserPreferencesKey;
}

const props = defineProps<Props>();

const title = computed(() => formConfig.value?.title || "User Preference");

const breadcrumbItems = computed(() => [{ title: "User Preferences", to: "/user" }, { title: title.value }]);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const router = useRouter();

const loading = ref(true);

const model = computed<UserPreferencesModel | undefined>(() => {
    if (router.currentRoute.params.id) {
        return getUserPreferencesModel(router.currentRoute.params.id);
    } else if (isRegisteredUser(currentUser.value)) {
        return getUserPreferencesModel(currentUser.value.id);
    } else {
        return undefined;
    }
});

const formConfig = computed(() => {
    return model.value?.[props.formId];
});

watchEffect(() => {
    if (model.value) {
        loading.value = false;
    }
});
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <FormGeneric v-if="formConfig" v-bind="formConfig" :trim-inputs="true" />
        <BAlert v-else-if="!loading" show variant="danger"> User preferences not found. </BAlert>
        <BAlert v-else-if="loading" show>
            <LoadingSpan message="Loading user preferences" />
        </BAlert>
    </div>
</template>
