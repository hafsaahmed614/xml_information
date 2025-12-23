# FDA SPL XML Content Analysis for Drug Knowledge Graph

## Executive Summary

FDA Structured Product Labeling (SPL) files contain comprehensive drug information using HL7 v3 Clinical Document Architecture (CDA). These files are ideal for building a drug knowledge graph due to their standardized structure, rich identifiers, and extensive clinical content.

---

## 1. KEY IDENTIFIERS FOR KNOWLEDGE GRAPH MERGING

### 1.1 Drug/Product Identifiers

| Identifier | Code System OID | Description | Example | Use Case |
|------------|-----------------|-------------|---------|----------|
| **NDC** | `2.16.840.1.113883.6.69` | National Drug Code (10/11-digit) | `59651-528`, `55910-506-78` | Primary drug product identifier |
| **UNII** | `2.16.840.1.113883.4.9` | Unique Ingredient Identifier | `57Y76R9ATQ` (Naproxen) | Links to FDA substance registry, ingredient matching |
| **SetID** | Document element | Stable identifier across versions | `570974d4-0d5b-4df2-b307-37380511835d` | Track label versions over time |
| **Document ID** | Document element | Unique per SPL version | `1e5c425c-1387-49c4-8200-b36cb8925f9c` | Specific label version reference |

### 1.2 Regulatory/Application Identifiers

| Identifier | Example | Description |
|------------|---------|-------------|
| **ANDA** | `ANDA216504` | Abbreviated New Drug Application (generics) |
| **NDA** | `NDA212045` | New Drug Application |
| **BLA** | `BLA103872` | Biologics License Application |
| **OTC Monograph** | `M013` | OTC drug monograph reference |

### 1.3 Organization Identifiers

| Identifier | Code System | Description |
|------------|-------------|-------------|
| **DUNS Number** | `1.3.6.1.4.1.519.1` | Organization identifier (e.g., `650082092`) |

### 1.4 Section Code Identifiers (LOINC)

All section types use LOINC codes from code system `2.16.840.1.113883.6.1`.

---

## 2. SECTION TYPES RELEVANT TO YOUR QUERY

### YES - These identifiers/sections ARE present:

| Your Field | SPL Section Code | SPL Section Name | Present in Files |
|------------|------------------|------------------|------------------|
| **indications_text** | `34067-9` | INDICATIONS & USAGE SECTION | 16 files |
| **contraindications** | `34070-3` | CONTRAINDICATIONS SECTION | 6 files |
| **boxed_warnings** | `34066-1` | BOXED WARNING SECTION | 5 files |
| **warnings_precautions** | `34071-1` | WARNINGS SECTION | 16 files |
| **warnings_precautions** | `43685-7` | WARNINGS AND PRECAUTIONS SECTION | 3 files |
| **storage_requirements** | `44425-7` | STORAGE AND HANDLING SECTION | 2 files |

### Additional Clinical Sections Available:

| Section Code | Section Name | Count |
|--------------|--------------|-------|
| `34068-7` | DOSAGE & ADMINISTRATION SECTION | 18 |
| `34084-4` | ADVERSE REACTIONS SECTION | 6 |
| `34073-7` | DRUG INTERACTIONS SECTION | 4 |
| `43680-8` | DOSAGE FORMS & STRENGTHS SECTION | 3 |
| `34088-5` | OVERDOSAGE SECTION | 5 |
| `34089-3` | DESCRIPTION SECTION | 6 |
| `34090-1` | CLINICAL PHARMACOLOGY SECTION | 6 |
| `43682-4` | PHARMACOKINETICS SECTION | 3 |
| `43681-6` | PHARMACODYNAMICS SECTION | 3 |
| `42228-7` | PREGNANCY SECTION | 6 |
| `42229-5` | PEDIATRIC USE SECTION | 7 |
| `34074-5` | GERIATRIC USE SECTION | 7 |
| `34092-7` | CARCINOGENESIS & MUTAGENESIS SECTION | 5 |
| `50741-8` | CLINICAL STUDIES SECTION | 2 |
| `34093-5` | REFERENCES SECTION | 1 |
| `51945-4` | PACKAGE LABEL.PRINCIPAL DISPLAY PANEL | 72 |

---

## 3. COMPLETE LOINC SECTION CODE MAPPING

