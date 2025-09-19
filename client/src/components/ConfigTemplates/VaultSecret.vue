<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import { markup } from "@/components/ObjectStore/configurationMarkdown";

library.add(faPen);

interface Props {
    name: string;
    label: string;
    help: string;
    isSet: boolean;
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
                            <BButton @click="onClick">
                                <FontAwesomeIcon :icon="faPen" />
                                Update
                            </BButton>
                        </BInputGroupAppend>
                    </BInputGroup>
                </div>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span class="ui-form-info form-text text-muted" v-html="helpHtml" />
        </div>
        <b-modal ref="edit-modal" v-model="showEdit" :title="editTitle" ok-title="Update" @ok="onOk">
            <div>
                <BFormInput v-model="secretValue" type="password" />
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span class="ui-form-info form-text text-muted" v-html="helpHtml" />
            </div>
        </b-modal>
    </div>
</template>

<style lang="scss" scoped>
@import "../Form/_form-elements.scss";
</style>
