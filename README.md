# Example Library README

This is a demonstration README for testing Galaxy data library markdown rendering.

## Features

This library contains datasets for the **genome analysis project**. The following resources are available:

### Available Datasets

1. Reference genomes (FASTA format)
2. Annotation files (GFF3/GTF)
3. RNA-seq data (FASTQ)
4. Analysis results (BAM, VCF)

### Usage Guidelines

To use these datasets in your analysis:

- Select the appropriate reference genome from the "References" folder
- Ensure your tools are compatible with the file formats
- Check the metadata for version information

### Quick Links

- [Galaxy Documentation](https://galaxyproject.org)
- [Training Materials](https://training.galaxyproject.org)

### Code Example

Here's how to reference these datasets in a workflow:

```yaml
inputs:
  reference:
    type: data
    format: fasta
  reads:
    type: data
    format: fastq
```

### Important Notes

> **Note:** All datasets in this library are read-only. To modify data, copy it to your history first.

> **Warning:** Large datasets may take time to import into your history.

### Contact

For questions about this library, contact the data librarian or submit a support request.

---

*Last updated: 2025*