```
DOCUMENT TYPES:
  34390-5 = HUMAN OTC DRUG LABEL
  34391-3 = HUMAN PRESCRIPTION DRUG LABEL
  50577-6 = OTC ANIMAL DRUG LABEL
  81203-2 = BULK INGREDIENT - ANIMAL DRUG

CLINICAL SECTIONS:
  34066-1 = BOXED WARNING SECTION
  34067-9 = INDICATIONS & USAGE SECTION
  34068-7 = DOSAGE & ADMINISTRATION SECTION
  34069-5 = HOW SUPPLIED SECTION
  34070-3 = CONTRAINDICATIONS SECTION
  34071-1 = WARNINGS SECTION
  34072-9 = GENERAL PRECAUTIONS SECTION
  34073-7 = DRUG INTERACTIONS SECTION
  34074-5 = GERIATRIC USE SECTION
  34075-2 = LABORATORY TESTS SECTION
  34076-0 = INFORMATION FOR PATIENTS SECTION
  34079-4 = DRUG & OR LABORATORY TEST INTERACTIONS SECTION
  34080-2 = NURSING MOTHERS SECTION
  34081-0 = PEDIATRIC USE SECTION
  34082-8 = ABUSE SECTION
  34083-6 = DEPENDENCE SECTION
  34084-4 = ADVERSE REACTIONS SECTION
  34085-1 = CONTROLLED SUBSTANCE SECTION
  34086-9 = DRUG ABUSE AND DEPENDENCE SECTION
  34087-7 = MECHANISM OF ACTION SECTION
  34088-5 = OVERDOSAGE SECTION
  34089-3 = DESCRIPTION SECTION
  34090-1 = CLINICAL PHARMACOLOGY SECTION
  34092-7 = CARCINOGENESIS & MUTAGENESIS & IMPAIRMENT OF FERTILITY SECTION
  34093-5 = REFERENCES SECTION

NEWER PLR FORMAT SECTIONS:
  43678-2 = DOSAGE FORMS & STRENGTHS SECTION
  43679-0 = INDICATIONS AND USAGE SECTION
  43680-8 = CONTRAINDICATIONS SECTION
  43681-6 = PHARMACODYNAMICS SECTION
  43682-4 = PHARMACOKINETICS SECTION
  43683-2 = RECENT MAJOR CHANGES SECTION
  43684-0 = USE IN SPECIFIC POPULATIONS SECTION
  43685-7 = WARNINGS AND PRECAUTIONS SECTION
  44425-7 = STORAGE AND HANDLING SECTION

OTC-SPECIFIC SECTIONS:
  55105-1 = OTC - PURPOSE SECTION
  55106-9 = OTC - ACTIVE INGREDIENT SECTION
  50565-1 = OTC - KEEP OUT OF REACH OF CHILDREN SECTION
  50566-9 = OTC - STOP USE SECTION
  50567-7 = OTC - WHEN USING SECTION
  50568-5 = OTC - ASK DOCTOR/PHARMACIST SECTION
  50569-3 = OTC - ASK DOCTOR SECTION
  50570-1 = OTC - DO NOT USE SECTION
  53413-1 = OTC - QUESTIONS SECTION
  53414-9 = OTC - PREGNANCY OR BREAST FEEDING SECTION
  60561-8 = OTHER SAFETY INFORMATION

PRODUCT DATA:
  48780-1 = SPL PRODUCT DATA ELEMENTS SECTION
  51727-6 = INACTIVE INGREDIENT SECTION
  51945-4 = PACKAGE LABEL.PRINCIPAL DISPLAY PANEL

PATIENT MATERIALS:
  58476-3 = SPL PATIENT PACKAGE INSERT SECTION
  59845-8 = INSTRUCTIONS FOR USE SECTION
  68498-5 = PATIENT MEDICATION INFORMATION SECTION
  77290-5 = SPL MEDGUIDE SECTION
```

---

## 4. DATA STRUCTURE FOR EXTRACTION

### 4.1 Recommended Knowledge Graph Schema

