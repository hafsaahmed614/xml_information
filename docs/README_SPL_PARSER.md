# FDA DailyMed SPL XML Parser

A comprehensive Python parser for FDA Structured Product Labeling (SPL) XML files that outputs normalized JSON suitable for integration into a master drug knowledge graph.

## Features

- **Full SPL Support**: Handles Prescription, OTC, Homeopathic, and Other SPL document types
- **Comprehensive Extraction**: Extracts all identifiers (NDC, UNII, SetID, ANDA/NDA/BLA), products, ingredients, sections
- **Knowledge Graph Ready**: Outputs both normalized JSON and entity/edge KG format
- **Robust**: Handles missing fields, edge cases, and varied document structures
- **Well-Tested**: 44 unit tests covering all major functionality

## Installation

No external dependencies required. Uses Python 3.7+ standard library only.

```bash
# Clone the repository
git clone <repository-url>
cd xml_information

# Run tests
python3 -m unittest test_spl_parser -v
```

## Usage

### Command Line

```bash
# Parse a single file
python3 spl_parser.py -i sample.xml -o output.json

# Parse a directory of XML files
python3 spl_parser.py -d xml_sample/ -o parsed_output/

# Parse with Knowledge Graph output
python3 spl_parser.py -d xml_sample/ -o parsed_output/ --kg

# Output as JSON Lines
python3 spl_parser.py -d xml_sample/ --jsonl output.jsonl

# Pretty print output
python3 spl_parser.py -d xml_sample/ -o parsed_output/ --pretty
```

### Python API

```python
from spl_parser import SPLParser

# Initialize parser
parser = SPLParser()

# Parse single file
doc = parser.parse_file('sample.xml')
print(doc.to_dict())

# Parse directory
documents = parser.parse_directory('xml_sample/')

# Generate knowledge graph
kg = parser.to_knowledge_graph(doc)
print(kg.to_dict())
```

## Output Schema

### Main JSON Schema

```json
{
  "source": {
    "dataset": "DailyMed",
    "format": "SPL",
    "input_filename": "...",
    "parsed_at": "ISO-8601 timestamp",
    "parser_version": "1.0.0"
  },
  "spl": {
    "document_id": { "root": "...", "extension": null },
    "set_id": { "root": "..." },
    "version_number": 1,
    "effective_time": "YYYYMMDD",
    "title": "...",
    "document_type": "prescription|otc|homeopathic|other|unknown"
  },
  "labeler": {
    "name": "...",
    "org_ids": [
      { "root": "...", "extension": "...", "type_hint": "DUNS" }
    ]
  },
  "products": [
    {
      "product_name": "...",
      "generic_name": "...",
      "routes": ["ORAL"],
      "dosage_forms": ["TABLET"],
      "ndc": {
        "product_ndcs": ["XXXXX-XXXX"],
        "package_ndcs": ["XXXXX-XXXX-XX"]
      },
      "regulatory": {
        "rx_otc_flag": "RX|OTC|UNKNOWN",
        "application_number": "NDA...|ANDA...|null",
        "otc_monograph_id": "M###|null",
        "marketing_category": "...",
        "dea_schedule": "CII|CIII|...|null"
      },
      "ingredients": [
        {
          "name": "...",
          "role": "active|inactive|other",
          "unii": "...",
          "strength": {
            "numerator_value": 500.0,
            "numerator_unit": "mg",
            "denominator_value": 1.0,
            "denominator_unit": "1"
          },
          "homeopathic": {
            "potency": "6C|30X|etc|null",
            "source_material": "...|null"
          }
        }
      ],
      "packages": [...],
      "physical_characteristics": {
        "color": "...",
        "shape": "...",
        "size": "...",
        "imprint": "...",
        "flavor": "..."
      }
    }
  ],
  "sections": [
    {
      "code_system": "2.16.840.1.113883.6.1",
      "code": "34067-9",
      "display": "INDICATIONS & USAGE SECTION",
      "title": "1 INDICATIONS AND USAGE",
      "text_xhtml": "<raw xhtml string>",
      "text_plain": "plain text with normalized whitespace"
    }
  ],
  "derived": {
    "merge_keys": {
      "primary": ["set_id:...", "ndc:..."],
      "secondary": ["doc_id:...", "unii:..."]
    },
    "section_presence_flags": {
      "boxed_warning": true/false,
      "indications_and_usage": true/false,
      "contraindications": true/false,
      "warnings_and_precautions": true/false,
      "storage_and_handling": true/false,
      "dosage_and_administration": true/false,
      "adverse_reactions": true/false,
      "drug_interactions": true/false
    }
  }
}
```

