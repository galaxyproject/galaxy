# OCR datatype fixtures

These files exercise direct sniffing and detection through the sample datatype
registry in `test/unit/data/datatypes/test_ocr.py`. They can also be uploaded to
Galaxy with the datatype set to Auto-detect. No accompanying page image is
needed for datatype detection. Tests use the checked-in files without network access.

| File | Expected datatype | Origin |
| --- | --- | --- |
| `ocr_sample.page.xml` | `page.xml` | Hand-authored PAGE 2019 example with metadata, reading order, a region, a baseline, words, and recognized text. |
| `ocr_sample.alto` | `alto` | Hand-authored ALTO v4 example with image metadata, page layout, a text block, a line, words, spacing, and confidence scores. |
| `ocr_sample.hocr` | `hocr` | Unmodified hocr-tools Tesseract 3.03 output for an Alice in Wonderland page; XHTML doctype, OCR metadata, layout, words, and confidence scores. |
| `ocr_sample.abbyy.xml` | `abbyy.xml` | Unmodified Calamari OCR test page from Hiltl's Die Bank des Verderbens; FineReader v10 namespace, layout, formatting, and character confidence scores. Includes the original UTF-8 BOM and CRLF line endings. |

External samples were downloaded on 2026-10-03:

- hOCR: https://raw.githubusercontent.com/ocropus/hocr-tools/master/test/testdata/tess.hocr
- ABBYY: https://raw.githubusercontent.com/Calamari-OCR/calamari/master/calamari_ocr/test/data/hiltl_die_bank_des_verderbens_abbyyxml/bsb11015645_00020.abbyy.xml

The inline examples in the test module retain coverage for malformed input,
namespace variants, and false positives. The PAGE and ALTO fixtures are synthetic
examples, not output captured from an OCR engine.
