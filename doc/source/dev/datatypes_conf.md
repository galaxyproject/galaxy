# The Datatypes Configuration File (`datatypes_conf.xml`)

Galaxy's datatype system is driven by an XML configuration file, typically named
`datatypes_conf.xml`. A fully-annotated sample is shipped with Galaxy at
`lib/galaxy/config/sample/datatypes_conf.xml.sample`. This page describes the
format of that file and the meaning of every element and attribute.

## Overview

The file is a standard XML document with a single root element, `<datatypes>`,
containing two child sections:

```xml
<?xml version="1.0"?>
<datatypes>
  <registration converters_path="lib/galaxy/datatypes/converters"
                display_path="display_applications">
    <!-- one <datatype> element per format -->
  </registration>
  <sniffers>
    <!-- one <sniffer> element per auto-detectable format -->
  </sniffers>
</datatypes>
```

`<registration>`
: Declares every file format Galaxy knows about, and controls how those formats
  are converted and displayed.

`<sniffers>`
: Lists Python classes that Galaxy uses to auto-detect a file's format by
  inspecting its content when no explicit type has been set.

## The `<registration>` element

### Attributes

`converters_path`
: Filesystem path (relative to the Galaxy root) where converter tool XML files
  are found. Default: `lib/galaxy/datatypes/converters`.

`display_path`
: Filesystem path (relative to the `lib/galaxy/datatypes` directory) where external display application configuration files are found.

## `<datatype>` elements

Each `<datatype>` element registers one file format. The only hard requirements
are `extension` and `type`; all other attributes are optional.

```xml
<datatype extension="fastqsanger"
          auto_compressed_types="gz,bz2"
          type="galaxy.datatypes.sequence:FastqSanger"
          display_in_upload="true"
          description="Sanger variant of the FASTQ format: phred+33"/>
```

### Attributes

`extension`
: The format identifier used throughout Galaxy (e.g. `bam`, `vcf`,
  `fastqsanger`). This string appears in tool XML `format=` attributes,
  history item badges, and converter target references. Dotted extensions such
  as `fast5.tar.gz` or `ome.tiff` are used when a format is a compound type or
  to avoid colliding with simpler names.

`type`
: The Python class that implements this datatype, expressed as
  `module.path:ClassName` (e.g. `galaxy.datatypes.binary:Bam`). Galaxy imports
  this class at startup to obtain sniffers, metadata definitions, display
  logic, and so on.

`subclass`
: When `true`, this entry reuses the referenced `type` class directly instead
  of expecting a distinct subclass. Use this for aliases and minor variants
  that share all logic with their parent but need a separate identity (separate
  history item type, separate converter list, etc.).

  ```xml
  <!-- bcf_bgzip is an alias for bcf kept for backward compatibility -->
  <datatype extension="bcf_bgzip" type="galaxy.datatypes.binary:Bcf" subclass="true"/>
  ```

`mimetype`
: MIME type used when Galaxy serves the file over HTTP (e.g.
  `application/octet-stream`, `text/plain`, `image/png`). When omitted,
  Galaxy falls back to a sensible default for the base class.

`display_in_upload`
: When `true` (the default is `false`), the format appears in the upload
  dialog's *File Format* dropdown so users can select it explicitly. Set to
  `false` for index files, intermediate formats, or anything Galaxy generates
  automatically (e.g. `.bai` BAM indices).

`description`
: A human-readable description of the format shown in the UI.

`description_url`
: A URL pointing to external documentation for the format.

`auto_compressed_types`
: Comma-separated list of compression extensions (e.g. `gz,bz2`) that Galaxy
  will handle transparently for this type. A user uploading a `fastqsanger.gz`
  file will have it automatically associated with the `fastqsanger` datatype
  without needing to select it explicitly.

`max_optional_metadata_filesize`
: Maximum file size in bytes for which Galaxy will compute *optional* (i.e.
  expensive) metadata. Files larger than this threshold will have their
  optional metadata skipped to avoid long delays during upload.

## Child elements of `<datatype>`

### `<infer_from>`

Tells Galaxy to assign this datatype automatically when an uploaded or produced
file carries the given filename suffix. A single `<datatype>` can have multiple
`<infer_from>` entries.

