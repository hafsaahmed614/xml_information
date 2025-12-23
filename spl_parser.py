#!/usr/bin/env python3
"""
FDA DailyMed SPL XML Parser for Drug Knowledge Graph

Parses HL7 v3 SPL (Structured Product Labeling) XML files and outputs
normalized JSON suitable for integration into a master drug knowledge graph.

Supports: Prescription, OTC, Homeopathic, and Other SPL document types.

Author: Claude Code
Version: 1.0.0
"""

import xml.etree.ElementTree as ET
import json
import os
import re
import html
import argparse
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import hashlib

# =============================================================================
# CONSTANTS
# =============================================================================

PARSER_VERSION = "1.0.0"

# HL7 v3 SPL namespace
NS = {'hl7': 'urn:hl7-org:v3'}

# Code system OIDs
CODE_SYSTEMS = {
    'LOINC': '2.16.840.1.113883.6.1',
    'NDC': '2.16.840.1.113883.6.69',
    'UNII': '2.16.840.1.113883.4.9',
    'FDA_CODE': '2.16.840.1.113883.3.26.1.1',
    'TERRITORY': '2.16.840.1.113883.5.28',
    'CHARACTERISTIC': '2.16.840.1.113883.1.11.19255',
    'DUNS': '1.3.6.1.4.1.519.1',
    'FDA_APPLICATION': '2.16.840.1.113883.3.150',
    'OTC_MONOGRAPH': '2.16.840.1.113883.3.9421',
}

# Document type codes (LOINC)
DOCUMENT_TYPE_CODES = {
    '34391-3': 'prescription',
    '34390-5': 'otc',
    '50577-6': 'otc',  # OTC animal drug
    '81203-2': 'other',  # Bulk ingredient
    '53404-0': 'other',  # Dietary supplement
}

# Section codes for presence flags (LOINC)
SECTION_CODES = {
    'BOXED_WARNING': ['34066-1'],
    'INDICATIONS_AND_USAGE': ['34067-9', '43679-0'],
    'CONTRAINDICATIONS': ['34070-3', '43680-8'],
    'WARNINGS_AND_PRECAUTIONS': ['34071-1', '43685-7', '34072-9', '50566-9', '50567-7'],
    'STORAGE_AND_HANDLING': ['44425-7', '34069-5'],
    'DOSAGE_AND_ADMINISTRATION': ['34068-7'],
    'ADVERSE_REACTIONS': ['34084-4'],
    'DRUG_INTERACTIONS': ['34073-7'],
    'CLINICAL_PHARMACOLOGY': ['34090-1'],
    'DESCRIPTION': ['34089-3'],
    'OVERDOSAGE': ['34088-5'],
    'PREGNANCY': ['42228-7', '53414-9'],
    'PEDIATRIC_USE': ['34081-0'],
    'GERIATRIC_USE': ['34074-5'],
}

# Known LOINC section codes with their display names
LOINC_SECTIONS = {
    '34066-1': 'BOXED WARNING SECTION',
    '34067-9': 'INDICATIONS & USAGE SECTION',
    '34068-7': 'DOSAGE & ADMINISTRATION SECTION',
    '34069-5': 'HOW SUPPLIED SECTION',
    '34070-3': 'CONTRAINDICATIONS SECTION',
    '34071-1': 'WARNINGS SECTION',
    '34072-9': 'GENERAL PRECAUTIONS SECTION',
    '34073-7': 'DRUG INTERACTIONS SECTION',
    '34074-5': 'GERIATRIC USE SECTION',
    '34075-2': 'LABORATORY TESTS SECTION',
    '34076-0': 'INFORMATION FOR PATIENTS SECTION',
    '34079-4': 'DRUG & OR LABORATORY TEST INTERACTIONS SECTION',
    '34080-2': 'NURSING MOTHERS SECTION',
    '34081-0': 'PEDIATRIC USE SECTION',
    '34082-8': 'ABUSE SECTION',
    '34083-6': 'DEPENDENCE SECTION',
    '34084-4': 'ADVERSE REACTIONS SECTION',
    '34085-1': 'CONTROLLED SUBSTANCE SECTION',
    '34086-9': 'DRUG ABUSE AND DEPENDENCE SECTION',
    '34087-7': 'MECHANISM OF ACTION SECTION',
    '34088-5': 'OVERDOSAGE SECTION',
    '34089-3': 'DESCRIPTION SECTION',
    '34090-1': 'CLINICAL PHARMACOLOGY SECTION',
    '34092-7': 'CARCINOGENESIS & MUTAGENESIS SECTION',
    '34093-5': 'REFERENCES SECTION',
    '42228-7': 'PREGNANCY SECTION',
    '42229-5': 'SPL UNCLASSIFIED SECTION',
    '43678-2': 'DOSAGE FORMS & STRENGTHS SECTION',
    '43679-0': 'INDICATIONS AND USAGE SECTION',
    '43680-8': 'CONTRAINDICATIONS SECTION',
    '43681-6': 'PHARMACODYNAMICS SECTION',
    '43682-4': 'PHARMACOKINETICS SECTION',
    '43683-2': 'RECENT MAJOR CHANGES SECTION',
    '43684-0': 'USE IN SPECIFIC POPULATIONS SECTION',
    '43685-7': 'WARNINGS AND PRECAUTIONS SECTION',
    '44425-7': 'STORAGE AND HANDLING SECTION',
    '48780-1': 'SPL PRODUCT DATA ELEMENTS SECTION',
    '50565-1': 'OTC - KEEP OUT OF REACH OF CHILDREN SECTION',
    '50566-9': 'OTC - STOP USE SECTION',
    '50567-7': 'OTC - WHEN USING SECTION',
    '50568-5': 'OTC - ASK DOCTOR/PHARMACIST SECTION',
    '50569-3': 'OTC - ASK DOCTOR SECTION',
    '50570-1': 'OTC - DO NOT USE SECTION',
    '51727-6': 'INACTIVE INGREDIENT SECTION',
    '51945-4': 'PACKAGE LABEL.PRINCIPAL DISPLAY PANEL',
    '53413-1': 'OTC - QUESTIONS SECTION',
    '53414-9': 'OTC - PREGNANCY OR BREAST FEEDING SECTION',
    '55105-1': 'OTC - PURPOSE SECTION',
    '55106-9': 'OTC - ACTIVE INGREDIENT SECTION',
    '58476-3': 'SPL PATIENT PACKAGE INSERT SECTION',
    '59845-8': 'INSTRUCTIONS FOR USE SECTION',
    '60561-8': 'OTHER SAFETY INFORMATION',
    '68498-5': 'PATIENT MEDICATION INFORMATION SECTION',
    '77290-5': 'SPL MEDGUIDE SECTION',
}

