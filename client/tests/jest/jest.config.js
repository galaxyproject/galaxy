const path = require("path");
const { defaults: tsjPreset } = require("ts-jest/presets");

// For a detailed explanation regarding each configuration property, visit:
// https://jestjs.io/docs/en/configuration.html

const modulesToTransform = [
    "bootstrap-vue",
    "rxjs",
    "@hirez_io",
    "winbox",
    "pretty-bytes",
    "@fortawesome",
    "openapi-typescript-fetch",
].join("|");

module.exports = {
    preset: "ts-jest",
    clearMocks: true,
    coverageDirectory: "coverage",
    globals: { __webpack_public_path__: "" },
    moduleFileExtensions: ["js", "ts", "json", "vue", "yml", "txt"],
    modulePaths: ["<rootDir>/src/", "<rootDir>/tests/", "<rootDir>/node_modules/", "./"],
    moduleNameMapper: {
        "^d3(.*)$": "<rootDir>/node_modules/d3$1/dist/d3$1.min.js",
        "\\.(css|scss)$": "<rootDir>/tests/jest/__mocks__/style.js",
        "^@fontsource/.*": "<rootDir>/tests/jest/__mocks__/font.js",
        "^config$": "<rootDir>/tests/jest/__mocks__/config.js",
        handsontable: "node_modules/handsontable/dist/handsontable.js",
        "utils/localization$": "<rootDir>/tests/jest/__mocks__/localization.js",
        "viz/trackster$": "<rootDir>/tests/jest/__mocks__/trackster.js",
        "rxjs/internal/scheduler/AsyncScheduler":
            "<rootDir>/node_modules/rxjs/dist/esm/internal/scheduler/AsyncScheduler.js",
        "^@/(.*)$": "<rootDir>/src/$1",
        "^@tests/(.*)$": "<rootDir>/tests/$1",
    },
    modulePathIgnorePatterns: ["<rootDir>/src/.*/__mocks__"],
    rootDir: path.join(__dirname, "../../"),
    roots: ["<rootDir>/src/", "<rootDir>/tests/jest/standalone/"],
    setupFilesAfterEnv: ["<rootDir>/tests/jest/jest.setup.js"],
    testEnvironment: "jsdom",
    testPathIgnorePatterns: ["/node_modules/", "/dist/"],
    transform: {
        "^.+\\.js$": "babel-jest",
        "^.*\\.(vue)$": "@vue/vue2-jest",
        "^.+\\.ya?ml$": "<rootDir>/tests/jest/yaml-jest.js",
        "^.+\\.txt$": "<rootDir>/tests/jest/jest-raw-loader.js",
        ...tsjPreset.transform,
    },
    transformIgnorePatterns: [`/node_modules/(?!${modulesToTransform})`],
};
