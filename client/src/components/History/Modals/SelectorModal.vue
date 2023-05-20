<script setup lang="ts">
import { storeToRefs } from "pinia";
import {
    BModal,
    BFormGroup,
    BFormInput,
    BListGroup,
    BListGroupItem,
    BBadge,
    BButtonGroup,
    BButton,
} from "bootstrap-vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";
import { computed, nextTick, onMounted, onUnmounted, ref, watch, type PropType, type Ref } from "vue";
import localize from "@/utils/localization";
import Heading from "@/components/Common/Heading.vue";
import type { HistorySummary } from "@/stores/historyStore";
import { useRouter } from "vue-router/composables";
import { useHistoryStore } from "@/stores/historyStore";
import Filtering, { contains, expandNameTag } from "@/utils/filtering";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faColumns, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { faListAlt } from "@fortawesome/free-regular-svg-icons";
import { useInfiniteScroll } from "@vueuse/core";

const validFilters = {
    name: contains("name"),
    tag: contains("tags", "tag", expandNameTag),
    annotation: contains("annotation"),
};
const HistoriesFilters = new Filtering(validFilters, false);

type AdditionalOptions = "set-current" | "multi" | "center";

const props = defineProps({
    multiple: { type: Boolean, default: false },
    title: { type: String, default: "Switch to history" },
    histories: { type: Array as PropType<HistorySummary[]>, default: () => [] },
    additionalOptions: { type: Array as PropType<AdditionalOptions[]>, default: () => [] },
    showModal: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "selectHistory", history: HistorySummary): void;
    (e: "selectHistories", histories: { id: string }[]): void;
    (e: "update:show-modal", showModal: boolean): void;
}>();

const propShowModal = computed({
    get: () => {
        return props.showModal;
    },
    set: (val) => {
        emit("update:show-modal", val);
    },
});

const selectedHistories: Ref<{ id: string }[]> = ref([]);
const filter = ref("");
const busy = ref(false);
const modal: Ref<BModal | null> = ref(null);
const scrollableDiv: Ref<HTMLElement | null> = ref(null);

const historyStore = useHistoryStore();

const pinnedHistories: Ref<{ id: string }[]> = computed(() => historyStore.pinnedHistories);
const totalHistoryCount = computed(() => historyStore.totalHistoryCount);
const hasNoResults = computed(() => filter.value && filtered.value.length == 0);
const validFilter = computed(() => filter.value && filter.value.length > 2);
const allLoaded = computed(() => totalHistoryCount.value <= filtered.value.length);

onMounted(async () => {
    await nextTick();
    scrollableDiv.value = document.querySelector(".history-selector-modal .modal-body");
    useInfiniteScroll(scrollableDiv.value, () => loadMore());
    if (props.multiple) {
        selectedHistories.value = [...pinnedHistories.value];
    }
});

onUnmounted(() => {
    // Remove the infinite scrolling behavior
    useInfiniteScroll(scrollableDiv.value, () => {});
});

// @ts-ignore bad library types
library.add(faColumns, faSignInAlt, faListAlt);

watch(
    () => filter.value,
    async (newVal, oldVal) => {
        if (newVal !== "" && validFilter.value && newVal !== oldVal) {
            await loadMore(true);
        }
    }
);

// reactive proxy for props.histories, as the prop is not
// always guaranteed to be reactive for some strange reason.
// TODO: Re investigate when upgrading to vue3
const historiesProxy: Ref<HistorySummary[]> = ref([]);
watch(
    () => props.histories,
    (h) => {
        historiesProxy.value = h;
    },
    {
        immediate: true,
    }
);

const { currentHistoryId } = storeToRefs(useHistoryStore());

const filtered: Ref<HistorySummary[]> = computed(() => {
    let filteredHistories: HistorySummary[] = [];
    if (!filter.value) {
        filteredHistories = historiesProxy.value;
    } else {
        const filters = HistoriesFilters.getFiltersForText(filter.value);
        filteredHistories = historiesProxy.value.filter((history) => {
            if (!HistoriesFilters.testFilters(filters, history)) {
                return false;
            }
            return true;
        });
    }
    return filteredHistories.sort((a, b) => {
        if (a.id == currentHistoryId.value) {
            return -1;
        } else if (b.id == currentHistoryId.value) {
            return 1;
        } else if (a.update_time < b.update_time) {
            return 1;
        } else {
            return -1;
        }
    });
});

function historyClicked(history: HistorySummary) {
    if (props.multiple) {
        const index = selectedHistories.value.findIndex((item) => item.id == history.id);
        if (index !== -1) {
            selectedHistories.value.splice(index, 1);
        } else {
            selectedHistories.value.push({ id: history.id });
        }
    } else {
        emit("selectHistory", history);
        modal.value?.hide();
    }
}

function selectHistories() {
    // set value of pinned histories in store
    emit("selectHistories", selectedHistories.value);
    // set local value equal to updated value from store
    selectedHistories.value = pinnedHistories.value;
    modal.value?.hide();
}

const router = useRouter();

function setCurrentHistory(history: HistorySummary) {
    historyStore.setCurrentHistory(history.id);
    modal.value?.hide();
}

