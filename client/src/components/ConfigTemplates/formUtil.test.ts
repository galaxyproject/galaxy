import { type TemplateVariable } from "@/api/configTemplates";

import { createTemplateForm, templateVariableFormEntry, upgradeForm } from "./formUtil";
import {
    GENERIC_FTP_FILE_SOURCE_TEMPLATE,
    OBJECT_STORE_INSTANCE,
    STANDARD_FILE_SOURCE_TEMPLATE,
    STANDARD_OBJECT_STORE_TEMPLATE,
} from "./test_fixtures";

const FTP_VARIABLES = GENERIC_FTP_FILE_SOURCE_TEMPLATE.variables as TemplateVariable[];
const PROJECT_VARIABLE = {
    name: "Project",
    type: "path_component",
} as TemplateVariable;

describe("formUtils", () => {
    describe("createTemplateForm", () => {
        it("should create a form from an object store templates", () => {
            const form = createTemplateForm(STANDARD_OBJECT_STORE_TEMPLATE, "storage location");
            expect(form.length).toBe(6);
            const formEl0 = form[0];
            expect(formEl0?.name).toEqual("_meta_name");
            expect(formEl0?.help).toEqual("Label this new storage location with a name.");
            const formEl1 = form[1];
            expect(formEl1?.name).toEqual("_meta_description");
        });

        it("should create a form from a file source templates", () => {
            const form = createTemplateForm(STANDARD_FILE_SOURCE_TEMPLATE, "file source");
            expect(form.length).toBe(6);
            const formEl0 = form[0];
            expect(formEl0?.name).toEqual("_meta_name");
            expect(formEl0?.help).toEqual("Label this new file source with a name.");
            const formEl1 = form[1];
            expect(formEl1?.name).toEqual("_meta_description");
        });
    });

    describe("upgradeForm", () => {
        it("should create a form from an object store templates", () => {
            const form = upgradeForm(STANDARD_OBJECT_STORE_TEMPLATE, OBJECT_STORE_INSTANCE);
            expect(form.length).toBe(3);
            const formEl0 = form[0];
            expect(formEl0?.name).toEqual("oldvar");
            const formEl1 = form[1];
            expect(formEl1?.name).toEqual("newvar");
        });

        it("should only ask for new secrets during upgrade", () => {
            const form = upgradeForm(STANDARD_OBJECT_STORE_TEMPLATE, OBJECT_STORE_INSTANCE);
            expect(form.length).toBe(3);
            const formEl0 = form[2];
            expect(formEl0?.name).toEqual("newsecret");
            expect(formEl0?.type).toEqual("password");
        });
    });

    describe("templateVariableFormEntry", () => {
        it("should render string types as Galaxy text form inputs", () => {
            const hostVariable = FTP_VARIABLES[0] as TemplateVariable;
            const formEntry = templateVariableFormEntry(hostVariable, undefined);
            expect(formEntry.name).toBe("host");
            expect(formEntry.label).toBe("FTP Host");
            expect(formEntry.type).toBe("text");
            expect(formEntry.help).toBe("<p>Host of FTP Server to connect to.</p>\n");
        });
        it("should render integer types as Galaxy integer inputs", () => {
            const portVariable = FTP_VARIABLES[3] as TemplateVariable;
            const formEntry = templateVariableFormEntry(portVariable, undefined);
            expect(formEntry.name).toBe("port");
            expect(formEntry.label).toBe("FTP Port");
            expect(formEntry.type).toBe("integer");
            expect(formEntry.value).toBe(21);
        });
        it("should render boolean types as Galaxy boolean inputs", () => {
            const writableVariable = FTP_VARIABLES[2] as TemplateVariable;
            const formEntry = templateVariableFormEntry(writableVariable, undefined);
            expect(formEntry.name).toBe("writable");
            expect(formEntry.label).toBe("Writable?");
            expect(formEntry.type).toBe("boolean");
            expect(formEntry.value).toBe(false);
        });
        it("should render path_component types as Galaxy text form inputs", () => {
            const formEntry = templateVariableFormEntry(PROJECT_VARIABLE, undefined);
            expect(formEntry.name).toBe("Project");
            expect(formEntry.label).toBe("Project");
            expect(formEntry.type).toBe("text");
        });
        it("should render path_component updated default values if supplied", () => {
            const formEntry = templateVariableFormEntry(PROJECT_VARIABLE, "foobar");
            expect(formEntry.value).toBe("foobar");
        });
        it("should render string types with updated default values if supplied", () => {
            const hostVariable = FTP_VARIABLES[0] as TemplateVariable;
            const formEntry = templateVariableFormEntry(hostVariable, "mycoolhost.org");
            expect(formEntry.value).toBe("mycoolhost.org");
        });
    });
});
