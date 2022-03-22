import router from "./DataManagerRouter";
import DataManagerView from "./DataManagerView";

export const DataManager = {
    router,
    render: (h) => h(DataManagerView),
    created() {
        if (router.currentRoute.name !== "DataManager") {
            router.push({ name: "DataManager" });
        }
    },
};

export default DataManager;
