#!/usr/bin/env python3
"""
FDA SPL XML Drug Information Extractor

This script parses FDA Structured Product Labeling (SPL) XML files and extracts
all relevant drug information including product details, ingredients, warnings,
dosage, and manufacturer information.
"""

import xml.etree.ElementTree as ET
import os
import json
from datetime import datetime

# XML namespace
NS = {'hl7': 'urn:hl7-org:v3'}


def parse_xml_file(filepath):
    """Parse a single SPL XML file and extract all information."""
    tree = ET.parse(filepath)
    root = tree.getroot()

    drug_info = {
        'filename': os.path.basename(filepath),
        'document_id': '',
        'document_type': '',
        'title': '',
        'effective_date': '',
        'version': '',
        'author': {},
        'product': {},
        'sections': []
    }

    # Document ID
    id_elem = root.find('hl7:id', NS)
    if id_elem is not None:
        drug_info['document_id'] = id_elem.get('root', '')

    # Document type/code
    code_elem = root.find('hl7:code', NS)
    if code_elem is not None:
        drug_info['document_type'] = code_elem.get('displayName', '')

    # Title
    title_elem = root.find('hl7:title', NS)
    if title_elem is not None:
        drug_info['title'] = title_elem.text or ''

    # Effective date
    eff_time = root.find('hl7:effectiveTime', NS)
    if eff_time is not None:
        drug_info['effective_date'] = eff_time.get('value', '')

    # Version
    version_elem = root.find('hl7:versionNumber', NS)
    if version_elem is not None:
        drug_info['version'] = version_elem.get('value', '')

    # Author/Organization
    author_elem = root.find('.//hl7:author//hl7:representedOrganization', NS)
    if author_elem is not None:
        org_name = author_elem.find('hl7:name', NS)
        org_id = author_elem.find('hl7:id', NS)
        drug_info['author'] = {
            'name': org_name.text if org_name is not None else '',
            'id': org_id.get('extension', '') if org_id is not None else ''
        }

    # Product information
    mfg_product = root.find('.//hl7:manufacturedProduct/hl7:manufacturedProduct', NS)
    if mfg_product is not None:
        product = {}

        # Product code (NDC)
        prod_code = mfg_product.find('hl7:code', NS)
        if prod_code is not None:
            product['ndc'] = prod_code.get('code', '')

        # Product name
        prod_name = mfg_product.find('hl7:name', NS)
        if prod_name is not None:
            product['name'] = prod_name.text or ''

        # Form (tablet, liquid, etc.)
        form_code = mfg_product.find('hl7:formCode', NS)
        if form_code is not None:
            product['form'] = form_code.get('displayName', '')

        # Generic medicine name
        generic = mfg_product.find('.//hl7:genericMedicine/hl7:name', NS)
        if generic is not None:
            product['generic_name'] = generic.text or ''

        # Active ingredients
        product['active_ingredients'] = []
        for ingredient in mfg_product.findall('.//hl7:ingredient[@classCode="ACTIB"]', NS):
            ing_info = {}

            # Ingredient name
            ing_name = ingredient.find('.//hl7:ingredientSubstance/hl7:name', NS)
            if ing_name is not None:
                ing_info['name'] = ing_name.text or ''

            # Ingredient code
            ing_code = ingredient.find('.//hl7:ingredientSubstance/hl7:code', NS)
            if ing_code is not None:
                ing_info['code'] = ing_code.get('code', '')

            # Quantity/strength
            numerator = ingredient.find('.//hl7:quantity/hl7:numerator', NS)
            denominator = ingredient.find('.//hl7:quantity/hl7:denominator', NS)
            if numerator is not None:
                ing_info['strength'] = f"{numerator.get('value', '')} {numerator.get('unit', '')}"
            if denominator is not None:
                ing_info['per'] = f"{denominator.get('value', '')} {denominator.get('unit', '')}"

            if ing_info:
                product['active_ingredients'].append(ing_info)

        # Inactive ingredients
        product['inactive_ingredients'] = []
        for ingredient in mfg_product.findall('.//hl7:ingredient[@classCode="IACT"]', NS):
            ing_name = ingredient.find('.//hl7:ingredientSubstance/hl7:name', NS)
            if ing_name is not None:
                product['inactive_ingredients'].append(ing_name.text or '')

        # Packaging information
        product['packaging'] = []
        for content in mfg_product.findall('.//hl7:asContent', NS):
            pkg_info = {}

            numerator = content.find('hl7:quantity/hl7:numerator', NS)
            if numerator is not None:
                pkg_info['quantity'] = f"{numerator.get('value', '')} {numerator.get('unit', '')}"

            container = content.find('.//hl7:containerPackagedProduct', NS)
            if container is not None:
                pkg_code = container.find('hl7:code', NS)
                pkg_form = container.find('hl7:formCode', NS)
                if pkg_code is not None:
                    pkg_info['ndc'] = pkg_code.get('code', '')
                if pkg_form is not None:
                    pkg_info['container'] = pkg_form.get('displayName', '')

            if pkg_info:
                product['packaging'].append(pkg_info)

        # Route of administration
        route = root.find('.//hl7:consumedIn//hl7:routeCode', NS)
        if route is not None:
            product['route'] = route.get('displayName', '')

        # Marketing status
        marketing = root.find('.//hl7:marketingAct', NS)
        if marketing is not None:
            status_code = marketing.find('hl7:statusCode', NS)
            if status_code is not None:
                product['marketing_status'] = status_code.get('code', '')

            eff_time_low = marketing.find('.//hl7:low', NS)
            if eff_time_low is not None:
                product['marketing_start_date'] = eff_time_low.get('value', '')

        # Approval status
        approval = root.find('.//hl7:approval/hl7:code', NS)
        if approval is not None:
            product['approval_status'] = approval.get('displayName', '')

        # Physical characteristics (color, shape, size, imprint)
        for char in root.findall('.//hl7:characteristic', NS):
            char_code = char.find('hl7:code', NS)
            char_value = char.find('hl7:value', NS)
            if char_code is not None and char_value is not None:
                code_name = char_code.get('code', '')
                if code_name == 'SPLCOLOR':
                    product['color'] = char_value.get('displayName', '')
                elif code_name == 'SPLSHAPE':
                    product['shape'] = char_value.get('displayName', '')
                elif code_name == 'SPLSIZE':
                    product['size'] = f"{char_value.get('value', '')} {char_value.get('unit', '')}"
                elif code_name == 'SPLIMPRINT':
                    product['imprint'] = char_value.text or ''

        drug_info['product'] = product

    # Extract all sections (warnings, indications, dosage, etc.)
    for section in root.findall('.//hl7:section', NS):
        section_info = {}

        section_code = section.find('hl7:code', NS)
        if section_code is not None:
            section_info['code'] = section_code.get('code', '')
            section_info['type'] = section_code.get('displayName', '')

        section_title = section.find('hl7:title', NS)
        if section_title is not None:
            section_info['title'] = section_title.text or ''

        # Extract text content
        text_elem = section.find('hl7:text', NS)
        if text_elem is not None:
            section_info['content'] = extract_text_content(text_elem)

        if section_info.get('type') or section_info.get('content'):
            drug_info['sections'].append(section_info)

    return drug_info


