<script setup lang="ts">
import { faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BFormTextarea, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import { markup } from "@/components/ObjectStore/configurationMarkdown";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GModal from "../BaseComponents/GModal.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    name: string;
    label: string;
    help: string;
    isSet: boolean;
    multiline?: boolean;
}
const props = defineProps<Props>();

const showEdit = ref<boolean>(false);
const secretValue = ref<string>("");
const editTitle = computed(() => `Edit ${props.label}`);
const helpHtml = computed(() => markup(props.help, true));

function onClick() {
    showEdit.value = true;
}
const emit = defineEmits<{
    (e: "update", secretName: string, secretValue: string): void;
}>();

async function onOk() {
    emit("update", props.name, secretValue.value);
}
</script>

<template>
    <div>
        <div class="ui-form-element section-row">
            <div class="ui-form-title">
                <div class="ui-form-title-text">
                    {{ label }}
                </div>
            </div>
            <div class="ui-form-field">
                <div>
                    <BInputGroup>
                        <BFormInput type="password" value="*****************************" disabled @click="onClick" />
                        <BInputGroupAppend>
                            <GButton @click="onClick">
                                <FontAwesomeIcon :icon="faPen" />
                                Update
                            </GButton>
                        </BInputGroupAppend>
                    </BInputGroup>
                </div>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span class="ui-form-info form-text text-muted" v-html="helpHtml" />
        </div>
        <GModal confirm size="small" :show.sync="showEdit" :title="editTitle" ok-text="Update" @ok="onOk">
            <div>
                <BFormTextarea v-if="multiline" v-model="secretValue" rows="8" no-resize />
                <GFormInput v-else v-model="secretValue" class="w-100" type="password" />
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span class="ui-form-info form-text text-muted" v-html="helpHtml" />
            </div>
        </GModal>
    </div>
</template>

<style lang="scss" scoped>
@import "../Form/_form-elements.scss";
</style>