function setCenterPanelHistory(history: HistorySummary) {
    router.push(`/histories/view?id=${history.id}`);
    modal.value?.hide();
}

function openInMulti(history: HistorySummary) {
    router.push("/histories/view_multiple");
    historyStore.pinHistory(history.id);
    modal.value?.hide();
}

/** Loads (paginates) for more histories
 * @param noScroll When set to true, we pass the filter as queryString to loadHistories()
 */
async function loadMore(noScroll = false) {
    if (!busy.value && (noScroll || (!noScroll && !filter.value && !allLoaded.value))) {
        busy.value = true;
        const queryString = filter.value && HistoriesFilters.getQueryString(filter.value);
        await historyStore.loadHistories(true, queryString);
        busy.value = false;
    }
}
</script>

<template>
    <div>
        <b-modal
            ref="modal"
            v-model="propShowModal"
            v-bind="$attrs"
            scrollable
            content-class="history-selector-modal"
            v-on="$listeners">
            <template v-slot:modal-title>
                <Heading h2 inline size="sm">{{ localize(title) }}</Heading>
            </template>

            <b-form-group :description="localize('Filter histories')">
                <b-form-input v-model="filter" type="search" debounce="400" :placeholder="localize('Search Filter')" />
            </b-form-group>

            <b-badge v-if="filter && !validFilter" class="alert-danger w-100">Search string too short!</b-badge>
            <b-alert v-else-if="!busy && hasNoResults" variant="danger" show>No histories found.</b-alert>
            <b-list-group v-if="propShowModal">
                <b-list-group-item
                    v-for="history in filtered"
                    :key="history.id"
                    :data-pk="history.id"
                    button
                    :class="{ current: history.id === currentHistoryId }"
                    :active="selectedHistories.some((h) => h.id === history.id)"
                    @click="() => historyClicked(history)">
                    <div class="d-flex justify-content-between align-items-center">
                        <Heading h3 inline bold size="text">
                            {{ history.name }}
                            <i v-if="history.id === currentHistoryId">(Current)</i>
                        </Heading>

                        <div class="d-flex align-items-center flex-gapx-1">
                            <b-badge v-b-tooltip pill :title="localize('Amount of items in history')">
                                {{ history.count }} {{ localize("items") }}
                            </b-badge>
                            <b-badge v-b-tooltip pill :title="localize('Last edited')">
                                <UtcDate :date="history.update_time" mode="elapsed" />
                            </b-badge>
                        </div>
                    </div>

                    <p v-if="history.annotation" class="my-1">{{ history.annotation }}</p>

                    <StatelessTags
                        v-if="history.tags.length > 0"
                        class="my-1"
                        :value="history.tags"
                        :disabled="true"
                        :max-visible-tags="10" />

                    <div
                        v-if="props.additionalOptions.length > 0"
                        class="d-flex justify-content-end align-items-center mt-1">
                        <b-button-group>
                            <b-button
                                v-if="props.additionalOptions.includes('set-current')"
                                v-b-tooltip
                                :title="localize('Set as current history')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => setCurrentHistory(history)">
                                <FontAwesomeIcon icon="fa-sign-in-alt" />
                            </b-button>

                            <b-button
                                v-if="props.additionalOptions.includes('multi')"
                                v-b-tooltip
                                :title="localize('Open in multi-view')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => openInMulti(history)">
                                <FontAwesomeIcon icon="fa-columns" />
                            </b-button>

                            <b-button
                                v-if="props.additionalOptions.includes('center')"
                                v-b-tooltip
                                :title="localize('Open in center panel')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => setCenterPanelHistory(history)">
                                <FontAwesomeIcon icon="far fa-list-alt" />
                            </b-button>
                        </b-button-group>
                    </div>
                </b-list-group-item>
                <div>
                    <div v-if="allLoaded || filter !== ''" class="list-end my-2">
                        <span v-if="filtered.length == 1">- {{ filtered.length }} history loaded -</span>
                        <span v-else-if="filtered.length > 1">- All {{ filtered.length }} histories loaded -</span>
                    </div>
                    <b-overlay :show="busy" opacity="0.5" />
                </div>
            </b-list-group>

            <template v-slot:modal-footer>
                <div v-if="!allLoaded" class="mr-auto">
                    <i>Showing {{ filtered.length }} out of {{ totalHistoryCount }} histories</i>
                </div>
                <b-button
                    v-if="multiple"
                    v-localize
                    :disabled="selectedHistories.length === 0"
                    variant="primary"
                    @click="selectHistories">
                    Add Selected
                </b-button>
                <span v-else v-localize> Click a history to switch to it </span>
            </template>
        </b-modal>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.history-selector-modal {
    .list-group {
        .list-group-item {
            border-radius: 0;

            &.current {
                border-left: 0.25rem solid $brand-primary;
            }

            &:first-child {
                border-top-left-radius: inherit;
                border-top-right-radius: inherit;
            }

            &:last-child {
                border-bottom-left-radius: inherit;
                border-bottom-right-radius: inherit;
            }
        }
    }
    .list-end {
        width: 100%;
        text-align: center;
        color: $text-light;
    }
}
</style>
