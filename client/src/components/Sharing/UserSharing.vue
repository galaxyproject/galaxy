<script setup lang="ts">
import axios from "axios";
import { BAlert, BButton, BCard, BCardHeader, BCol, BCollapse, BListGroup, BListGroupItem, BRow } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload";
import { useUserStore } from "@/stores/userStore";
import { assertArray } from "@/utils/assertions";

import type { Item, ShareOption } from "./item";

const props = defineProps<{
    item: Item;
    modelClass: string;
}>();

const emit = defineEmits<{
    (e: "share", userIds: string[], shareOption?: ShareOption): void;
    (e: "error", error: Error): void;
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

const sharingCandidates = ref<Array<{ email: string }>>([]);
const sharingCandidatesAsEmails = computed(() => sharingCandidates.value.map(({ email }) => email));

watch(
    () => props.item.users_shared_with,
    (users) => {
        sharingCandidates.value = [...users];
    },
    { immediate: true }
);

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

    if (currentSearch.value && !sharingCandidatesAsEmails.value && !isValueChosen) {
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
    sharingCandidates.value = [...props.item.users_shared_with];
}

function onSubmit() {
    emit("share", sharingCandidatesAsEmails.value);
}

const noChanges = computed(() => {
    const candidates = [...sharingCandidatesAsEmails.value];
    const sharedWith = [...props.item.users_shared_with.map(({ email }) => email)];

    const newCandidates = candidates.filter((email) => !sharedWith.includes(email));
    const removedShared = sharedWith.filter((email) => !candidates.includes(email));

    return !(newCandidates.length !== 0 || removedShared.length !== 0);
});

const canChangeCount = computed(() => props.item.extra?.can_change.length ?? 0);
const cannotChangeCount = computed(() => props.item.extra?.cannot_change.length ?? 0);

function onMakePublic() {
    emit("share", sharingCandidatesAsEmails.value, "make_public");
}

function onMakePrivate() {
    emit("share", sharingCandidatesAsEmails.value, "make_accessible_to_shared");
}

function onShareAnyway() {
    emit("share", sharingCandidatesAsEmails.value, "no_changes");
}
</script>

<template>
    <div class="user-sharing">
        <div v-if="currentUser && isConfigLoaded && !permissionsChangeRequired">
            <p v-if="props.item.users_shared_with.length === 0">
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

                <div class="share-with-card-buttons">
                    <BButton class="cancel-sharing-with" :disabled="noChanges" @click="onCancel"> Cancel </BButton>
                    <BButton variant="primary" class="submit-sharing-with" :disabled="noChanges" @click="onSubmit">
                        {{ currentSearch ? `Add` : `Save` }}
                    </BButton>
                </div>
            </div>
        </div>

        <BAlert variant="warning" dismissible fade :show="permissionsChangeRequired">
            {{
                canChangeCount > 0
                    ? `${canChangeCount} datasets are exclusively private to you`
                    : `You are not authorized to share ${cannotChangeCount} datasets`
            }}
        </BAlert>

        <BRow v-if="permissionsChangeRequired">
            <BCol v-if="canChangeCount > 0">
                <BCard>
                    <BCardHeader header-tag="header" class="p-1" role="tab">
                        <BButton v-b-toggle.can-share block variant="warning">
                            Datasets can be shared by updating their permissions
                        </BButton>
                    </BCardHeader>

                    <BCollapse id="can-share" visible accordion="can-share-accordion" role="tabpanel">
                        <BListGroup>
                            <BListGroupItem v-for="dataset in props.item.extra?.can_change ?? []" :key="dataset.id">
                                {{ dataset.name }}
                            </BListGroupItem>
                        </BListGroup>
                    </BCollapse>
                </BCard>
            </BCol>

            <BCol v-if="cannotChangeCount > 0">
                <BCard>
                    <BCardHeader header-tag="header" class="p-1" role="tab">
                        <BButton v-b-toggle.cannot-share block variant="danger">
                            Datasets cannot be shared, you are not authorized to change permissions
                        </BButton>
                    </BCardHeader>

                    <BCollapse id="cannot-share" visible accordion="cannot-accordion" role="tabpanel">
                        <BListGroup>
                            <BListGroupItem v-for="dataset in props.item.extra?.cannot_change ?? []" :key="dataset.id">
                                {{ dataset.name }}
                            </BListGroupItem>
                        </BListGroup>
                    </BCollapse>
                </BCard>
            </BCol>

            <BCol>
                <BCard
                    border-variant="primary"
                    header="How would you like to proceed?"
                    header-bg-variant="primary"
                    header-text-variant="white">
                    <BButton v-if="canChangeCount > 0" block @click="onMakePublic"> Make datasets public </BButton>

                    <BButton v-if="canChangeCount > 0" block @click="onMakePrivate">
                        Make datasets private to me and
                        {{ sharingCandidatesAsEmails.join() }}
                    </BButton>

                    <BButton block @click="onShareAnyway"> Share Anyway </BButton>

                    <BButton block variant="warning" @click="onCancel"> Cancel </BButton>
                </BCard>
            </BCol>
        </BRow>
    </div>
</template>

<style scoped lang="scss">
.user-sharing {
    // removes content shifting
    &:deep(.multiselect__input) {
        padding-left: 0;
        padding-top: 2px;
        margin-bottom: 10px;
        font-size: 14px;
    }
}
</style>