# DEA Schedule codes
DEA_SCHEDULES = {
    'C48672': 'CI',
    'C48675': 'CII',
    'C48676': 'CIII',
    'C48677': 'CIV',
    'C48679': 'CV',
}


# =============================================================================
# DATA CLASSES (JSON SCHEMA)
# =============================================================================

@dataclass
class Source:
    dataset: str = "DailyMed"
    format: str = "SPL"
    input_filename: str = ""
    parsed_at: str = ""
    parser_version: str = PARSER_VERSION


@dataclass
class DocumentId:
    root: Optional[str] = None
    extension: Optional[str] = None


@dataclass
class SPLMetadata:
    document_id: DocumentId = field(default_factory=DocumentId)
    set_id: DocumentId = field(default_factory=DocumentId)
    version_number: Optional[int] = None
    effective_time: Optional[str] = None
    title: Optional[str] = None
    document_type: str = "unknown"


@dataclass
class OrgId:
    root: Optional[str] = None
    extension: Optional[str] = None
    type_hint: Optional[str] = None


@dataclass
class Labeler:
    name: Optional[str] = None
    org_ids: List[OrgId] = field(default_factory=list)


@dataclass
class NDCInfo:
    product_ndcs: List[str] = field(default_factory=list)
    package_ndcs: List[str] = field(default_factory=list)


@dataclass
class Regulatory:
    rx_otc_flag: str = "UNKNOWN"
    application_number: Optional[str] = None
    otc_monograph_id: Optional[str] = None
    marketing_category: Optional[str] = None
    dea_schedule: Optional[str] = None


@dataclass
class Strength:
    numerator_value: Optional[float] = None
    numerator_unit: Optional[str] = None
    denominator_value: Optional[float] = None
    denominator_unit: Optional[str] = None


@dataclass
class HomeopathicInfo:
    potency: Optional[str] = None
    source_material: Optional[str] = None


@dataclass
class Ingredient:
    name: Optional[str] = None
    role: str = "other"
    unii: Optional[str] = None
    strength: Optional[Strength] = None
    homeopathic: Optional[HomeopathicInfo] = None
    _xpath: Optional[str] = None


@dataclass
class PackageQuantity:
    value: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class Package:
    package_ndc: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[PackageQuantity] = None
    marketing_start_date: Optional[str] = None
    marketing_status: Optional[str] = None


@dataclass
class PhysicalCharacteristics:
    color: Optional[str] = None
    shape: Optional[str] = None
    size: Optional[str] = None
    imprint: Optional[str] = None
    flavor: Optional[str] = None


@dataclass
class Product:
    product_name: Optional[str] = None
    generic_name: Optional[str] = None
    routes: List[str] = field(default_factory=list)
    dosage_forms: List[str] = field(default_factory=list)
    ndc: NDCInfo = field(default_factory=NDCInfo)
    regulatory: Regulatory = field(default_factory=Regulatory)
    ingredients: List[Ingredient] = field(default_factory=list)
    packages: List[Package] = field(default_factory=list)
    physical_characteristics: Optional[PhysicalCharacteristics] = None
    _xpath: Optional[str] = None


@dataclass
class Section:
    code_system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None
    title: Optional[str] = None
    text_xhtml: Optional[str] = None
    text_plain: Optional[str] = None
    _xpath: Optional[str] = None


@dataclass
class MergeKeys:
    primary: List[str] = field(default_factory=list)
    secondary: List[str] = field(default_factory=list)


@dataclass
class SectionPresenceFlags:
    boxed_warning: bool = False
    indications_and_usage: bool = False
    contraindications: bool = False
    warnings_and_precautions: bool = False
    storage_and_handling: bool = False
    dosage_and_administration: bool = False
    adverse_reactions: bool = False
    drug_interactions: bool = False


@dataclass
class Derived:
    merge_keys: MergeKeys = field(default_factory=MergeKeys)
    section_presence_flags: SectionPresenceFlags = field(default_factory=SectionPresenceFlags)


