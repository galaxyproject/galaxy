## What Galaxy Learns from Column Headers

Galaxy automatically recognizes column headers in your workbook and uses them to set up your datasets. The header recognition is **flexible and case-insensitive** - you can use various names for the same thing.

This might seem overwhelming but for datasets only a URI/URL is really essential for uploading workbooks to Galaxy. For uploading collections,
the collection element identifiers describing the collection structure is also required - but everything else remains optional. Hopefully the
examples ahead make this clear - but this section exists as reference documentation for what is available and how it works.

### How Header Parsing Works

All of these headers mean the same thing to Galaxy:
- "MD5 Sum", "MD5", "md5", "Hash MD5", "md5sum" → all recognized as MD5 checksum
- "Genome Build", "DBKey", "genome", "build" → all recognized as genome reference
- "URI", "URL", "uri 1 (forward)" → all recognized as data source URL

Galaxy does this by ignoring differences in capitalization, whitespace, special characters like `( ) - _`, and the word "optional" when reading your column headers.

### Recognized Column Headers

| What It's For | Example Headers | Description |
|----------------|-----------------|-------------|
| **URL/URI** | `URI`, `URL`, `uri`, `URI 1 (Forward)`, `URI 2 (Reverse)` | Where to download your data from |
| **Deferred URL** | `URL Deferred`, `Deferred URL` | URL that won't download until the data is actually used |
| **Name** | `Name`, `name`, `NAME` | Dataset name shown in your history |
| **Collection Name** | `Collection Name`, `List Name`, `listname` | Groups multiple datasets into a named collection |
| **Genome/DBKey** | `Genome`, `DBKey`, `build`, `Genome Build` | Reference genome (e.g., hg19, mm10) |
| **File Type** | `File Type`, `Type`, `Extension`, `file extension` | Data format (e.g., fastqsanger, bam, vcf) |
| **Info** | `Info`, `info` | Descriptive text shown in history panel |
| **Tag** | `Tag`, `tag` | Tags for organizing your data |
| **Group Tag** | `Group Tag`, `grouptag` | Tags that carry over to outputs (useful for experiments) |
| **Name Tag** | `Name Tag`, `nametag` | Hash tags based on dataset name |
| **List Identifier** | `List Identifier`, `listidentifier` | Sample or replicate name for collections |
| **Paired Identifier** | `Paired Identifier`, `pairedidentifier` | Which read in a pair (forward/reverse: 1/2, F/R) |
| **MD5 Hash** | `MD5`, `MD5 Sum`, `Hash MD5`, `md5sum` | MD5 checksum to verify file wasn't corrupted |
| **SHA-1 Hash** | `SHA1`, `SHA-1 Sum`, `Hash SHA-1`, `sha1sum` | SHA-1 checksum to verify file wasn't corrupted |
| **SHA-256 Hash** | `SHA256`, `SHA-256 Sum`, `Hash SHA-256` | SHA-256 checksum to verify file wasn't corrupted |
| **SHA-512 Hash** | `SHA512`, `SHA-512 Sum`, `Hash SHA-512` | SHA-512 checksum to verify file wasn't corrupted |

## Example Workbook

Here's a sample workbook showing flexible header naming:

| URI | Name | MD5 Sum | Genome Build | File Type |
|-----|------|---------|--------------|-----------|
| http://example.com/sample1.fq.gz | Sample A | 5d41402abc4b2a76b9719d911017c592 | hg19 | fastqsanger.gz |
| http://example.com/sample2.fq.gz | Sample B | 7d793037a0760186574b0282f2f435e7 | hg19 | fastqsanger.gz |

This could equivalently be written as:

| url | NAME | hash md5 | dbkey | extension |
|-----|------|----------|-------|-----------|
| http://example.com/sample1.fq.gz | Sample A | 5d41402abc4b2a76b9719d911017c592 | hg19 | fastqsanger.gz |
| http://example.com/sample2.fq.gz | Sample B | 7d793037a0760186574b0282f2f435e7 | hg19 | fastqsanger.gz |

Both versions are recognized identically by Galaxy.

### Unrecognized Columns

Columns that Galaxy doesn't recognize are simply ignored - they won't cause errors, but their data won't be used.
