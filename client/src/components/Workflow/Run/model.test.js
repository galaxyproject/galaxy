import { getReplacements } from "./model";

describe("test basic parameter replacement", () => {
    it("should replace", async () => {
        const step_1 = {
            inputs: [
                { name: "input_1", value: "${wp_1}", wp_linked: true },
                { name: "input_2", value: "input_2", step_linked: [{ index: 0, step_type: "data" }] },
            ],
        };
        const stepData = [{ input: { values: ["input_new_data"] } }];
        const wpData = { wp_1: "input_new_wp" };
        const result = getReplacements(step_1.inputs, stepData, wpData);
        expect(result.input_1).toEqual("input_new_wp");
        expect(result.input_2.values[0]).toEqual("input_new_data");
    });
});
