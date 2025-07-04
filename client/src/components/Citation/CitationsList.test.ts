import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import CitationItem from "./CitationItem.vue";
import MountTarget from "./CitationsList.vue";

const localVue = getLocalVue(true);

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {
            value: {
                citation_bibtex:
                    "@article{Galaxy2024, title={The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update}, author={{The Galaxy Community}}, journal={Nucleic Acids Research}, year={2024}, doi={10.1093/nar/gkae410}, url={https://doi.org/10.1093/nar/gkae410}}",
            },
        },
    })),
}));

jest.mock("@/components/Citation/services", () => ({
    getCitations: jest.fn(() =>
        Promise.resolve([
            {
                raw: "@article{Hourahine_2020,\n\tdoi = {10.1063/1.5143190},\n\turl = {https://doi.org/10.1063%2F1.5143190},\n\tyear = 2020,\n\tmonth = {mar},\n\tpublisher = {{AIP} Publishing},\n\tvolume = {152},\n\tnumber = {12},\n\tpages = {124101},\n\tauthor = {B. Hourahine and B. Aradi and V. Blum and F. Bonaf{\\'{e}} and A. Buccheri and C. Camacho and C. Cevallos and M. Y. Deshaye and T. Dumitric{\\u{a}} and A. Dominguez and S. Ehlert and M. Elstner and T. van der Heide and J. Hermann and S. Irle and J. J. Kranz and C. K\u00f6hler and T. Kowalczyk and T. Kuba{\\v{r}} and I. S. Lee and V. Lutsker and R. J. Maurer and S. K. Min and I. Mitchell and C. Negre and T. A. Niehaus and A. M. N. Niklasson and A. J. Page and A. Pecchia and G. Penazzi and M. P. Persson and J. {\\v{R}}ez{\\'{a}}{\\v{c}} and C. G. S{\\'{a}}nchez and M. Sternberg and M. St\u00f6hr and F. Stuckenberg and A. Tkatchenko and V. W.-z. Yu and T. Frauenheim},\n\ttitle = {{DFTB}$\\mathplus$, a software package for efficient approximate density functional theory based atomistic simulations},\n\tjournal = {The Journal of Chemical Physics}\n}",
                cite: {
                    format: jest.fn(
                        () =>
                            '<div class="csl-bib-body"><div data-csl-entry-id="Hourahine_2020" class="csl-entry">Hourahine, B. (2020). DFTB$\\mathplus$, a software package for efficient approximate density functional theory based atomistic simulations. The Journal of Chemical Physics, 152(12), 124101. https://doi.org/10.1063/1.5143190</div></div>'
                    ),
                },
            },
        ])
    ),
}));

describe("CitationsList", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        wrapper = mount(MountTarget as object, {
            propsData: {
                id: "test-id",
                source: "histories",
            },
            localVue,
        });

        await flushPromises();
    });

    it("renders the config Galaxy citation and any fetched citations", () => {
        const citationItems = wrapper.findAllComponents(CitationItem);

        // It finds the Galaxy citation from the config, and the mocked citation for the history tools.
        expect(citationItems.length).toBe(2);

        expect(citationItems.at(0).text()).toContain(
            "The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update"
        );
        expect(citationItems.at(1).text()).toContain(
            "DFTB$\\mathplus$, a software package for efficient approximate density functional theory based atomistic simulations"
        );
    });
});
