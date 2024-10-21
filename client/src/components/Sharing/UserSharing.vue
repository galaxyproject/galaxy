<script setup lang="ts">
import axios from "axios";
import {
    BAlert,
    BButton,
    BCard,
    BCardGroup,
    BFormSelect,
    BFormSelectOption,
    BListGroup,
    BListGroupItem,
    BModal,
} from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload";
import { useUserStore } from "@/stores/userStore";
import { assertArray } from "@/utils/assertions";

import type { Item, ShareOption } from "./item";

import Heading from "../Common/Heading.vue";

const props = defineProps<{
    item: Item;
    modelClass: string;
}>();

const emit = defineEmits<{
    (e: "share", userIds: string[], shareOption?: ShareOption): void;
    (e: "error", error: Error): void;
    (e: "cancel"): void;
}>();

const { currentUser } = storeToRefs(useUserStore());
const { config, isConfigLoaded } = useConfig(false);

const permissionsChangeRequired = computed(() => {
    if (props.item.extra) {
        return props.item.extra.can_change.length > 0 || props.item.extra.cannot_change.length > 0;
    } else {
        return false;
    }
});

const userIsAdmin = computed(() => currentUser.value && "is_admin" in currentUser.value && currentUser.value.is_admin);
const exposeEmails = computed(() => config.value.expose_user_email || userIsAdmin.value);

const sharingCandidates = ref<Array<{ email: string }>>([...(props.item.users_shared_with ?? [])]);
const sharingCandidatesAsEmails = computed(() => sharingCandidates.value.map(({ email }) => email));

function reset() {
    sharingCandidates.value = [...(props.item.users_shared_with ?? [])];
}

const userOptions = ref<Array<{ email: string }>>([]);
const currentSearch = ref("");

async function onSearchChanged(searchValue: string) {
    currentSearch.value = searchValue;
    if (!exposeEmails.value) {
        userOptions.value = [{ email: searchValue }];
    } else if (searchValue.length < 3) {
        userOptions.value = [];
    } else {
        try {
            const response = await axios.get(`${getAppRoot()}api/users?f_email=${searchValue}`);
            const data = response.data;
            assertArray(data);

            userOptions.value = (data as Array<{ email: string }>).filter(
                (value) =>
                    value &&
                    typeof value === "object" &&
                    "email" in value &&
                    typeof value.email === "string" &&
                    !sharingCandidatesAsEmails.value.includes(value.email)
            );
        } catch (e) {
            emit("error", e as Error);
        }
    }
}

function onBlur() {
    const isValueChosen = sharingCandidates.value.some(({ email }) => email === currentSearch.value);

    if (currentSearch.value && !exposeEmails.value && !isValueChosen) {
        sharingCandidates.value.push({ email: currentSearch.value });
    }
}

function onRemove(user: { email: string }) {
    const index = sharingCandidates.value.indexOf(user);

    if (index >= 0) {
        sharingCandidates.value.splice(index, 1);
    }
}

const charactersThresholdWarning = "Enter at least 3 characters to see suggestions";
const elementsNotFoundWarning = "No elements found. Consider changing the search query";

function onCancel() {
    sharingCandidates.value = [...(props.item.users_shared_with ?? [])];
    emit("cancel");
}

function onSubmit() {
    emit("share", sharingCandidatesAsEmails.value);
}

const noChanges = computed(() => {
    const candidates = [...sharingCandidatesAsEmails.value];
    const sharedWith = [...(props.item.users_shared_with ?? []).map(({ email }) => email)];

    const newCandidates = candidates.filter((email) => !sharedWith.includes(email));
    const removedShared = sharedWith.filter((email) => !candidates.includes(email));

    return !(newCandidates.length !== 0 || removedShared.length !== 0);
});

const canChangeCount = computed(() => props.item.extra?.can_change.length ?? 0);
const cannotChangeCount = computed(() => props.item.extra?.cannot_change.length ?? 0);

const selectedSharingOption = ref<ShareOption>("make_public");

function onUpdatePermissions() {
    emit("share", sharingCandidatesAsEmails.value, selectedSharingOption.value);
}

defineExpose({
    reset,
});
</script>