### Knowledge Graph Schema

```json
{
  "entities": [
    {
      "entity_type": "organization|label_version|product|package|ingredient|section",
      "entity_id": "type:identifier",
      "properties": { ... }
    }
  ],
  "edges": [
    {
      "edge_type": "HAS_LABEL_VERSION|HAS_PRODUCT|HAS_PACKAGE|HAS_INGREDIENT|HAS_SECTION|LABELED_BY",
      "source_id": "...",
      "target_id": "...",
      "properties": { ... }
    }
  ]
}
```

## Key Identifiers for Knowledge Graph Merging

| Identifier | Code System | Description |
|------------|-------------|-------------|
| **NDC** | `2.16.840.1.113883.6.69` | National Drug Code (product & package level) |
| **UNII** | `2.16.840.1.113883.4.9` | Unique Ingredient Identifier |
| **SetID** | Document element | Stable identifier across label versions |
| **ANDA/NDA/BLA** | `2.16.840.1.113883.3.150` | FDA application numbers |
| **DUNS** | `1.3.6.1.4.1.519.1` | Organization identifier |

## Section Codes (LOINC)

| Code | Section Type |
|------|--------------|
| `34066-1` | Boxed Warning |
| `34067-9` | Indications & Usage |
| `34068-7` | Dosage & Administration |
| `34070-3` | Contraindications |
| `34071-1` | Warnings |
| `43685-7` | Warnings and Precautions |
| `34084-4` | Adverse Reactions |
| `34073-7` | Drug Interactions |
| `44425-7` | Storage and Handling |
| `34089-3` | Description |
| `34090-1` | Clinical Pharmacology |

See `spl_parser.py` for the complete list of 60+ known LOINC section codes.

## Extraction Rules

### Identifiers
- **Document ID**: Extracted from `/document/id/@root`
- **Set ID**: Extracted from `/document/setId/@root` (stable across versions)
- **NDC**: Separated into product-level (10-digit) and package-level (11-digit)
- **UNII**: Extracted from ingredient code with codeSystem `2.16.840.1.113883.4.9`

### Products
- Extracts all `manufacturedProduct` elements
- Parses active/inactive ingredients with strength
- Captures physical characteristics (color, shape, size, imprint)
- Handles homeopathic potencies (6C, 30X, etc.)

### Sections
- Preserves raw XHTML in `text_xhtml` for fidelity
- Normalizes whitespace in `text_plain` for text processing
- Detects section presence by LOINC code and title matching

## Limitations & Assumptions

1. **Namespace**: Assumes HL7 v3 namespace `urn:hl7-org:v3`
2. **NDC Format**: Expects standard NDC format (XXXXX-XXXX or XXXXX-XXXX-XX)
3. **Document Type Detection**: Falls back to filename prefix if code-based detection fails
4. **Multiple Products**: Supports multiple products per file
5. **Empty Fields**: Outputs null/empty arrays for missing data (never crashes)

## Testing

```bash
# Run all tests
python3 -m unittest test_spl_parser -v

# Run specific test class
python3 -m unittest test_spl_parser.TestProductExtraction -v

# Run with coverage (if coverage.py installed)
coverage run -m unittest test_spl_parser
coverage report
```

## Output Files

When processing a directory, the parser generates:

- `{filename}.json` - Individual parsed JSON for each XML file
- `{filename}_kg.json` - Knowledge graph format (with --kg flag)
- `all_drugs_combined.json` - Combined array of all parsed documents
- `all_drugs_kg.json` - Combined knowledge graph (with --kg flag)

## Version History

- **1.0.0**: Initial release with full SPL parsing, KG output, and unit tests

## License

MIT License
