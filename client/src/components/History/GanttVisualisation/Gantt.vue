<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ historiesLoading }" :user="user">
            <div>
                <b-alert v-if="historiesLoading || isLoading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Gantt Visualization" />
                </b-alert>
                <b-alert v-if="emptyHistory" class="m-2" variant="info" show>
                    <EmptyHistory />
                </b-alert>
                <div class="sticky">
                    <div class="timeButtonsDiv">
                        <button id="QDayView" :disabled="emptyHistory" @click="changeQDayView">Quarter Day View</button>
                        <button id="HDayView" :disabled="emptyHistory" @click="changeHDayView">Half Day View</button>
                        <button id="dayView" :disabled="emptyHistory" @click="changeDayView">Day View</button>
                        <button id="weekView" :disabled="emptyHistory" @click="changeWeekView">Week View</button>
                        <button id="monthView" :disabled="emptyHistory" @click="changeMonthView">Month View</button>
                        <button id="hourView" :disabled="emptyHistory" @click="changeHourView">Hour View</button>
                        <button id="minuteView" :disabled="emptyHistory" @click="changeMinuteView">Minute View</button>
                    </div>
                </div>
                <div>
                    <svg id="gantt"></svg>
                </div>
                <DateTimeModal
                    v-if="openModal"
                    :dateTimeVal="dateTimeVal"
                    :openModal="openModal"
                    @closeModal="closeModal"
                    @changeDate="changeDate" />
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import Gantt from "../../../../node_modules/frappe-gantt";
import { ref, watch, onMounted, computed } from 'vue'
import store from "@/store"
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";
import { keyedColorScheme } from "utils/color";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import { mapState, mapActions } from "pinia";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import LoadingSpan from "components/LoadingSpan";
import DateTimeModal from "./DateTimeModal.vue";
import EmptyHistory from "./EmptyHistory.vue";
import moment from "moment";