```
DRUG_PRODUCT
├── identifiers
│   ├── ndc (primary)
│   ├── set_id (version tracking)
│   ├── application_number (ANDA/NDA/BLA)
│   └── document_id (specific version)
├── product_info
│   ├── name
│   ├── generic_name
│   ├── form (TABLET, LIQUID, etc.)
│   ├── route (ORAL, TOPICAL, etc.)
│   ├── marketing_status
│   └── approval_status
├── ingredients
│   ├── active[]
│   │   ├── name
│   │   ├── unii_code  ← KEY for merging
│   │   └── strength
│   └── inactive[]
├── clinical_content
│   ├── indications_text (34067-9)
│   ├── contraindications (34070-3)
│   ├── boxed_warnings (34066-1)
│   ├── warnings_precautions (34071-1, 43685-7)
│   ├── storage_requirements (44425-7)
│   ├── dosage_administration (34068-7)
│   ├── adverse_reactions (34084-4)
│   └── drug_interactions (34073-7)
├── physical_characteristics
│   ├── color
│   ├── shape
│   ├── size
│   ├── imprint
│   └── flavor
└── organizations
    ├── manufacturer
    ├── labeler
    └── duns_number
```

### 4.2 UNII Code Importance

**UNII (Unique Ingredient Identifier)** is the most important identifier for merging:
- Links to FDA Substance Registration System
- Consistent across all products containing the same ingredient
- Can be used to link to:
  - PubChem
  - ChEMBL
  - DrugBank
  - RxNorm

Example UNIIs found in these files:
```
57Y76R9ATQ = NAPROXEN
362O9ITL9D = ACETAMINOPHEN
WK2XYI10QM = IBUPROFEN
34AP3BBP9T = PIMOBENDAN
ETJ7Z6XBU4 = SILICON DIOXIDE
```

---

## 5. XML STRUCTURE OVERVIEW

### Document Hierarchy
```xml
<document>
  <id root="[UUID]"/>                         <!-- Document ID -->
  <code displayName="[LABEL TYPE]"/>          <!-- Document type -->
  <title>[Drug Name]</title>
  <effectiveTime value="[YYYYMMDD]"/>
  <setId root="[UUID]"/>                      <!-- Stable across versions -->
  <versionNumber value="N"/>

  <author>
    <representedOrganization>
      <id extension="[DUNS]"/>
      <name>[Company Name]</name>
    </representedOrganization>
  </author>

  <component>
    <structuredBody>
      <component>
        <section>
          <code code="[LOINC]" displayName="[SECTION TYPE]"/>
          <title>[Section Title]</title>
          <text>[Clinical Content]</text>

          <!-- Product data section contains -->
          <subject>
            <manufacturedProduct>
              <code code="[NDC]"/>
              <name>[Product Name]</name>
              <formCode displayName="[FORM]"/>
              <ingredient classCode="ACTIB|IACT">
                <ingredientSubstance>
                  <code code="[UNII]"/>
                  <name>[Ingredient Name]</name>
                </ingredientSubstance>
              </ingredient>
            </manufacturedProduct>
          </subject>
        </section>
      </component>
    </structuredBody>
  </component>
</document>
```

---

## 6. DRUG CATEGORIES IN THIS DATASET

| Category | Count | Typical Content |
|----------|-------|-----------------|
| **Homeopathic** | 5 | Minimal clinical data, HPUS references |
| **OTC** | 5 | Drug Facts format, consumer-oriented |
| **Prescription** | 5 | Full prescribing information (PLR format) |
| **Other/Bulk** | 5 | API/bulk ingredients, minimal labeling |

**Note:** Prescription drugs have the richest clinical content including boxed warnings, contraindications, clinical studies, and pharmacology sections.

---

## 7. RECOMMENDATIONS FOR KNOWLEDGE GRAPH

1. **Primary Key**: Use `SetID` for tracking drug products across label versions
2. **Ingredient Linking**: Use `UNII` codes to link ingredients across products and to external databases
3. **NDC Mapping**: Use NDC for linking to:
   - Claims/pricing data
   - RxNorm (via NDC-RxNorm mapping)
   - FDA Orange Book
4. **Version Tracking**: Store `versionNumber` and `effectiveTime` to track label changes
5. **Section Extraction**: Parse sections by LOINC code for consistent clinical content extraction
6. **Regulatory Linking**: Use ANDA/NDA/BLA numbers to link to FDA approval data

---

## 8. FILES BY CLINICAL RICHNESS

### Richest Content (Prescription drugs with boxed warnings):
- `prescription_570974d4-0d5b-4df2-b307-37380511835d.xml` (Naproxen)
- `prescription_da424329-9a63-4df3-bced-4157d2086e20.xml`

### Moderate Content (OTC drugs):
- `otc_2f8bbda5-0100-4d14-84b7-e5712f6dad6f.xml` (Acetaminophen)

### Basic Content (Homeopathic/Bulk):
- `homeopathic_*.xml` files
- `other_*.xml` files
