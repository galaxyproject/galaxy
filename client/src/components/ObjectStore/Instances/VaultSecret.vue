<script setup lang="ts">
import { computed, ref } from "vue";

interface Props {
    name: string;
    help: string;
    isSet: boolean;
}
const props = defineProps<Props>();

const showEdit = ref<boolean>(false);
const secretValue = ref<string>("");
const editTitle = computed(() => `Edit ${props.name}`);

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
                    {{ name }}
                </div>
            </div>
            <div class="ui-form-field">
                <div>
                    <b-input-group>
                        <b-form-input type="password" value="*****************************" disabled @click="onClick" />
                        <b-input-group-append>
                            <b-button @click="onClick">
                                <icon icon="edit" />
                                Update
                            </b-button>
                        </b-input-group-append>
                    </b-input-group>
                </div>
            </div>
            <span class="ui-form-info form-text text-muted">
                {{ help }}
            </span>
        </div>
        <b-modal ref="edit-modal" v-model="showEdit" :title="editTitle" ok-title="Update" @ok="onOk">
            <div>
                <b-form-input v-model="secretValue" type="password" />
                <span class="ui-form-info form-text text-muted">
                    {{ help }}
                </span>
            </div>
        </b-modal>
    </div>
</template>

<style lang="scss" scoped>
@import "../../Form/form-elements.scss";
</style>
