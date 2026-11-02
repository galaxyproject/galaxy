import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TrsUrlImport from "./TrsUrlImport.vue";

const TRS_URL = "https://training.galaxyproject.org/training-material/api/ga4gh/trs/v2/tools/t-x/versions/wf";

describe("TrsUrlImport", () => {
    it("imports a TRS URL given in the query, as GTN launch links send it", () => {
        const wrapper = mount(TrsUrlImport as object, { global: getLocalVue(), props: { queryTrsUrl: TRS_URL } });
        expect(wrapper.emitted("onImport")).toEqual([[TRS_URL]]);
    });

    it("waits for the user without a query URL", () => {
        const wrapper = mount(TrsUrlImport as object, { global: getLocalVue() });
        expect(wrapper.emitted("onImport")).toBeUndefined();
    });
});
