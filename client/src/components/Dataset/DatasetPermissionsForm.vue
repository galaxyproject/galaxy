<script lang="ts" setup>
import { faUsers } from "@fortawesome/free-solid-svg-icons";
import { BFormCheckbox } from "bootstrap-vue";
import { ref, watch } from "vue";

import PortletSection from "../Common/PortletSection.vue";
import FormGeneric from "@/components/Form/FormGeneric.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type FormGenericPropsType = InstanceType<typeof FormGeneric>["$props"];

interface DatasetPermissionsFormProps {
    loading: boolean;
    simplePermissions: boolean;
    title: string;
    checked: boolean;
    formConfig: FormGenericPropsType;
}

const props = defineProps<DatasetPermissionsFormProps>();

const selectedAdvancedForm = ref(false);
const checkedInForm = ref(props.checked);

const emit = defineEmits<{
    (e: "change", value: boolean): void;
}>();

async function change(value: boolean) {
    emit("change", value);
}

watch(props, () => {
    checkedInForm.value = props.checked;
});
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading permission information" />
        <div v-else-if="simplePermissions && !selectedAdvancedForm">
            <PortletSection :icon="faUsers" :title="title">
                <div class="mb-3">
                    <BFormCheckbox v-model="checkedInForm" name="check-button" switch @change="change">
                        Make new datasets private
                    </BFormCheckbox>
                </div>

                <a href="javascript:void(0)" @click="selectedAdvancedForm = true">Show advanced options.</a>
            </PortletSection>
        </div>
        <div v-else>
            <FormGeneric v-bind="formConfig" />
        </div>
    </div>
</template>
