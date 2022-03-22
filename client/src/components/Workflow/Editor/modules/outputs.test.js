import { allLabels, ActiveOutputs } from "./outputs";

describe("Workflow Outputs", () => {
    it("test output label handling", () => {
        // Test adding initial node
        const activeOutputs = new ActiveOutputs();
        const outputs = [{ name: "output_0" }, { name: "output_1" }, { name: "output_2" }];
        const incoming = [
            { output_name: "output_0", label: "label_0" },
            { output_name: "output_1", label: "label_0" },
            { output_name: "output_2", label: "label_1" },
        ];
        activeOutputs.initialize(outputs, incoming);
        expect(Object.keys(allLabels).length).toBe(2);
        expect(allLabels["label_0"]).toBe(true);
        expect(allLabels["label_1"]).toBe(true);
        expect(activeOutputs.count()).toBe(3);
        expect(activeOutputs.entries["output_0"].label).toBe("label_0");
        expect(activeOutputs.entries["output_1"].label).toBe(null);
        expect(activeOutputs.entries["output_2"].label).toBe("label_1");

        // Test adding additional node
        const activeOutputs_1 = new ActiveOutputs();
        const outputs_1 = [{ name: "output_0" }, { name: "output_1" }, { name: "output_2" }];
        const incoming_1 = [
            { output_name: "output_0", label: "label_0" },
            { output_name: "output_1", label: "label_0" },
            { output_name: "output_2", label: "label_2" },
        ];
        activeOutputs_1.initialize(outputs_1, incoming_1);
        expect(Object.keys(allLabels).length).toBe(3);
        expect(allLabels["label_0"]).toBe(true);
        expect(allLabels["label_1"]).toBe(true);
        expect(allLabels["label_2"]).toBe(true);
        expect(activeOutputs_1.count()).toBe(3);
        expect(activeOutputs_1.entries["output_0"].label).toBe(null);
        expect(activeOutputs_1.entries["output_1"].label).toBe(null);
        expect(activeOutputs_1.entries["output_2"].label).toBe("label_2");

        // Test toggle / removal
        activeOutputs_1.toggle("output_0");
        expect(activeOutputs_1.count()).toBe(2);
        activeOutputs_1.toggle("output_1");
        expect(activeOutputs_1.count()).toBe(1);
        activeOutputs_1.toggle("output_0");
        expect(activeOutputs_1.count()).toBe(2);
        activeOutputs_1.toggle("output_1");
        expect(activeOutputs_1.count()).toBe(3);

        // Test output filtering
        activeOutputs.filterOutputs(["output_0", "output_2"]);
        expect(activeOutputs.count()).toBe(2);
        expect(activeOutputs.entries["output_0"].label).toBe("label_0");
        expect(activeOutputs.entries["output_1"]).toBe(undefined);
        expect(activeOutputs.entries["output_2"].label).toBe("label_1");

        // Update output label
        const response = activeOutputs.labelOutput("output_0", "label_3");
        expect(response).toBe(true);
        expect(activeOutputs.entries["output_0"].label).toBe("label_3");
        const response_1 = activeOutputs.labelOutput("output_0", "label_1");
        expect(response_1).toBe(false);
        expect(activeOutputs.entries["output_0"].label).toBe("label_3");

        // Test output removal
        activeOutputs.filterOutputs([]);
        expect(Object.keys(allLabels).length).toBe(1);
    });
});