<template>
    <div class="user-sharing">
        <div v-if="currentUser && isConfigLoaded">
            <p v-if="props.item.users_shared_with?.length === 0">
                You have not shared this {{ props.modelClass }} with any users.
            </p>
            <p v-else>
                The following users will see this {{ modelClass }} in their {{ modelClass }} list and will be able to
                view, import and run it.
            </p>

            <div class="share_with_view">
                <Multiselect
                    v-model="sharingCandidates"
                    :options="userOptions"
                    :clear-on-select="true"
                    :multiple="true"
                    :internal-search="false"
                    :max-height="exposeEmails ? 300 : 0"
                    label="email"
                    tack-by="email"
                    placeholder="Please specify user email"
                    @remove="onRemove"
                    @search-change="onSearchChanged"
                    @close="onBlur">
                    <template v-if="!sharingCandidates" slot="caret">
                        <div></div>
                    </template>

                    <template v-slot:tag="{ option, remove }">
                        <span class="multiselect__tag remove_sharing_with" :data-email="option.email">
                            <span>{{ option.email }}</span>
                            <i
                                aria-hidden="true"
                                tabindex="0"
                                class="multiselect__tag-icon"
                                @click="remove(option)"
                                @keyup.enter.space="remove(option)"></i>
                        </span>
                    </template>

                    <template v-if="sharingCandidates" slot="noResult">
                        <div v-if="currentSearch.length < 3">
                            {{ charactersThresholdWarning }}
                        </div>
                        <div v-else>
                            {{ elementsNotFoundWarning }}
                        </div>
                    </template>

                    <template slot="noOptions">
                        <div v-if="currentSearch.length < 3">
                            {{ charactersThresholdWarning }}
                        </div>
                        <div v-else>
                            {{ elementsNotFoundWarning }}
                        </div>
                    </template>
                </Multiselect>

                <div class="share-with-card-buttons mt-2 w-100 d-flex justify-content-end flex-gapx-1">
                    <BButton class="cancel-sharing-with" :disabled="noChanges" @click="onCancel"> Cancel </BButton>
                    <BButton variant="primary" class="submit-sharing-with" :disabled="noChanges" @click="onSubmit">
                        {{ currentSearch ? `Add` : `Save` }}
                    </BButton>
                </div>
            </div>
        </div>

        <BModal
            :visible="permissionsChangeRequired"
            size="xl"
            no-close-on-backdrop
            scrollable
            dialog-class="user-sharing-modal"
            @ok="onUpdatePermissions"
            @cancel="onCancel"
            @close="onCancel">
            <template v-slot:modal-title>
                <Heading inline h2 size="md"> Permissions Change Required </Heading>
            </template>

            <BAlert variant="warning" dismissible :show="permissionsChangeRequired && canChangeCount > 0">
                This {{ modelClass }} contains {{ canChangeCount }}
                {{ canChangeCount === 1 ? "dataset which is" : "datasets which are" }} exclusively private to you. You
                need to update {{ canChangeCount === 1 ? "its" : "their" }} permissions, in order to share
                {{ canChangeCount === 1 ? "it" : "them" }}.
            </BAlert>

            <BAlert variant="danger" dismissible :show="permissionsChangeRequired && cannotChangeCount > 0">
                This {{ modelClass }} contains {{ cannotChangeCount }}
                {{ cannotChangeCount === 1 ? "dataset" : "datasets" }} which you are not authorized to share.
            </BAlert>

            <BCard
                border-variant="primary"
                header="How would you like to proceed?"
                header-bg-variant="primary"
                header-text-variant="white"
                class="mb-4">
                <BFormSelect v-model="selectedSharingOption">
                    <BFormSelectOption value="make_public"> Make datasets public </BFormSelectOption>
                    <BFormSelectOption value="make_accessible_to_shared">
                        Make datasets private to me and users this {{ modelClass }} is shared with
                    </BFormSelectOption>
                    <BFormSelectOption value="no_changes"> Share {{ modelClass }} anyways </BFormSelectOption>
                </BFormSelect>
            </BCard>

            <BCardGroup deck>
                <BCard
                    v-if="canChangeCount > 0"
                    header="The following datasets can be shared by updating their permissions">
                    <BListGroup>
                        <BListGroupItem v-for="dataset in props.item.extra?.can_change ?? []" :key="dataset.id">
                            {{ dataset.name }}
                        </BListGroupItem>
                    </BListGroup>
                </BCard>

                <BCard
                    v-if="cannotChangeCount > 0"
                    header="The following datasets cannot be shared, you are not authorized to change their permissions">
                    <BListGroup>
                        <BListGroupItem v-for="dataset in props.item.extra?.cannot_change ?? []" :key="dataset.id">
                            {{ dataset.name }}
                        </BListGroupItem>
                    </BListGroup>
                </BCard>
            </BCardGroup>
        </BModal>
    </div>
</template>

<style>
.user-sharing-modal {
    width: 100%;
}
</style>