export default {
    name: "Gantt",
    components: {
        LoadingSpan,
        EmptyHistory,
        CurrentUser,
        UserHistories,
        DateTimeModal,
    },
    setup() {
        
        // Store
        const piniaStore = useHistoryItemsStore() 

        // Refs
        const historyId = ref(store.getters['history/currentHistoryId'])
        const accountingArray = ref([])
        const accountingArrayMinutes = ref([])
        const historyItems = ref(piniaStore.items[historyId.value])
        const gantt = ref() 
        const ganttView = ref('Hour')
        const currentlyProcessing = ref(false)
        const isLoading = ref(true)
        const openModal = ref(false)
        const emptyHistory = ref(false)
        const dateTimeVal = ref(new Date().toLocaleString("en-GB"))
        const start_time = ref(null)
        const end_time = ref(null)

        
        // Computed properties
        // const history = computed(() => {
        //     return store.getters['history/currentHistoryId'];
        // }) 

        const historyContent = computed( async () => {
            return await piniaStore.items[historyId.value];
        })

        // Hooks
        onMounted(() => {
            getData()
            createKeyedColorForButtons()
        })

        // Watchers
        watch(() => store.getters['history/currentHistoryId'], (newHistoryId, oldHistoryId) => {
            if (newHistoryId !== oldHistoryId) {
                // Making currently processing false so that when you switch to a new History, we can re-fetch the historyContents to refresh the GANTT
                currentlyProcessing.value = false;
                historyId.value = newHistoryId;
                clearGantt()
                ganttView.value = "Day"
                createKeyedColorForButtons();
            }
        })

        watch(historyContent, (newContent, oldContent) => {
            newContent.then((res) => {
                if (res && res.length > 0 && !currentlyProcessing.value) {
                emptyHistory.value = false;
                historyItems.value = res;
                getData();
                } else if (res && res.length == 0 && currentlyProcessing.value) {
                    isLoading.value = false
                    emptyHistory.value = true;
                }
                createKeyedColorForButtons();
            })
        })

        watch(emptyHistory, (newEmpty, oldEmpty) => {
            if (newEmpty === true) {
              clearGantt()    
            }
        })
        
        watch(ganttView, (newval, oldval) => {
            if (oldval == "Minute") {
                makeGantt();
            }
        })

        // Methods/Functions
        function makeGantt() {
            var entries = [];
            if (ganttView.value == "Minute") {
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
          var container = document.getElementsByClassName("gantt");
          if (container && container.length > 0) {
              // We will make .gantt empty so that old data from the visualization is removed and transition to the new one looks more smooth 
              accountingArray.value = [];
              accountingArrayMinutes.value = [];
              container[0].innerHTML = "";
          }
        }

        async function getData() {
            isLoading.value = true;
            currentlyProcessing.value = true;
            historyId.value = store.getters['history/currentHistoryId'];
            accountingArray.value = [];
            accountingArrayMinutes.value = []
            historyItems.value = piniaStore.getHistoryItems( historyId.value, "" );
            if (historyItems.value.length == 0) {
                currentlyProcessing.value = false;
                getHistoryItems();
            }
            if (historyItems.value && historyItems.value.length > 0) {
                for await (const job of historyItems.value) {
                    var Accounting = {};
                    if (job.id) {
                        await store.dispatch('fetchJobMetricsForDatasetId', { datasetId: job.id, datasetType: "hda" });
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
                        }
                    }
                }
                if (accountingArray.value.length > 0) {
                    currentlyProcessing.value = false;
                    makeGantt();
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
                    accountingArrayMinutes.value = accountingArray.value.filter((entry) => {
                        if (moment(end_time.value).isBefore(moment(entry.endTime))) {
                            end_time.value = moment(entry.endTime).format("YYYY-MM-DD HH:mm:ss");
                        }
                        return moment(entry.startTime).isBetween(moment(start_time.value), moment(end_time.value));
                    });
                    makeGantt();
                    gantt.value.change_view_mode("Minute");
                }
            }
        }

        function closeModal() {
            openModal.value = false;
        }

        function changeQDayView() {
            ganttView.value = "Quarter Day";
            gantt.value.change_view_mode("Quarter Day");
        }

        function changeHDayView() {
            ganttView.value = "Half Day";
            gantt.value.change_view_mode("Half Day");
        }

        function changeDayView() {
            ganttView.value = "Day";
            gantt.value.change_view_mode("Day");
        }

        function changeWeekView() {
            ganttView.value = "Week";
            gantt.value.change_view_mode("Week");
        }

        function changeMonthView() {
            ganttView.value = "Month";
            gantt.value.change_view_mode("Month");
        }

        function changeHourView() {
            ganttView.value = "Hour";
            gantt.value.change_view_mode("Hour");
        }

        function changeMinuteView() {
            ganttView.value = "Minute";
            openModal.value = true;
        }

        function createKeyedColorForButtons() {
            createClassWithCSS(
                ".QDayView",
                `background : ${keyedColorScheme("QDayView")["primary"]}; border-color : ${
                    keyedColorScheme("QDayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("QDayView").className = "QDayView";
            createClassWithCSS(
                ".HDayView",
                `background : ${keyedColorScheme("HDayView")["primary"]}; border-color : ${
                    keyedColorScheme("HDayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("HDayView").className = "HDayView";
            createClassWithCSS(
                ".dayView",
                `background : ${keyedColorScheme("dayView")["primary"]}; border-color : ${
                    keyedColorScheme("dayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("dayView").className = "dayView";
            createClassWithCSS(
                ".weekView",
                `background : ${keyedColorScheme("weekView")["primary"]}; border-color : ${
                    keyedColorScheme("weekView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("weekView").className = "weekView";
            createClassWithCSS(
                ".monthView",
                `background : ${keyedColorScheme("monthView")["primary"]}; border-color : ${
                    keyedColorScheme("monthView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("monthView").className = "monthView";
            createClassWithCSS(
                ".hourView",
                `background : ${keyedColorScheme("hourView")["primary"]}; border-color : ${
                    keyedColorScheme("hourView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("hourView").className = "hourView";
            createClassWithCSS(
                ".minuteView",
                `background : ${keyedColorScheme("minuteView")["primary"]}; border-color : ${
                    keyedColorScheme("minuteView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("minuteView").className = "minuteView";
        }

        // return to use in template
        return {
            isLoading,
            emptyHistory,
            changeMonthView,
            changeWeekView,
            changeQDayView,
            changeHDayView,
            changeDayView,
            changeHourView,
            changeMinuteView,
            openModal,
            dateTimeVal,
            closeModal,
            changeDate
        }
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
</style>
