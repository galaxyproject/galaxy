<script lang="ts" setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUsers } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox } from "bootstrap-vue";
import { ref, watch } from "vue";

import FormGeneric from "@/components/Form/FormGeneric.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type FormGenericPropsType = InstanceType<typeof FormGeneric>["$props"];

library.add(faUsers);

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
            <div class="ui-portlet-section">
                <div class="portlet-header">
                    <span class="portlet-title">
                        <FontAwesomeIcon :icnon="faUsers" class="portlet-title-icon mr-1" />

                        <b itemprop="name" class="portlet-title-text">{{ title }}</b>
                    </span>
                </div>

                <div class="portlet-content">
                    <div class="mb-3 mt-3">
                        <BFormCheckbox v-model="checkedInForm" name="check-button" switch @change="change">
                            Make new datasets private
                        </BFormCheckbox>
                    </div>

                    <a href="#" @click="selectedAdvancedForm = true">Show advanced options.</a>
                </div>
            </div>
        </div>
        <div v-else>
            <FormGeneric v-bind="formConfig" />
        </div>
    </div>
</template>