```xml
<datatype extension="tiff" type="galaxy.datatypes.images:Tiff" ...>
  <infer_from suffix="tiff" />
  <infer_from suffix="tif" />
</datatype>
```

`suffix`
: The filename extension to match (without the leading dot).

### `<converter>`

Registers a tool that converts this format into another, making a *Convert*
action available in the history item menu.

```xml
<datatype extension="bam" ...>
  <converter file="bam_to_bai.xml" target_datatype="bai"/>
  <converter file="bam_to_bigwig_converter.xml" target_datatype="bigwig"/>
  <converter file="to_qname_sorted_bam.xml" target_datatype="qname_sorted.bam"/>
</datatype>
```

`file`
: Filename of the converter tool XML, resolved relative to `converters_path`.

`target_datatype`
: The `extension` of the output format produced by the converter.

`depends_on`
: Optional. The `target_datatype` of another converter that must run first.
  Used to express chained conversions:

  ```xml
  <converter file="interval_to_bgzip_converter.xml" target_datatype="bgzip"/>
  <converter file="interval_to_tabix_converter.xml" target_datatype="tabix"
             depends_on="bgzip"/>
  ```

### `<display>`

Links this datatype to an external display application (genome browser,
specialized viewer, etc.).

```xml
<datatype extension="bam" ...>
  <display file="ucsc/bam.xml"/>
  <display file="igv/bam.xml"/>
  <display file="ensembl/ensembl_bam.xml" inherit="true"/>
</datatype>
```

`file`
: Path to the display application XML file, relative to `display_path`.

`inherit`
: When `true`, subtypes of this datatype automatically inherit the display
  link without having to redeclare it.

### `<visualization>`

Links the datatype to a built-in Galaxy visualization plugin, enabling a
*Visualize* button on the history item.

```xml
<datatype extension="h5" ...>
  <visualization plugin="h5web" />
</datatype>
```

`plugin`
: The identifier of the visualization plugin (must match a plugin registered
  in Galaxy's visualization framework).

### `<upload_warning>`

Displays a warning message in the upload dialog when the user selects this
format. Useful for deprecated or rarely-appropriate types.

```xml
<datatype extension="fastq" ...>
  <upload_warning>
    Generally a more specific fastq datatype should be specified; please
    consider selecting fastqsanger instead.
  </upload_warning>
</datatype>
```

## The `<sniffers>` element

The `<sniffers>` section lists Python classes that Galaxy tries in order to
auto-detect a dataset's type. Each entry is a single `<sniffer>` element:

```xml
<sniffers>
  <sniffer type="galaxy.datatypes.sequence:Fasta"/>
  <sniffer type="galaxy.datatypes.sequence:Fastq"/>
  <!-- ... -->
</sniffers>
```

`type`
: The fully-qualified Python class to use as a sniffer, in the same
  `module.path:ClassName` format as `<datatype type="...">`. The class must
  implement the `sniff` method from `galaxy.datatypes.data:Data`.

## Conventions and tips

- **Dotted extensions** (`fast5.tar.gz`, `ome.tiff`, `qname_sorted.bam`)
  disambiguate compound or variant formats from their simpler base types.
- **`display_in_upload="false"`** is the right choice for index files and
  tool-generated intermediates that users would never upload directly (e.g.
  `.bai`, `tabix`).
- **XML comments** (`<!-- ... -->`) are used heavily in the sample file to
  group datatypes by domain (Proteomics, FlowCytometry, RGenetics, etc.) and
  to explain disabled or deprecated entries. Adopt the same style for new
  additions.
- **Subclassing vs. a full class**: if your new format needs no Python-level
  customisation beyond what an existing class already provides, set
  `subclass="true"` rather than writing a new class. Only create a new Python
  class when you need custom sniffing, metadata, or display logic.
- **Converter chaining**: when a conversion requires an intermediate step (e.g.
  bgzip before tabix), declare each converter separately and use `depends_on`
  to express the dependency order.

## See also

- [Data types](data_types.md) — developer guide to implementing new datatype classes in Python.
- `lib/galaxy/datatypes/` — source directory containing the Python implementations
  of all built-in datatypes.
- `lib/galaxy/datatypes/converters/` — source directory for converter tool XML files.
- `display_applications/` — source directory for display-application XML files.
