import Ui from "mvc/ui/ui-misc";

import ParameterFactory from "./parameters";

jest.mock("app");
jest.mock("mvc/ui/ui-misc", () => ({
    TextSelect: jest.fn(() => {
        return {
            value: jest.fn(),
        };
    }),
    Input: jest.fn(() => {
        return {
            value: jest.fn(),
        };
    }),
}));

describe("ParameterFactory", () => {
    it("should create a TEXT parameter input when no type is specified", async () => {
        const input = {
            id: "type-less parameter",
            type: "",
            value: "initial_value",
        };
        const parameter = new ParameterFactory();
        parameter.create(input);
        expect(Ui.Input).toHaveBeenCalled();
        expect(Ui.TextSelect).not.toHaveBeenCalled();
    });
});
