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
const charactersThresholdWarning = "请输入至少3个字符以查看建议";
const elementsNotFoundWarning = "未找到任何元素。请考虑更改搜索查询";

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
                您尚未与任何用户共享此{{ props.modelClass }}。
            </p>
            <p v-else>
                以下用户将在他们的{{ modelClass }}列表中看到此{{ modelClass }}，并且能够查看、导入和运行它。
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
                    placeholder="请指定用户邮箱"
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
                    <BButton class="cancel-sharing-with" :disabled="noChanges" @click="onCancel">取消</BButton>
                    <BButton variant="primary" class="submit-sharing-with" :disabled="noChanges" @click="onSubmit">
                        {{ currentSearch ? `添加` : `保存` }}
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
                <Heading inline h2 size="md">需要更改权限</Heading>
            </template>

            <BAlert variant="warning" dismissible :show="permissionsChangeRequired && canChangeCount > 0">
                此{{ modelClass }}包含{{ canChangeCount }}个
                {{ canChangeCount === 1 ? "数据集，它是" : "数据集，它们是" }}您专属的私有数据。
                您需要更新{{ canChangeCount === 1 ? "它的" : "它们的" }}权限，才能共享
                {{ canChangeCount === 1 ? "它" : "它们" }}。
            </BAlert>

            <BAlert variant="danger" dismissible :show="permissionsChangeRequired && cannotChangeCount > 0">
                此{{ modelClass }}包含{{ cannotChangeCount }}个
                {{ cannotChangeCount === 1 ? "数据集" : "数据集" }}，您无权共享这些数据集。
            </BAlert>

            <BCard
                border-variant="primary"
                header="您想如何处理？"
                header-bg-variant="primary"
                header-text-variant="white"
                class="mb-4">
                <BFormSelect v-model="selectedSharingOption">
                    <BFormSelectOption value="make_public">将数据集设为公开</BFormSelectOption>
                    <BFormSelectOption value="make_accessible_to_shared">
                        将数据集设为仅对我和此{{ modelClass }}的共享用户可见
                    </BFormSelectOption>
                    <BFormSelectOption value="no_changes">仍然共享此{{ modelClass }}</BFormSelectOption>
                </BFormSelect>
            </BCard>

            <BCardGroup deck>
                <BCard
                    v-if="canChangeCount > 0"
                    header="通过更新以下数据集的权限，可以共享这些数据集">
                    <BListGroup>
                        <BListGroupItem v-for="dataset in props.item.extra?.can_change ?? []" :key="dataset.id">
                            {{ dataset.name }}
                        </BListGroupItem>
                    </BListGroup>
                </BCard>

                <BCard
                    v-if="cannotChangeCount > 0"
                    header="以下数据集无法共享，您无权更改它们的权限">
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