@dataclass
class SPLDocument:
    source: Source = field(default_factory=Source)
    spl: SPLMetadata = field(default_factory=SPLMetadata)
    labeler: Labeler = field(default_factory=Labeler)
    products: List[Product] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    derived: Derived = field(default_factory=Derived)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, removing private fields starting with _"""
        def clean_dict(obj):
            if isinstance(obj, dict):
                return {k: clean_dict(v) for k, v in obj.items() if not k.startswith('_')}
            elif isinstance(obj, list):
                return [clean_dict(item) for item in obj]
            elif hasattr(obj, '__dataclass_fields__'):
                return clean_dict(asdict(obj))
            else:
                return obj
        return clean_dict(asdict(self))


# =============================================================================
# KNOWLEDGE GRAPH ENTITIES AND EDGES
# =============================================================================

@dataclass
class KGEntity:
    entity_type: str
    entity_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KGEdge:
    edge_type: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    entities: List[KGEntity] = field(default_factory=list)
    edges: List[KGEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entities': [asdict(e) for e in self.entities],
            'edges': [asdict(e) for e in self.edges]
        }


# =============================================================================
# PARSER CLASS
# =============================================================================

class SPLParser:
    """
    FDA DailyMed SPL XML Parser

    Parses HL7 v3 SPL files and extracts structured drug information
    for integration into a drug knowledge graph.
    """

    def __init__(self, include_provenance: bool = True):
        """
        Initialize parser.

        Args:
            include_provenance: If True, include XPath/context info in output
        """
        self.include_provenance = include_provenance
        self.root = None
        self.filename = None

    def parse_file(self, filepath: str) -> SPLDocument:
        """
        Parse a single SPL XML file.

        Args:
            filepath: Path to SPL XML file

        Returns:
            SPLDocument with extracted data
        """
        self.filename = os.path.basename(filepath)
        tree = ET.parse(filepath)
        self.root = tree.getroot()

        doc = SPLDocument()

        # Source metadata
        doc.source = Source(
            input_filename=self.filename,
            parsed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Extract all components
        doc.spl = self._extract_spl_metadata()
        doc.labeler = self._extract_labeler()
        doc.products = self._extract_products()
        doc.sections = self._extract_sections()
        doc.derived = self._build_derived(doc)

        return doc

    def parse_directory(self, dirpath: str, output_dir: Optional[str] = None) -> List[SPLDocument]:
        """
        Parse all XML files in a directory.

        Args:
            dirpath: Path to directory containing SPL XML files
            output_dir: Optional output directory for individual JSON files

        Returns:
            List of SPLDocument objects
        """
        documents = []
        xml_files = sorted(Path(dirpath).glob('*.xml'))

        for xml_file in xml_files:
            try:
                doc = self.parse_file(str(xml_file))
                documents.append(doc)

                if output_dir:
                    output_path = Path(output_dir) / f"{xml_file.stem}.json"
                    with open(output_path, 'w') as f:
                        json.dump(doc.to_dict(), f, indent=2)

            except Exception as e:
                print(f"Error parsing {xml_file}: {e}")

        return documents

    # =========================================================================
    # SPL METADATA EXTRACTION
    # =========================================================================

    def _extract_spl_metadata(self) -> SPLMetadata:
        """Extract SPL document-level metadata."""
        meta = SPLMetadata()

        # Document ID
        id_elem = self.root.find('hl7:id', NS)
        if id_elem is not None:
            meta.document_id = DocumentId(
                root=id_elem.get('root'),
                extension=id_elem.get('extension')
            )

        # Set ID (stable across versions)
        set_id_elem = self.root.find('hl7:setId', NS)
        if set_id_elem is not None:
            meta.set_id = DocumentId(
                root=set_id_elem.get('root'),
                extension=set_id_elem.get('extension')
            )

        # Version number
        version_elem = self.root.find('hl7:versionNumber', NS)
        if version_elem is not None:
            try:
                meta.version_number = int(version_elem.get('value', 0))
            except (ValueError, TypeError):
                meta.version_number = None

        # Effective time
        eff_time = self.root.find('hl7:effectiveTime', NS)
        if eff_time is not None:
            meta.effective_time = eff_time.get('value')

        # Title
        title_elem = self.root.find('hl7:title', NS)
        if title_elem is not None:
            meta.title = self._get_text_content(title_elem)

        # Document type (from code element)
        code_elem = self.root.find('hl7:code', NS)
        if code_elem is not None:
            code = code_elem.get('code', '')
            display_name = code_elem.get('displayName', '').lower()

            if code in DOCUMENT_TYPE_CODES:
                meta.document_type = DOCUMENT_TYPE_CODES[code]
            elif 'prescription' in display_name:
                meta.document_type = 'prescription'
            elif 'otc' in display_name or 'over' in display_name:
                meta.document_type = 'otc'
            elif 'homeopathic' in display_name:
                meta.document_type = 'homeopathic'
            elif 'bulk' in display_name or 'dietary' in display_name:
                meta.document_type = 'other'

            # Also check filename for hints
            if meta.document_type == 'unknown' and self.filename:
                fn_lower = self.filename.lower()
                if fn_lower.startswith('prescription'):
                    meta.document_type = 'prescription'
                elif fn_lower.startswith('otc'):
                    meta.document_type = 'otc'
                elif fn_lower.startswith('homeopathic'):
                    meta.document_type = 'homeopathic'
                elif fn_lower.startswith('other'):
                    meta.document_type = 'other'

        return meta

    # =========================================================================
    # LABELER EXTRACTION
    # =========================================================================

    def _extract_labeler(self) -> Labeler:
        """Extract labeler/manufacturer organization info."""
        labeler = Labeler()

        # Find representedOrganization (primary labeler)
        org_elem = self.root.find('.//hl7:author//hl7:representedOrganization', NS)
        if org_elem is not None:
            name_elem = org_elem.find('hl7:name', NS)
            if name_elem is not None:
                labeler.name = name_elem.text

            # Extract all organization IDs
            for id_elem in org_elem.findall('.//hl7:id', NS):
                root = id_elem.get('root')
                ext = id_elem.get('extension')

                if root or ext:
                    type_hint = None
                    if root == CODE_SYSTEMS['DUNS']:
                        type_hint = 'DUNS'
                    elif root:
                        # Try to identify other ID types
                        type_hint = self._identify_org_id_type(root)

                    org_id = OrgId(root=root, extension=ext, type_hint=type_hint)
                    # Avoid duplicates
                    if not any(o.root == root and o.extension == ext for o in labeler.org_ids):
                        labeler.org_ids.append(org_id)

        return labeler

    def _identify_org_id_type(self, root: str) -> Optional[str]:
        """Identify organization ID type from root OID."""
        for name, oid in CODE_SYSTEMS.items():
            if root == oid:
                return name
        return None

    # =========================================================================
    # PRODUCT EXTRACTION
    # =========================================================================

    def _extract_products(self) -> List[Product]:
        """Extract all products from the SPL."""
        products = []

        # Find all manufacturedProduct elements
        for mfg_prod in self.root.findall('.//hl7:manufacturedProduct/hl7:manufacturedProduct', NS):
            product = self._parse_product(mfg_prod)
            if product:
                products.append(product)

        # If no products found with nested structure, try direct
        if not products:
            for mfg_prod in self.root.findall('.//hl7:manufacturedProduct', NS):
                # Avoid the wrapper element
                if mfg_prod.find('hl7:manufacturedProduct', NS) is None:
                    product = self._parse_product(mfg_prod)
                    if product:
                        products.append(product)

        return products

    def _parse_product(self, elem: ET.Element) -> Optional[Product]:
        """Parse a single manufacturedProduct element."""
        product = Product()

        # Product name
        name_elem = elem.find('hl7:name', NS)
        if name_elem is not None:
            product.product_name = self._get_text_content(name_elem)

        # Generic name
        generic = elem.find('.//hl7:genericMedicine/hl7:name', NS)
        if generic is not None:
            product.generic_name = generic.text

        # Form code (TABLET, LIQUID, etc.)
        form_code = elem.find('hl7:formCode', NS)
        if form_code is not None:
            form = form_code.get('displayName')
            if form:
                product.dosage_forms.append(form)

        # Product NDC
        code_elem = elem.find('hl7:code', NS)
        if code_elem is not None:
            ndc = code_elem.get('code')
            if ndc and self._is_ndc(ndc):
                if self._is_package_ndc(ndc):
                    product.ndc.package_ndcs.append(ndc)
                else:
                    product.ndc.product_ndcs.append(ndc)

        # Extract ingredients
        product.ingredients = self._extract_ingredients(elem)

        # Extract packages
        product.packages = self._extract_packages(elem)

        # Collect all package NDCs
        for pkg in product.packages:
            if pkg.package_ndc and pkg.package_ndc not in product.ndc.package_ndcs:
                product.ndc.package_ndcs.append(pkg.package_ndc)

        # Route of administration
        route_elem = elem.find('.//hl7:consumedIn//hl7:routeCode', NS)
        if route_elem is not None:
            route = route_elem.get('displayName')
            if route:
                product.routes.append(route)

        # Also check parent for route
        parent = self.root.find('.//hl7:manufacturedProduct', NS)
        if parent is not None:
            for route_elem in parent.findall('.//hl7:routeCode', NS):
                route = route_elem.get('displayName')
                if route and route not in product.routes:
                    product.routes.append(route)

        # Regulatory information
        product.regulatory = self._extract_regulatory(elem)

        # Physical characteristics
        product.physical_characteristics = self._extract_physical_characteristics(elem)

        return product if product.product_name else None

    def _extract_ingredients(self, elem: ET.Element) -> List[Ingredient]:
        """Extract ingredients from a product element."""
        ingredients = []

        for ing_elem in elem.findall('.//hl7:ingredient', NS):
            ingredient = Ingredient()

            # Role (active/inactive)
            class_code = ing_elem.get('classCode', '')
            if class_code == 'ACTIB' or class_code == 'ACTI':
                ingredient.role = 'active'
            elif class_code == 'IACT':
                ingredient.role = 'inactive'
            else:
                ingredient.role = 'other'

            # Ingredient substance info
            substance = ing_elem.find('.//hl7:ingredientSubstance', NS)
            if substance is not None:
                # Name
                name_elem = substance.find('hl7:name', NS)
                if name_elem is not None:
                    ingredient.name = name_elem.text

                # UNII code
                code_elem = substance.find('hl7:code', NS)
                if code_elem is not None:
                    code_system = code_elem.get('codeSystem')
                    if code_system == CODE_SYSTEMS['UNII']:
                        ingredient.unii = code_elem.get('code')

            # Strength/quantity
            quantity = ing_elem.find('hl7:quantity', NS)
            if quantity is not None:
                ingredient.strength = self._parse_quantity(quantity)

                # Check for homeopathic potency
                numerator = quantity.find('hl7:numerator', NS)
                if numerator is not None:
                    unit = numerator.get('unit', '')
                    if '[hp_C]' in unit or '[hp_X]' in unit:
                        value = numerator.get('value', '')
                        potency = f"{value}{unit.replace('[hp_', '').replace(']', '')}"
                        ingredient.homeopathic = HomeopathicInfo(
                            potency=potency,
                            source_material=ingredient.name
                        )

            if ingredient.name:
                ingredients.append(ingredient)

        return ingredients

    def _parse_quantity(self, quantity_elem: ET.Element) -> Strength:
        """Parse a quantity element into Strength."""
        strength = Strength()

        numerator = quantity_elem.find('hl7:numerator', NS)
        if numerator is not None:
            try:
                strength.numerator_value = float(numerator.get('value', 0))
            except (ValueError, TypeError):
                pass
            strength.numerator_unit = numerator.get('unit')

        denominator = quantity_elem.find('hl7:denominator', NS)
        if denominator is not None:
            try:
                strength.denominator_value = float(denominator.get('value', 0))
            except (ValueError, TypeError):
                pass
            strength.denominator_unit = denominator.get('unit')

        return strength

    def _extract_packages(self, elem: ET.Element) -> List[Package]:
        """Extract package information from a product element."""
        packages = []

        for content in elem.findall('.//hl7:asContent', NS):
            pkg = Package()

            # Quantity
            quantity = content.find('hl7:quantity', NS)
            if quantity is not None:
                numerator = quantity.find('hl7:numerator', NS)
                if numerator is not None:
                    try:
                        value = float(numerator.get('value', 0))
                    except (ValueError, TypeError):
                        value = None
                    unit = numerator.get('unit')
                    pkg.quantity = PackageQuantity(value=value, unit=unit)

            # Container/Package info
            container = content.find('.//hl7:containerPackagedProduct', NS)
            if container is not None:
                # Package NDC
                code_elem = container.find('hl7:code', NS)
                if code_elem is not None:
                    ndc = code_elem.get('code')
                    if ndc and self._is_ndc(ndc):
                        pkg.package_ndc = ndc

                # Container type
                form_code = container.find('hl7:formCode', NS)
                if form_code is not None:
                    pkg.description = form_code.get('displayName')

            # Marketing info
            marketing = content.find('.//hl7:marketingAct', NS)
            if marketing is not None:
                status = marketing.find('hl7:statusCode', NS)
                if status is not None:
                    pkg.marketing_status = status.get('code')

                eff_time = marketing.find('.//hl7:low', NS)
                if eff_time is not None:
                    pkg.marketing_start_date = eff_time.get('value')

            if pkg.package_ndc or pkg.quantity:
                packages.append(pkg)

        return packages

    def _extract_regulatory(self, elem: ET.Element) -> Regulatory:
        """Extract regulatory information."""
        reg = Regulatory()

        # Find approval element
        approval = self.root.find('.//hl7:approval', NS)
        if approval is not None:
            # Application number (ANDA, NDA, BLA)
            app_id = approval.find('hl7:id', NS)
            if app_id is not None:
                ext = app_id.get('extension')
                if ext:
                    reg.application_number = ext

            # Marketing category
            code_elem = approval.find('hl7:code', NS)
            if code_elem is not None:
                display = code_elem.get('displayName', '')
                code = code_elem.get('code', '')

                reg.marketing_category = display or code

                # Determine RX/OTC flag
                display_lower = display.lower()
                if 'otc' in display_lower or 'monograph' in display_lower:
                    reg.rx_otc_flag = 'OTC'
                elif 'prescription' in display_lower or 'nda' in display_lower.lower() or 'anda' in display_lower.lower():
                    reg.rx_otc_flag = 'RX'
                elif 'homeopathic' in display_lower:
                    reg.rx_otc_flag = 'OTC'  # Homeopathic typically OTC

                # OTC Monograph ID
                if 'monograph' in display_lower:
                    ext = approval.find('hl7:id', NS)
                    if ext is not None:
                        reg.otc_monograph_id = ext.get('extension')

        # DEA Schedule
        for char in self.root.findall('.//hl7:characteristic', NS):
            code_elem = char.find('hl7:code', NS)
            if code_elem is not None and 'SPLCONTROLLED' in code_elem.get('code', ''):
                value = char.find('hl7:value', NS)
                if value is not None:
                    schedule_code = value.get('code')
                    if schedule_code in DEA_SCHEDULES:
                        reg.dea_schedule = DEA_SCHEDULES[schedule_code]

        return reg

    def _extract_physical_characteristics(self, elem: ET.Element) -> Optional[PhysicalCharacteristics]:
        """Extract physical characteristics (color, shape, etc.)."""
        chars = PhysicalCharacteristics()
        found = False

        # Look in the parent manufacturedProduct for characteristics
        for char in self.root.findall('.//hl7:characteristic', NS):
            code_elem = char.find('hl7:code', NS)
            value_elem = char.find('hl7:value', NS)

            if code_elem is None or value_elem is None:
                continue

            code = code_elem.get('code', '')

            if code == 'SPLCOLOR':
                chars.color = value_elem.get('displayName')
                found = True
            elif code == 'SPLSHAPE':
                chars.shape = value_elem.get('displayName')
                found = True
            elif code == 'SPLSIZE':
                size_val = value_elem.get('value', '')
                size_unit = value_elem.get('unit', '')
                chars.size = f"{size_val} {size_unit}".strip()
                found = True
            elif code == 'SPLIMPRINT':
                chars.imprint = value_elem.text
                found = True
            elif code == 'SPLFLAVOR':
                chars.flavor = value_elem.get('displayName')
                found = True

        return chars if found else None

    # =========================================================================
    # NDC HELPERS
    # =========================================================================

    def _is_ndc(self, code: str) -> bool:
        """Check if a code looks like an NDC."""
        if not code:
            return False
        # NDCs typically have format: XXXXX-XXXX or XXXXX-XXXX-XX
        return bool(re.match(r'^\d{4,5}-\d{3,4}(-\d{1,2})?$', code))

    def _is_package_ndc(self, ndc: str) -> bool:
        """Check if NDC is package-level (has 3 segments)."""
        return ndc.count('-') == 2

    # =========================================================================
    # SECTION EXTRACTION
    # =========================================================================

    def _extract_sections(self) -> List[Section]:
        """Extract all sections from the SPL."""
        sections = []

        for section_elem in self.root.findall('.//hl7:section', NS):
            section = self._parse_section(section_elem)
            if section and (section.code or section.title):
                sections.append(section)

        return sections

    def _parse_section(self, elem: ET.Element) -> Section:
        """Parse a single section element."""
        section = Section()

        # Section code
        code_elem = elem.find('hl7:code', NS)
        if code_elem is not None:
            section.code = code_elem.get('code')
            section.code_system = code_elem.get('codeSystem')
            section.display = code_elem.get('displayName')

        # Title
        title_elem = elem.find('hl7:title', NS)
        if title_elem is not None:
            section.title = self._get_text_content(title_elem)

        # If no title but we have a known code, use the standard display name
        if not section.title and section.code and section.code in LOINC_SECTIONS:
            section.title = LOINC_SECTIONS[section.code]

        # Text content
        text_elem = elem.find('hl7:text', NS)
        if text_elem is not None:
            section.text_xhtml = self._serialize_element(text_elem)
            section.text_plain = self._extract_plain_text(text_elem)

        return section

    def _serialize_element(self, elem: ET.Element) -> str:
        """Serialize element to XHTML string."""
        # Remove namespace prefixes for cleaner output
        def strip_ns(tag):
            if '}' in tag:
                return tag.split('}')[1]
            return tag

        def elem_to_str(e, depth=0):
            tag = strip_ns(e.tag)
            attrs = ' '.join(f'{k}="{v}"' for k, v in e.attrib.items())

            children_text = ''
            if e.text:
                children_text += html.escape(e.text)

            for child in e:
                children_text += elem_to_str(child)
                if child.tail:
                    children_text += html.escape(child.tail)

            if children_text:
                return f'<{tag}{" " + attrs if attrs else ""}>{children_text}</{tag}>'
            else:
                return f'<{tag}{" " + attrs if attrs else ""}/>'

        return elem_to_str(elem)

    def _extract_plain_text(self, elem: ET.Element) -> str:
        """Extract and normalize plain text from element."""
        texts = []

        if elem.text:
            texts.append(elem.text)

        for child in elem:
            texts.append(self._extract_plain_text(child))
            if child.tail:
                texts.append(child.tail)

        # Normalize whitespace
        text = ' '.join(texts)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_text_content(self, elem: ET.Element) -> str:
        """Get all text content from an element."""
        return self._extract_plain_text(elem)

    # =========================================================================
    # DERIVED DATA
    # =========================================================================

    def _build_derived(self, doc: SPLDocument) -> Derived:
        """Build derived fields including merge keys and presence flags."""
        derived = Derived()

        # Build merge keys
        derived.merge_keys = self._build_merge_keys(doc)

        # Build section presence flags
        derived.section_presence_flags = self._build_presence_flags(doc.sections)

        return derived

    def _build_merge_keys(self, doc: SPLDocument) -> MergeKeys:
        """Build merge keys for knowledge graph integration."""
        keys = MergeKeys()

        # Primary keys
        if doc.spl.set_id.root:
            keys.primary.append(f"set_id:{doc.spl.set_id.root}")

        for product in doc.products:
            for ndc in product.ndc.product_ndcs:
                keys.primary.append(f"ndc:{ndc}")

        # Secondary keys
        if doc.spl.document_id.root:
            keys.secondary.append(f"doc_id:{doc.spl.document_id.root}")

        for product in doc.products:
            for ing in product.ingredients:
                if ing.unii:
                    key = f"unii:{ing.unii}"
                    if key not in keys.secondary:
                        keys.secondary.append(key)

        return keys

    def _build_presence_flags(self, sections: List[Section]) -> SectionPresenceFlags:
        """Build section presence flags based on section codes and titles."""
        flags = SectionPresenceFlags()

        section_codes_present = set()
        section_titles = set()

        for section in sections:
            if section.code:
                section_codes_present.add(section.code)
            if section.title:
                section_titles.add(section.title.upper())

        # Check each flag category
        for code in SECTION_CODES['BOXED_WARNING']:
            if code in section_codes_present:
                flags.boxed_warning = True
                break
        if not flags.boxed_warning:
            for title in section_titles:
                if 'BOXED WARNING' in title:
                    flags.boxed_warning = True
                    break

        for code in SECTION_CODES['INDICATIONS_AND_USAGE']:
            if code in section_codes_present:
                flags.indications_and_usage = True
                break
        if not flags.indications_and_usage:
            for title in section_titles:
                if 'INDICATION' in title:
                    flags.indications_and_usage = True
                    break

        for code in SECTION_CODES['CONTRAINDICATIONS']:
            if code in section_codes_present:
                flags.contraindications = True
                break
        if not flags.contraindications:
            for title in section_titles:
                if 'CONTRAINDICATION' in title:
                    flags.contraindications = True
                    break

        for code in SECTION_CODES['WARNINGS_AND_PRECAUTIONS']:
            if code in section_codes_present:
                flags.warnings_and_precautions = True
                break
        if not flags.warnings_and_precautions:
            for title in section_titles:
                if 'WARNING' in title or 'PRECAUTION' in title:
                    flags.warnings_and_precautions = True
                    break

        for code in SECTION_CODES['STORAGE_AND_HANDLING']:
            if code in section_codes_present:
                flags.storage_and_handling = True
                break
        if not flags.storage_and_handling:
            for title in section_titles:
                if 'STORAGE' in title or 'HANDLING' in title:
                    flags.storage_and_handling = True
                    break

        for code in SECTION_CODES['DOSAGE_AND_ADMINISTRATION']:
            if code in section_codes_present:
                flags.dosage_and_administration = True
                break

        for code in SECTION_CODES['ADVERSE_REACTIONS']:
            if code in section_codes_present:
                flags.adverse_reactions = True
                break

        for code in SECTION_CODES['DRUG_INTERACTIONS']:
            if code in section_codes_present:
                flags.drug_interactions = True
                break

        return flags

    # =========================================================================
    # KNOWLEDGE GRAPH OUTPUT
    # =========================================================================

    def to_knowledge_graph(self, doc: SPLDocument) -> KnowledgeGraph:
        """
        Convert SPLDocument to knowledge graph entities and edges.

        Entity types:
        - label_version: The specific SPL document version
        - product: Drug product
        - package: Product package
        - ingredient: Active/inactive ingredient
        - organization: Labeler/manufacturer
        - section: Label section

        Edge types:
        - HAS_LABEL_VERSION: org -> label
        - HAS_PRODUCT: label -> product
        - HAS_PACKAGE: product -> package
        - HAS_INGREDIENT: product -> ingredient
        - HAS_SECTION: label -> section
        - LABELED_BY: product -> org
        """
        kg = KnowledgeGraph()

        # Generate IDs
        label_id = f"label:{doc.spl.set_id.root or doc.spl.document_id.root}"
        org_id = f"org:{doc.labeler.org_ids[0].extension if doc.labeler.org_ids else 'unknown'}"

        # Organization entity
        if doc.labeler.name:
            kg.entities.append(KGEntity(
                entity_type="organization",
                entity_id=org_id,
                properties={
                    "name": doc.labeler.name,
                    "duns": doc.labeler.org_ids[0].extension if doc.labeler.org_ids else None
                }
            ))

        # Label version entity
        kg.entities.append(KGEntity(
            entity_type="label_version",
            entity_id=label_id,
            properties={
                "set_id": doc.spl.set_id.root,
                "document_id": doc.spl.document_id.root,
                "version": doc.spl.version_number,
                "effective_time": doc.spl.effective_time,
                "title": doc.spl.title,
                "document_type": doc.spl.document_type
            }
        ))

        # Edge: organization -> label (HAS_LABEL_VERSION)
        if doc.labeler.name:
            kg.edges.append(KGEdge(
                edge_type="HAS_LABEL_VERSION",
                source_id=org_id,
                target_id=label_id
            ))

        # Product entities
        for i, product in enumerate(doc.products):
            prod_ndc = product.ndc.product_ndcs[0] if product.ndc.product_ndcs else f"unknown_{i}"
            prod_id = f"product:{prod_ndc}"

            kg.entities.append(KGEntity(
                entity_type="product",
                entity_id=prod_id,
                properties={
                    "name": product.product_name,
                    "generic_name": product.generic_name,
                    "ndc": product.ndc.product_ndcs,
                    "routes": product.routes,
                    "dosage_forms": product.dosage_forms,
                    "rx_otc_flag": product.regulatory.rx_otc_flag,
                    "application_number": product.regulatory.application_number
                }
            ))

            # Edge: label -> product
            kg.edges.append(KGEdge(
                edge_type="HAS_PRODUCT",
                source_id=label_id,
                target_id=prod_id
            ))

            # Edge: product -> org (LABELED_BY)
            if doc.labeler.name:
                kg.edges.append(KGEdge(
                    edge_type="LABELED_BY",
                    source_id=prod_id,
                    target_id=org_id
                ))

            # Package entities
            for pkg in product.packages:
                if pkg.package_ndc:
                    pkg_id = f"package:{pkg.package_ndc}"
                    kg.entities.append(KGEntity(
                        entity_type="package",
                        entity_id=pkg_id,
                        properties={
                            "ndc": pkg.package_ndc,
                            "description": pkg.description,
                            "quantity": pkg.quantity.value if pkg.quantity else None,
                            "unit": pkg.quantity.unit if pkg.quantity else None
                        }
                    ))

                    kg.edges.append(KGEdge(
                        edge_type="HAS_PACKAGE",
                        source_id=prod_id,
                        target_id=pkg_id
                    ))

            # Ingredient entities
            for ing in product.ingredients:
                if ing.unii:
                    ing_id = f"ingredient:{ing.unii}"
                else:
                    ing_id = f"ingredient:{hashlib.md5(ing.name.encode()).hexdigest()[:12]}"

                kg.entities.append(KGEntity(
                    entity_type="ingredient",
                    entity_id=ing_id,
                    properties={
                        "name": ing.name,
                        "unii": ing.unii,
                        "role": ing.role,
                        "strength_value": ing.strength.numerator_value if ing.strength else None,
                        "strength_unit": ing.strength.numerator_unit if ing.strength else None
                    }
                ))

                kg.edges.append(KGEdge(
                    edge_type="HAS_INGREDIENT",
                    source_id=prod_id,
                    target_id=ing_id,
                    properties={"role": ing.role}
                ))

        # Section entities
        for section in doc.sections:
            if section.code:
                section_id = f"section:{label_id}:{section.code}"
                kg.entities.append(KGEntity(
                    entity_type="section",
                    entity_id=section_id,
                    properties={
                        "code": section.code,
                        "code_system": section.code_system,
                        "title": section.title,
                        "display": section.display,
                        "text_length": len(section.text_plain) if section.text_plain else 0
                    }
                ))

                kg.edges.append(KGEdge(
                    edge_type="HAS_SECTION",
                    source_id=label_id,
                    target_id=section_id
                ))

        return kg


# =============================================================================
# MAIN CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='FDA DailyMed SPL XML Parser for Drug Knowledge Graph',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse single file
  python spl_parser.py -i sample.xml -o output.json

  # Parse directory
  python spl_parser.py -d xml_sample/ -o output/

  # Parse directory with KG output
  python spl_parser.py -d xml_sample/ -o output/ --kg

  # Output as JSON Lines
  python spl_parser.py -d xml_sample/ --jsonl output.jsonl
        """
    )

    parser.add_argument('-i', '--input', help='Input SPL XML file')
    parser.add_argument('-d', '--directory', help='Input directory containing SPL XML files')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('--jsonl', help='Output as JSON Lines to specified file')
    parser.add_argument('--kg', action='store_true', help='Also output knowledge graph format')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either -i/--input or -d/--directory is required")

    spl_parser = SPLParser()
    indent = 2 if args.pretty else None

    if args.input:
        # Single file mode
        doc = spl_parser.parse_file(args.input)
        output_data = doc.to_dict()

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=indent)
            print(f"Output written to {args.output}")
        else:
            print(json.dumps(output_data, indent=indent))

        if args.kg:
            kg = spl_parser.to_knowledge_graph(doc)
            kg_output = args.output.replace('.json', '_kg.json') if args.output else None
            if kg_output:
                with open(kg_output, 'w') as f:
                    json.dump(kg.to_dict(), f, indent=indent)
                print(f"KG output written to {kg_output}")
            else:
                print("\n--- Knowledge Graph ---")
                print(json.dumps(kg.to_dict(), indent=indent))

    else:
        # Directory mode
        documents = []
        output_dir = args.output if args.output else None

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        xml_files = sorted(Path(args.directory).glob('*.xml'))

        for xml_file in xml_files:
            try:
                print(f"Parsing: {xml_file.name}")
                doc = spl_parser.parse_file(str(xml_file))
                documents.append(doc)

                if output_dir:
                    output_path = Path(output_dir) / f"{xml_file.stem}.json"
                    with open(output_path, 'w') as f:
                        json.dump(doc.to_dict(), f, indent=indent)

                    if args.kg:
                        kg = spl_parser.to_knowledge_graph(doc)
                        kg_path = Path(output_dir) / f"{xml_file.stem}_kg.json"
                        with open(kg_path, 'w') as f:
                            json.dump(kg.to_dict(), f, indent=indent)

            except Exception as e:
                print(f"  Error: {e}")

        if args.jsonl:
            with open(args.jsonl, 'w') as f:
                for doc in documents:
                    f.write(json.dumps(doc.to_dict()) + '\n')
            print(f"\nJSON Lines output written to {args.jsonl}")

        # Also write combined output
        if output_dir:
            combined_path = Path(output_dir) / "all_drugs_combined.json"
            with open(combined_path, 'w') as f:
                json.dump([doc.to_dict() for doc in documents], f, indent=indent)
            print(f"\nCombined output written to {combined_path}")

            if args.kg:
                all_kg = KnowledgeGraph()
                for doc in documents:
                    kg = spl_parser.to_knowledge_graph(doc)
                    all_kg.entities.extend(kg.entities)
                    all_kg.edges.extend(kg.edges)

                kg_combined_path = Path(output_dir) / "all_drugs_kg.json"
                with open(kg_combined_path, 'w') as f:
                    json.dump(all_kg.to_dict(), f, indent=indent)
                print(f"Combined KG output written to {kg_combined_path}")

        print(f"\nSuccessfully parsed {len(documents)} files")


if __name__ == '__main__':
    main()
