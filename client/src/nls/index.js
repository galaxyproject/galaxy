/** 
 * ES module locale aggregator
 * This replaces the RequireJS i18n plugin functionality
 * Loads all languages and returns them in the expected format
 */

// Import root strings and supported languages
import { root, supportedLanguages } from './locale.js';

// Import all language files
import frLocale from './fr/locale.js';
import esLocale from './es/locale.js';
import jaLocale from './ja/locale.js';
import zhLocale from './zh/locale.js';
import deLocale from './de/locale.js';

// Build the locale strings object with the same structure 
// that the i18n loader would have created
const localeStrings = {
    __root: root,
    __fr: frLocale,
    __es: esLocale,
    __ja: jaLocale,
    __zh: zhLocale,
    __de: deLocale,
    // Add language codes without underscores for compatibility
    fr: frLocale,
    es: esLocale,
    ja: jaLocale,
    zh: zhLocale,
    de: deLocale
};

// Export with the same structure that the i18n loader would have created
export default localeStrings;