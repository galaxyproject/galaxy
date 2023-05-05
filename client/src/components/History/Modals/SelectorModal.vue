<script setup lang="ts">
import {
    BModal,
    BFormGroup,
    BFormInput,
    BListGroup,
    BListGroupItem,
    BPagination,
    BBadge,
    BButtonGroup,
    BButton,
} from "bootstrap-vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";
import { ref, type PropType, computed, type Ref, watch } from "vue";
import { useFilterObjectArray } from "@/composables/filter";
import localize from "@/utils/localization";
import Heading from "@/components/Common/Heading.vue";
import type { HistorySummary } from "@/stores/historyStore";
import { useRouter } from "vue-router/composables";
import { useHistoryStore } from "@/stores/historyStore";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faColumns, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { faListAlt } from "@fortawesome/free-regular-svg-icons";

type AdditionalOptions = "set-current" | "multi" | "center";

const props = defineProps({
    multiple: { type: Boolean, default: false },
    title: { type: String, default: "Switch to history" },
    histories: { type: Array as PropType<HistorySummary[]>, default: () => [] },
    perPage: { type: Number, default: 8 },
    currentHistoryId: { type: String, required: true },
    additionalOptions: { type: Array as PropType<AdditionalOptions[]>, default: () => [] },
});

const emit = defineEmits<{
    (e: "selectHistory", history: HistorySummary): void;
    (e: "selectHistories", histories: HistorySummary[]): void;
}>();

// @ts-ignore bad library types
library.add(faColumns, faSignInAlt, faListAlt);

const filter = ref("");
const currentPage = ref(1);
const modal: Ref<BModal | null> = ref(null);

// reactive proxy for props.histories, as the prop is not
// always guaranteed to be reactive for some strange reason.
// TODO: Reinvestigate when upgrading to vue3
const histories: Ref<HistorySummary[]> = ref([]);
watch(
    () => props.histories,
    (h) => {
        histories.value = h;
    },
    {
        immediate: true,
    }
);

const filtered = useFilterObjectArray(histories, filter, ["name", "tags", "annotation"]);

watch(
    () => filtered.value,
    () => {
        filtered.value.sort((a, b) => (a.update_time < b.update_time ? 1 : -1));
    }
);

const paginated = computed(() =>
    filtered.value.slice((currentPage.value - 1) * props.perPage, currentPage.value * props.perPage)
);

const totalRows = computed(() => filtered.value.length);
const selectedHistories: Ref<HistorySummary[]> = ref([]);

function historyClicked(history: HistorySummary) {
    if (props.multiple) {
        const index = selectedHistories.value.indexOf(history);
        if (index !== -1) {
            selectedHistories.value.splice(index, 1);
        } else {
            selectedHistories.value.push(history);
        }
    } else {
        emit("selectHistory", history);
        modal.value?.hide();
    }
}

function selectHistories() {
    emit("selectHistories", selectedHistories.value);
    selectedHistories.value = [];
    modal.value?.hide();
}

const router = useRouter();
const historyStore = useHistoryStore();

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
</script>

<template>
    <div>
        <b-modal ref="modal" v-bind="$attrs" content-class="history-selector-modal" v-on="$listeners">
            <template v-slot:modal-title>
                <Heading h2 inline size="sm">{{ localize(title) }}</Heading>
            </template>

            <b-form-group :description="localize('Filter histories')">
                <b-form-input v-model="filter" type="search" debounce="400" :placeholder="localize('Search Filter')" />
            </b-form-group>

            <b-list-group>
                <b-list-group-item
                    v-for="history in paginated"
                    :key="history.id"
                    :data-pk="history.id"
                    button
                    :class="{ current: history.id === props.currentHistoryId }"
                    :active="selectedHistories.includes(history)"
                    @click="() => historyClicked(history)">
                    <div class="d-flex justify-content-between align-items-center">
                        <Heading h3 inline bold size="text">
                            {{ history.name }}
                            <i v-if="history.id === props.currentHistoryId">(Current)</i>
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
            </b-list-group>

            <b-pagination
                v-if="totalRows > props.perPage"
                v-model="currentPage"
                class="mt-4"
                :total-rows="totalRows"
                :per-page="props.perPage"></b-pagination>

            <template v-slot:modal-footer>
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
}
</style>
