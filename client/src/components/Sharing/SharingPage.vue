<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faCopy, faEdit, faUserPlus, faUserSlash } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { BFormCheckbox } from "bootstrap-vue";
import { computed, nextTick, reactive, ref, watch } from "vue";

import { getGalaxyInstance } from "@/app";
import { useToast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";
import { getFullAppUrl } from "@/utils/utils";

import type { Item, ShareOption } from "./item";

import EditableUrl from "./EditableUrl.vue";
import WorkflowEmbed from "./Embeds/WorkflowEmbed.vue";
import ErrorMessages from "./ErrorMessages.vue";
import UserSharing from "./UserSharing.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faCopy, faEdit, faUserPlus, faUserSlash, faCaretDown, faCaretUp);

const props = defineProps<{
    id: string;
    pluralName: string;
    modelClass: string;
}>();

const errors = ref<string[]>([]);

function addError(newError: string) {
    // temporary turning Set into Array, until we update till Vue 3.0, that supports Set reactivity
    errors.value = Array.from(new Set(errors.value).add(newError));
}

function onErrorDismissed(index: number) {
    errors.value.splice(index, 1);
}

const defaultExtra = () =>
    ({
        can_change: [],
        cannot_change: [],
    } as Item["extra"]);

const item = ref<Item>({
    title: "title",
    username_and_slug: "__username__/__slug__",
    importable: false,
    published: false,
    users_shared_with: [],
    extra: defaultExtra(),
});

const itemUrl = reactive({
    prefix: "",
    slug: "",
});

watch(
    () => item.value.username_and_slug,
    (value) => {
        if (value) {
            const index = value.lastIndexOf("/");

            itemUrl.prefix = getFullAppUrl(value.substring(0, index + 1));
            itemUrl.slug = value.substring(index + 1);
        }
    },
    { immediate: true }
);

const slugUrl = computed(() => `${getAppRoot()}api/${props.pluralName.toLowerCase()}/${props.id}/slug`);

function onChangeSlug(newValue: string) {
    itemUrl.slug = newValue;
}

async function onSubmitSlug(newValue: string) {
    itemUrl.slug = newValue;

    try {
        await axios.put(slugUrl.value, { new_slug: newValue });
    } catch (e) {
        onError(e);
    }
}

const itemStatus = computed(() => (item.value.published ? "accessible via link and published" : "accessible via link"));
const publishedUrl = computed(() => `${getAppRoot()}${props.pluralName.toLocaleLowerCase()}/list_published`);

function onError(axiosError: unknown) {
    addError(errorMessageAsString(axiosError));
}

const ready = ref(false);

async function getSharing() {
    ready.value = false;
    try {
        const response = await axios.get(
            `${getAppRoot()}api/${props.pluralName.toLocaleLowerCase()}/${props.id}/sharing`
        );
        assignItem(response.data, true);
    } catch (e) {
        onError(e);
    }
}

getSharing();

function permissionsChangeRequired(data: Item) {
    if (data.extra) {
        return data.extra.can_change.length > 0 || data.extra.cannot_change.length > 0;
    } else {
        return false;
    }
}

const actions = {
    enableLinkAccess: "enable_link_access",
    disableLinkAccess: "disable_link_access",
    publish: "publish",
    unpublish: "unpublish",
    share_with: "share_with_users",
} as const;

const { success } = useToast();

async function setSharing(
    action: (typeof actions)[keyof typeof actions],
    userId?: string | string[],
    shareOption?: ShareOption
) {
    let userIds: string[] | undefined;
    if (Array.isArray(userId)) {
        userIds = userId;
    } else {
        userIds = userId ? userId.replace(/ /g, "").split(",") : undefined;
    }

    const data = {
        user_ids: userIds,
        share_option: shareOption ? shareOption : undefined,
    };

    try {
        const response = await axios.put(
            `${getAppRoot()}api/${props.pluralName.toLocaleLowerCase()}/${props.id}/${action}`,
            data
        );

        errors.value = [];
        const userIdsSaved = userIds && !permissionsChangeRequired(response.data) && response.data.errors.length === 0;
        assignItem(response.data, userIdsSaved ?? false);

        if (!permissionsChangeRequired(response.data)) {
            success("Sharing preferences saved");
        }
    } catch (e) {
        onError(e);
    }
}

const userSharing = ref<InstanceType<typeof UserSharing>>();

async function assignItem(newItem: Item, overwriteCandidates: boolean) {
    if (newItem.errors) {
        errors.value = newItem.errors;
    }
    item.value = newItem;

    if ((!item.value.extra || newItem.errors?.length) ?? 0 > 0) {
        item.value.extra = defaultExtra();
    }

    if (overwriteCandidates) {
        await nextTick();
        //@ts-ignore incorrect property not found error
        userSharing.value?.reset();
    }

    ready.value = true;
}

function onImportable(importable: boolean) {
    if (importable) {
        setSharing(actions.enableLinkAccess);
    } else {
        item.value.published = false;
        setSharing(actions.disableLinkAccess);
    }
}
function onPublish(published: boolean) {
    if (published) {
        item.value.importable = true;
        setSharing(actions.publish);
    } else {
        setSharing(actions.unpublish);
    }
}

const hasUsername = ref(Boolean(getGalaxyInstance().user.get("username")));
const newUsername = ref("");

const slugSet = computed(() => itemUrl.slug != "__slug__" && itemUrl.prefix != "__username__");

async function setUsername() {
    axios
        .put(`${getAppRoot()}api/users/${getGalaxyInstance().user.id}/information/inputs`, {
            username: newUsername.value || "",
        })
        .then((response) => {
            hasUsername.value = true;
            getSharing();
        })
        .catch(onError);
}

const embedable = computed(() => item.value.importable && props.modelClass.toLocaleLowerCase() === "workflow");
</script>

<template>
    <div class="sharing-page">
        <Heading h1 size="lg" separator>
            <span>
                Share or Publish {{ modelClass }} <span v-if="ready">"{{ item.title }}"</span>
            </span>
        </Heading>

        <ErrorMessages :messages="errors" @dismissed="onErrorDismissed"></ErrorMessages>

        <form v-if="!hasUsername" class="d-flex flex-column flex-gapy-1" @submit.prevent="setUsername()">
            <label>
                To make a {{ modelClass }} accessible via link or publish it, you must create a public username:
                <input v-model="newUsername" class="form-control" type="text" />
            </label>

            <b-button class="align-self-start" type="submit" variant="primary">Set Username</b-button>
        </form>
        <div v-else-if="ready">
            <div class="mb-3">
                <BFormCheckbox v-model="item.importable" switch class="make-accessible" @change="onImportable">
                    Make {{ modelClass }} accessible
                </BFormCheckbox>
                <BFormCheckbox
                    v-if="item.importable"
                    v-model="item.published"
                    class="make-publishable"
                    switch
                    @change="onPublish">
                    Make {{ modelClass }} publicly available in
                    <a :href="publishedUrl" target="_top">Published {{ pluralName }}</a>
                </BFormCheckbox>
            </div>

            <div v-if="item.importable" class="mb-4">
                <div v-if="slugSet">
                    <p>
                        This {{ modelClass }} is currently {{ itemStatus }}.
                        <br />
                        Anyone can view and import this {{ modelClass }} by visiting the following URL:
                    </p>
                    <EditableUrl
                        :prefix="itemUrl.prefix"
                        :slug="itemUrl.slug"
                        @change="onChangeSlug"
                        @submit="onSubmitSlug" />
                </div>
                <div v-else>
                    <p>Currently publishing {{ modelClass }}. A shareable URL will be available here momentarily.</p>
                </div>
            </div>
            <div v-else class="mb-4">
                Access to this {{ modelClass }} is currently restricted so that only you and the users listed below can
                access it. Note that sharing a History will also allow access to all of its datasets.
            </div>

            <div v-if="embedable" class="mb-4">
                <Heading h2 size="md"> Embed {{ modelClass }} </Heading>

                <WorkflowEmbed v-if="props.modelClass.toLowerCase() === 'workflow'" :id="id" />
            </div>

            <Heading h2 size="md"> Share {{ modelClass }} with Individual Users </Heading>

            <UserSharing
                ref="userSharing"
                :item="item"
                :model-class="modelClass"
                @share="(users, option) => setSharing(actions.share_with, users, option)"
                @error="onError"
                @cancel="getSharing" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.sharing-page {
    container-type: inline-size;

    overflow-y: scroll;
}
</style>
