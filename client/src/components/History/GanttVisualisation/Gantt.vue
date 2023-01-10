<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ historiesLoading }" :user="user">
            <div>
                <b-alert v-if="historiesLoading || isLoading" variant="info" show>
                    <LoadingSpan message="Loading Gantt Visualization" />
                </b-alert>
                <b-alert
                    v-else-if="emptyHistory && !historiesLoading && !isLoading && !currentlyProcessing"
                    variant="info"
                    show>
                    No Jobs Exist In This History
                </b-alert>
                <b-alert v-else-if="noMinuteJobs || noMetrics" variant="info" show>
                    {{ message }}
                </b-alert>
                <div class="sticky">
                    <div class="timeButtonsDiv">
                        <button
                            id="QDayView"
                            :disabled="
                                historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Quarter Day'
                            "
                            data-description="change view button"
                            @click="changeQDayView">
                            Quarter Day View
                        </button>
                        <button
                            id="HDayView"
                            :disabled="
                                historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Half Day'
                            "
                            data-description="change view button"
                            @click="changeHDayView">
                            Half Day View
                        </button>
                        <button
                            id="dayView"
                            :disabled="historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Day'"
                            data-description="change view button"
                            @click="changeDayView">
                            Day View
                        </button>
                        <button
                            id="weekView"
                            :disabled="
                                historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Week'
                            "
                            data-description="change view button"
                            @click="changeWeekView">
                            Week View
                        </button>
                        <button
                            id="monthView"
                            :disabled="
                                historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Month'
                            "
                            data-description="change view button"
                            @click="changeMonthView">
                            Month View
                        </button>
                        <button
                            id="hourView"
                            :disabled="
                                historiesLoading || isLoading || emptyHistory || noMetrics || ganttView == 'Hour'
                            "
                            data-description="change view button"
                            @click="changeHourView">
                            Hour View
                        </button>
                        <button
                            id="minuteView"
                            v-b-modal.dateTimeModal
                            :disabled="historiesLoading || isLoading || emptyHistory || noMetrics"
                            data-description="change view button"
                            @click="changeMinuteView">
                            Minute View
                        </button>
                    </div>
                </div>
                <div>
                    <svg id="gantt"></svg>
                </div>
                <b-modal id="dateTimeModal" ref="modal" class="test" v-bind="$attrs" title="Choose a starting time">
                    <DatePicker v-model="date" mode="dateTime">
                        <template v-slot="{ inputValue, inputEvents }">
                            <input class="px-3 py-1 border rounded" :value="inputValue" v-on="inputEvents" />
                        </template>
                    </DatePicker>
                    <template v-slot:modal-footer>
                        <b-button id="confirmDate" variant="primary" @click="changeDate(date, 'confirmed')">
                            Confirm Date
                        </b-button>
                    </template>
                </b-modal>
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import Gantt from "../../../../node_modules/frappe-gantt";
import { ref, watch, onMounted } from "vue";
import store from "@/store";
import { keyedColorScheme } from "@/utils/color";
import { useHistoryItemsStore } from "@/stores/history/historyItemsStore";
import CurrentUser from "@/components/providers/CurrentUser";
import UserHistories from "@/components/providers/UserHistories";
import LoadingSpan from "@/components/LoadingSpan";
import DatePicker from "v-calendar/lib/components/date-picker.umd";
import { BModal } from "bootstrap-vue";
import BootstrapVue from "bootstrap-vue";
import moment from "moment";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    name: "Gantt",
    components: {
        LoadingSpan,
        CurrentUser,
        UserHistories,
        DatePicker,
        BModal,
    },
    setup() {
        // Store
        const piniaStore = useHistoryItemsStore();

        // Refs
        const historyId = ref(store.getters["history/currentHistoryId"]);
        const accountingArray = ref([]);
        const accountingArrayMinutes = ref([]);
        const historyItems = ref(piniaStore.items[historyId.value]);
        const gantt = ref();
        const ganttView = ref("Day");
        const noMinuteJobs = ref(false);
        const currentlyProcessing = ref(false);
        const isLoading = ref(true);
        const emptyHistory = ref(false);
        const dateTimeVal = ref(new Date().toLocaleString("en-GB"));
        const start_time = ref(null);
        const end_time = ref(null);
        const empty_metrics = ref(0);
        const noMetrics = ref(false);
        const message = ref("No Jobs Exist In This History");
        const date = ref(moment().format("YYYY-MM-DD HH:mm:ss"));

        // Hooks
        onMounted(() => {
            createKeyedColorForButtons();
            getData();
        });

        // Watchers
        watch(
            () => store.getters["history/currentHistoryId"],
            (newHistoryId, oldHistoryId) => {
                if (newHistoryId !== oldHistoryId) {
                    // Making currently processing false so that when you switch to a new History, we can re-fetch the historyContents to refresh the GANTT
                    currentlyProcessing.value = false;
                    historyId.value = newHistoryId;
                    empty_metrics.value = 0;
                    noMetrics.value = false;
                    noMinuteJobs.value = false;
                    message.value = "";
                    clearGantt();
                    clearPopups();
                    ganttView.value = "Day";
                    createKeyedColorForButtons();
                }
            }
        );

        watch(historyContent, async (newContent, oldContent) => {
            newContent.then((res) => {
                if (res && res.length > 0 && !currentlyProcessing.value) {
                    emptyHistory.value = false;
                    historyItems.value = res;
                    getData();
                } else if (res && res.length == 0 && !currentlyProcessing.value) {
                    isLoading.value = false;
                    emptyHistory.value = true;
                }
            });
            createKeyedColorForButtons();
        });

        watch(emptyHistory, (newEmpty, oldEmpty) => {
            if (newEmpty === true) {
                clearGantt();
            }
        });

        watch(ganttView, (newval, oldval) => {
            clearPopups();
            if (oldval == "Minute") {
                makeGantt();
            }
        });

        // Methods/Functions
        function makeGantt() {
            var entries = [];
            if (ganttView.value == "Minute") {
                if (accountingArrayMinutes.value.length > 0) {
                    accountingArrayMinutes.value.map((row, idx) => {
                        createClassWithCSS(
                            `.class-${row["id"]} .bar-progress`,
                            `fill : ${keyedColorScheme(`random-${row["label"]}`)["primary"]} !important`
                        );
                        entries.push({
                            id: idx.toString(),
                            job_id: row["id"],
                            name: row["label"],
                            start: row["startTime"],
                            end: row["endTime"],
                            progress: 100,
                            custom_class: `class-${row["id"]}`,
                        });
                    });
                } else {
                    clearGrid();
                }
            } else {
                accountingArray.value.map((row, idx) => {
                    createClassWithCSS(
                        `.class-${row["id"]} .bar-progress`,
                        `fill : ${keyedColorScheme(`random-${row["label"]}`)["primary"]} !important`
                    );
                    entries.push({
                        id: idx.toString(),
                        job_id: row["id"],
                        name: row["label"],
                        start: row["startTime"],
                        end: row["endTime"],
                        progress: 100,
                        custom_class: `class-${row["id"]}`,
                    });
                });
            }
            isLoading.value = false;
            if (entries.length > 0) {
                gantt.value = new Gantt("#gantt", entries, {
                    view_mode: "Day",
                    view_modes: ["Quarter Day", "Half Day", "Day", "Week", "Month", "Hour", "Minute"],
                    arrow_curve: 14,
                    date_format: "DD-MM-YYYY",
                    popup_trigger: "mouseover",
                    start_time: start_time.value,
                    end_time: end_time.value,
                    custom_popup_html: function (task) {
                        return `
                        <div class="popover-container">
                            <div class="popover-header">
                                ${task.job_id}: ${task.name}  
                            </div>
                            <div class="popover-body">
                                Started At: ${task.start}
                                <br>
                                Finished At: ${task.end}
                            </div>  
                        </div>`;
                    },
                });
            }
        }

        function clearGantt() {
            var container = document.querySelector("#gantt");
            if (container) {
                // We will make .gantt empty so that old data from the visualization is removed and transition to the new one looks more smooth
                accountingArray.value = [];
                accountingArrayMinutes.value = [];
                container.innerHTML = "";
            }
        }

        function clearGrid() {
            var parent = document.querySelector("#gantt");
            parent.remove();
            var div_svg = document.createElement("div");
            var xmlns = "http://www.w3.org/2000/svg";
            var svg = document.createElementNS(xmlns, "svg");
            svg.setAttribute("id", "gantt");
            div_svg.appendChild(svg);
            document.querySelector(".gantt-container").appendChild(div_svg);
            noMinuteJobs.value = true;
            message.value = "No jobs lie in the specified time-span";
        }

        async function historyContent() {
            return await piniaStore.items[historyId.value];
        }

        async function getData() {
            isLoading.value = true;
            currentlyProcessing.value = true;
            historyId.value = store.getters["history/currentHistoryId"];
            accountingArray.value = [];
            accountingArrayMinutes.value = [];
            historyItems.value = piniaStore.getHistoryItems(historyId.value, "");
            if (historyItems.value.length == 0) {
                currentlyProcessing.value = false;
                isLoading.value = false;
                emptyHistory.value = true;
                getHistoryItems();
            }
            if (historyItems.value && historyItems.value.length > 0) {
                for await (const job of historyItems.value) {
                    var Accounting = {};
                    if (job.id) {
                        await store.dispatch("fetchJobMetricsForDatasetId", { datasetId: job.id, datasetType: "hda" });
                        const metrics = await store.state?.jobMetrics?.jobMetricsByHdaId[`${job.id}`];
                        if (metrics && metrics[1] && metrics[2]) {
                            Accounting = {
                                label: job.name,
                                id: job.hid,
                                jobid: job.id,
                                startTime: metrics[1].value,
                                endTime: metrics[2].value,
                            };
                            accountingArray.value.push(Accounting);
                        } else {
                            empty_metrics.value += 1;
                        }
                    }
                }
                if (accountingArray.value.length > 0) {
                    currentlyProcessing.value = false;
                    makeGantt();
                }
                if (empty_metrics.value == historyItems.value.length) {
                    isLoading.value = false;
                    noMetrics.value = true;
                    message.value = "No data";
                }
            }
        }

        async function getHistoryItems() {
            if (historyId.value && piniaStore.fetchHistoryItems) {
                try {
                    await piniaStore.fetchHistoryItems(historyId.value, "", 0);
                } catch (error) {
                    console.debug("Gantt error.", error);
                }
            }
        }

        function changeDate(value, status) {
            dateTimeVal.value = value;
            if (status == "confirmed") {
                start_time.value = moment(value).format("YYYY-MM-DD HH:mm:ss");
                end_time.value = moment(value).add(10, "minutes").format("YYYY-MM-DD HH:mm:ss");
                if (start_time.value && end_time.value) {
                    isLoading.value = true;
                    // Finalizing on end_time before filtering records
                    accountingArray.value.forEach((entry) => {
                        if (moment(entry.startTime).isBetween(moment(start_time.value), moment(end_time.value))) {
                            if (moment(end_time.value).isBefore(moment(entry.endTime))) {
                                end_time.value = moment(entry.endTime).format("YYYY-MM-DD HH:mm:ss");
                            }
                        }
                    });
                    // Filtering based on finalized end_time
                    accountingArrayMinutes.value = accountingArray.value.filter((entry) => {
                        return moment(entry.startTime).isBetween(moment(start_time.value), moment(end_time.value));
                    });
                    makeGantt();
                    gantt.value.change_view_mode("Minute");
                    this.$refs.modal.hide();
                }
            }
        }

        function changeQDayView() {
            noMinuteJobs.value = false;
            ganttView.value = "Quarter Day";
            gantt.value.change_view_mode("Quarter Day");
        }

        function changeHDayView() {
            noMinuteJobs.value = false;
            ganttView.value = "Half Day";
            gantt.value.change_view_mode("Half Day");
        }

        function changeDayView() {
            noMinuteJobs.value = false;
            ganttView.value = "Day";
            gantt.value.change_view_mode("Day");
        }

        function changeWeekView() {
            noMinuteJobs.value = false;
            ganttView.value = "Week";
            gantt.value.change_view_mode("Week");
        }

        function changeMonthView() {
            noMinuteJobs.value = false;
            ganttView.value = "Month";
            gantt.value.change_view_mode("Month");
        }

        function changeHourView() {
            noMinuteJobs.value = false;
            ganttView.value = "Hour";
            gantt.value.change_view_mode("Hour");
        }

        function changeMinuteView() {
            ganttView.value = "Minute";
        }

        function clearPopups() {
            const popups = document.getElementsByClassName("popup.wrapper");
            popups.forEach((popup) => {
                popups.innerHTML = "";
            });
        }

        function createKeyedColorForButtons() {
            createClassWithCSS(
                ".QDayView",
                `background : ${keyedColorScheme("QDayView")["primary"]}; border-color : ${
                    keyedColorScheme("QDayView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("QDayView")) {
                document.getElementById("QDayView").className = "QDayView";
            }
            createClassWithCSS(
                ".HDayView",
                `background : ${keyedColorScheme("HDayView")["primary"]}; border-color : ${
                    keyedColorScheme("HDayView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("HDayView")) {
                document.getElementById("HDayView").className = "HDayView";
            }
            createClassWithCSS(
                ".dayView",
                `background : ${keyedColorScheme("dayView")["primary"]}; border-color : ${
                    keyedColorScheme("dayView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("dayView")) {
                document.getElementById("dayView").className = "dayView";
            }
            createClassWithCSS(
                ".weekView",
                `background : ${keyedColorScheme("weekView")["primary"]}; border-color : ${
                    keyedColorScheme("weekView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("weekView")) {
                document.getElementById("weekView").className = "weekView";
            }
            createClassWithCSS(
                ".monthView",
                `background : ${keyedColorScheme("monthView")["primary"]}; border-color : ${
                    keyedColorScheme("monthView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("monthView")) {
                document.getElementById("monthView").className = "monthView";
            }
            createClassWithCSS(
                ".hourView",
                `background : ${keyedColorScheme("hourView")["primary"]}; border-color : ${
                    keyedColorScheme("hourView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("hourView")) {
                document.getElementById("hourView").className = "hourView";
            }
            createClassWithCSS(
                ".minuteView",
                `background : ${keyedColorScheme("minuteView")["primary"]}; border-color : ${
                    keyedColorScheme("minuteView")["darker"]
                } ; color :"black"`
            );

            if (document.getElementById("minuteView")) {
                document.getElementById("minuteView").className = "minuteView";
            }
        }

        // return to use in template
        return {
            isLoading,
            emptyHistory,
            noMinuteJobs,
            noMetrics,
            message,
            ganttView,
            changeMonthView,
            changeWeekView,
            changeQDayView,
            changeHDayView,
            changeDayView,
            changeHourView,
            changeMinuteView,
            currentlyProcessing,
            dateTimeVal,
            changeDate,
            date,
        };
    },
};

function createClassWithCSS(selector, style) {
    if (!document.styleSheets) {
        return;
    }
    if (document.getElementsByTagName("head").length == 0) {
        return;
    }

    var styleSheet;
    var mediaType;

    if (document.styleSheets.length > 0) {
        for (var i = 0, l = document.styleSheets.length; i < l; i++) {
            if (document.styleSheets[i].disabled) {
                continue;
            }
            var media = document.styleSheets[i].media;
            mediaType = typeof media;

            if (mediaType === "string") {
                if (media === "" || media.indexOf("screen") !== -1) {
                    styleSheet = document.styleSheets[i];
                }
            } else if (mediaType == "object") {
                if (media.mediaText === "" || media.mediaText.indexOf("screen") !== -1) {
                    styleSheet = document.styleSheets[i];
                }
            }

            if (typeof styleSheet !== "undefined") {
                break;
            }
        }
    }

    if (typeof styleSheet === "undefined") {
        var styleSheetElement = document.createElement("style");
        styleSheetElement.type = "text/css";
        document.getElementsByTagName("head")[0].appendChild(styleSheetElement);

        for (i = 0; i < document.styleSheets.length; i++) {
            if (document.styleSheets[i].disabled) {
                continue;
            }
            styleSheet = document.styleSheets[i];
        }

        mediaType = typeof styleSheet.media;
    }

    if (mediaType === "string") {
        for (i = 0, l = styleSheet.rules.length; i < l; i++) {
            if (
                styleSheet.rules[i].selectorText &&
                styleSheet.rules[i].selectorText.toLowerCase() == selector.toLowerCase()
            ) {
                styleSheet.rules[i].style.cssText = style;
                return;
            }
        }
        styleSheet.addRule(selector, style);
    } else if (mediaType === "object") {
        var styleSheetLength = styleSheet.cssRules ? styleSheet.cssRules.length : 0;
        for (i = 0; i < styleSheetLength; i++) {
            if (
                styleSheet.cssRules[i].selectorText &&
                styleSheet.cssRules[i].selectorText.toLowerCase() == selector.toLowerCase()
            ) {
                styleSheet.cssRules[i].style.cssText = style;
                return;
            }
        }
        styleSheet.insertRule(selector + "{" + style + "}", styleSheetLength);
    }
}
</script>

<style>
.popover-container {
    width: max-content;
}

.popover-header {
    padding: 0.5rem 1rem;
    margin-bottom: 0;
    border: 1px solid black;
    background-color: #948f8fe2;
    color: white;
    border-top-left-radius: calc(0.3rem - 1px);
    border-top-right-radius: calc(0.3rem - 1px);
}

.popover-body {
    padding: 1rem 1rem;
    color: #212529;
    background-color: white;
    border: 1px solid;
}

.gantt .tick {
    stroke: #666;
}
.sticky {
    position: fixed;
}
.gantt-container {
    position: inherit !important;
}
.gantt {
    margin-top: 50px;
}
.popup-wrapper {
    margin-top: 65px;
    margin-left: 15px;
    margin-right: 15px;
}
.modal-content {
    height: 550px;
}
</style>