def extract_text_content(elem):
    """Extract all text content from an XML element recursively."""
    texts = []

    if elem.text:
        texts.append(elem.text.strip())

    for child in elem:
        child_text = extract_text_content(child)
        if child_text:
            texts.append(child_text)
        if child.tail:
            texts.append(child.tail.strip())

    return ' '.join(filter(None, texts))


def categorize_drug(filepath):
    """Determine drug category from filename."""
    basename = os.path.basename(filepath)
    if basename.startswith('homeopathic'):
        return 'Homeopathic'
    elif basename.startswith('otc'):
        return 'OTC (Over-the-Counter)'
    elif basename.startswith('prescription'):
        return 'Prescription'
    elif basename.startswith('other'):
        return 'Other/Bulk Ingredient'
    return 'Unknown'


def generate_report(all_drugs):
    """Generate a comprehensive text report of all extracted information."""
    report = []
    report.append("=" * 80)
    report.append("FDA SPL DRUG INFORMATION EXTRACTION REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 40)
    report.append(f"Total files processed: {len(all_drugs)}")

    categories = {}
    for drug in all_drugs:
        cat = drug.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1

    report.append("\nBy Category:")
    for cat, count in sorted(categories.items()):
        report.append(f"  - {cat}: {count}")
    report.append("")

    # Detailed information for each drug
    for i, drug in enumerate(all_drugs, 1):
        report.append("=" * 80)
        report.append(f"DRUG #{i}: {drug.get('title', 'Unknown')}")
        report.append("=" * 80)
        report.append("")

        report.append("DOCUMENT INFORMATION")
        report.append("-" * 40)
        report.append(f"  Filename: {drug.get('filename', '')}")
        report.append(f"  Document ID: {drug.get('document_id', '')}")
        report.append(f"  Document Type: {drug.get('document_type', '')}")
        report.append(f"  Category: {drug.get('category', '')}")
        report.append(f"  Effective Date: {format_date(drug.get('effective_date', ''))}")
        report.append(f"  Version: {drug.get('version', '')}")
        report.append("")

        author = drug.get('author', {})
        if author:
            report.append("MANUFACTURER/AUTHOR")
            report.append("-" * 40)
            report.append(f"  Name: {author.get('name', '')}")
            report.append(f"  ID: {author.get('id', '')}")
            report.append("")

        product = drug.get('product', {})
        if product:
            report.append("PRODUCT INFORMATION")
            report.append("-" * 40)
            report.append(f"  Product Name: {product.get('name', '')}")
            report.append(f"  Generic Name: {product.get('generic_name', '')}")
            report.append(f"  NDC: {product.get('ndc', '')}")
            report.append(f"  Form: {product.get('form', '')}")
            report.append(f"  Route: {product.get('route', '')}")
            report.append(f"  Marketing Status: {product.get('marketing_status', '')}")
            report.append(f"  Approval Status: {product.get('approval_status', '')}")

            if product.get('color'):
                report.append(f"  Color: {product.get('color', '')}")
            if product.get('shape'):
                report.append(f"  Shape: {product.get('shape', '')}")
            if product.get('size'):
                report.append(f"  Size: {product.get('size', '')}")
            if product.get('imprint'):
                report.append(f"  Imprint: {product.get('imprint', '')}")
            report.append("")

            if product.get('active_ingredients'):
                report.append("ACTIVE INGREDIENTS")
                report.append("-" * 40)
                for ing in product['active_ingredients']:
                    strength = ing.get('strength', '')
                    per = ing.get('per', '')
                    strength_str = f" ({strength}" + (f" per {per})" if per else ")") if strength else ""
                    report.append(f"  - {ing.get('name', 'Unknown')}{strength_str}")
                report.append("")

            if product.get('inactive_ingredients'):
                report.append("INACTIVE INGREDIENTS")
                report.append("-" * 40)
                for ing in product['inactive_ingredients']:
                    report.append(f"  - {ing}")
                report.append("")

            if product.get('packaging'):
                report.append("PACKAGING")
                report.append("-" * 40)
                for pkg in product['packaging'][:5]:  # Limit to first 5 for readability
                    ndc = pkg.get('ndc', '')
                    qty = pkg.get('quantity', '')
                    container = pkg.get('container', '')
                    if ndc or qty:
                        report.append(f"  - NDC: {ndc}, Quantity: {qty}, Container: {container}")
                if len(product['packaging']) > 5:
                    report.append(f"  ... and {len(product['packaging']) - 5} more packaging options")
                report.append("")

        # Key sections
        sections = drug.get('sections', [])
        key_section_types = [
            'INDICATIONS & USAGE SECTION',
            'WARNINGS SECTION',
            'DOSAGE & ADMINISTRATION SECTION',
            'OTC - ACTIVE INGREDIENT SECTION',
            'OTC - PURPOSE SECTION',
            'OTC - KEEP OUT OF REACH OF CHILDREN SECTION'
        ]

        for section in sections:
            section_type = section.get('type', '')
            if section_type in key_section_types and section.get('content'):
                report.append(section_type.upper())
                report.append("-" * 40)
                content = section.get('content', '')
                # Truncate long content
                if len(content) > 500:
                    content = content[:500] + "..."
                report.append(f"  {content}")
                report.append("")

        report.append("")

    return '\n'.join(report)


def format_date(date_str):
    """Format date string from YYYYMMDD to readable format."""
    if len(date_str) == 8:
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return date_str
    return date_str


def main():
    """Main function to process all XML files."""
    xml_dir = os.path.join(os.path.dirname(__file__), 'xml_sample')

    all_drugs = []

    # Process all XML files
    for filename in sorted(os.listdir(xml_dir)):
        if filename.endswith('.xml'):
            filepath = os.path.join(xml_dir, filename)
            print(f"Processing: {filename}")

            try:
                drug_info = parse_xml_file(filepath)
                drug_info['category'] = categorize_drug(filepath)
                all_drugs.append(drug_info)
            except Exception as e:
                print(f"  Error processing {filename}: {e}")

    # Generate and save JSON output
    json_output = os.path.join(os.path.dirname(__file__), 'extracted_drug_info.json')
    with open(json_output, 'w') as f:
        json.dump(all_drugs, f, indent=2)
    print(f"\nJSON output saved to: {json_output}")

    # Generate and save text report
    report = generate_report(all_drugs)
    report_output = os.path.join(os.path.dirname(__file__), 'drug_info_report.txt')
    with open(report_output, 'w') as f:
        f.write(report)
    print(f"Text report saved to: {report_output}")

    print(f"\nSuccessfully processed {len(all_drugs)} drug files!")

    return all_drugs


if __name__ == '__main__':
    main()
