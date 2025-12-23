#!/usr/bin/env python3
"""
Unit tests for FDA DailyMed SPL XML Parser

Tests cover:
- Document metadata extraction
- Product/ingredient extraction
- Section extraction
- NDC parsing
- Knowledge graph generation
- Edge cases and robustness
"""

import unittest
import json
import os
import tempfile
from pathlib import Path

from spl_parser import (
    SPLParser,
    SPLDocument,
    LOINC_SECTIONS,
    SECTION_CODES,
    CODE_SYSTEMS
)


class TestSPLParserBasics(unittest.TestCase):
    """Test basic parser functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'

        # Get sample files for each category
        cls.sample_files = {
            'homeopathic': list(cls.xml_dir.glob('homeopathic_*.xml'))[:1],
            'otc': list(cls.xml_dir.glob('otc_*.xml'))[:1],
            'prescription': list(cls.xml_dir.glob('prescription_*.xml'))[:1],
            'other': list(cls.xml_dir.glob('other_*.xml'))[:1],
        }

    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = SPLParser()
        self.assertIsNotNone(parser)
        self.assertTrue(parser.include_provenance)

    def test_parse_homeopathic_file(self):
        """Test parsing a homeopathic SPL file."""
        if not self.sample_files['homeopathic']:
            self.skipTest("No homeopathic sample files available")

        doc = self.parser.parse_file(str(self.sample_files['homeopathic'][0]))

        self.assertIsInstance(doc, SPLDocument)
        self.assertEqual(doc.source.dataset, "DailyMed")
        self.assertEqual(doc.source.format, "SPL")
        self.assertIsNotNone(doc.source.parsed_at)
        self.assertIn(doc.spl.document_type, ['homeopathic', 'otc', 'unknown'])

    def test_parse_otc_file(self):
        """Test parsing an OTC SPL file."""
        if not self.sample_files['otc']:
            self.skipTest("No OTC sample files available")

        doc = self.parser.parse_file(str(self.sample_files['otc'][0]))

        self.assertIsInstance(doc, SPLDocument)
        self.assertIsNotNone(doc.spl.document_id.root)
        self.assertIn(doc.spl.document_type, ['otc', 'unknown'])

    def test_parse_prescription_file(self):
        """Test parsing a prescription SPL file."""
        if not self.sample_files['prescription']:
            self.skipTest("No prescription sample files available")

        doc = self.parser.parse_file(str(self.sample_files['prescription'][0]))

        self.assertIsInstance(doc, SPLDocument)
        self.assertIn(doc.spl.document_type, ['prescription', 'unknown'])

    def test_parse_other_file(self):
        """Test parsing an 'other' category SPL file."""
        if not self.sample_files['other']:
            self.skipTest("No 'other' sample files available")

        doc = self.parser.parse_file(str(self.sample_files['other'][0]))

        self.assertIsInstance(doc, SPLDocument)


class TestDocumentMetadata(unittest.TestCase):
    """Test document metadata extraction."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
        else:
            cls.doc = None

    def test_document_id_extraction(self):
        """Test document ID is extracted."""
        if self.doc is None:
            self.skipTest("No sample files available")

        self.assertIsNotNone(self.doc.spl.document_id)
        # Document ID root should be a UUID-like string
        if self.doc.spl.document_id.root:
            self.assertRegex(
                self.doc.spl.document_id.root,
                r'^[a-f0-9-]+$',
                "Document ID should be UUID format"
            )

    def test_set_id_extraction(self):
        """Test set ID is extracted."""
        if self.doc is None:
            self.skipTest("No sample files available")

        self.assertIsNotNone(self.doc.spl.set_id)

    def test_version_number_extraction(self):
        """Test version number is extracted as integer."""
        if self.doc is None:
            self.skipTest("No sample files available")

        if self.doc.spl.version_number is not None:
            self.assertIsInstance(self.doc.spl.version_number, int)
            self.assertGreater(self.doc.spl.version_number, 0)

    def test_effective_time_format(self):
        """Test effective time is in expected format."""
        if self.doc is None:
            self.skipTest("No sample files available")

        if self.doc.spl.effective_time:
            # Should be YYYYMMDD or YYYYMMDDHHMMSS
            self.assertRegex(
                self.doc.spl.effective_time,
                r'^\d{8}(\d{6})?$',
                "Effective time should be YYYYMMDD format"
            )

    def test_title_extraction(self):
        """Test title is extracted."""
        if self.doc is None:
            self.skipTest("No sample files available")

        # Title might be None for some documents, but shouldn't crash
        if self.doc.spl.title:
            self.assertIsInstance(self.doc.spl.title, str)


class TestLabelerExtraction(unittest.TestCase):
    """Test labeler/organization extraction."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
        else:
            cls.doc = None

    def test_labeler_name_extraction(self):
        """Test labeler name is extracted."""
        if self.doc is None:
            self.skipTest("No sample files available")

        if self.doc.labeler.name:
            self.assertIsInstance(self.doc.labeler.name, str)
            self.assertGreater(len(self.doc.labeler.name), 0)

    def test_org_ids_extraction(self):
        """Test organization IDs are extracted."""
        if self.doc is None:
            self.skipTest("No sample files available")

        self.assertIsInstance(self.doc.labeler.org_ids, list)

        for org_id in self.doc.labeler.org_ids:
            # Each should have at least root or extension
            self.assertTrue(
                org_id.root is not None or org_id.extension is not None,
                "Org ID should have root or extension"
            )


class TestProductExtraction(unittest.TestCase):
    """Test product extraction."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        cls.docs = []
        for f in xml_files[:5]:  # Test first 5 files
            try:
                cls.docs.append(cls.parser.parse_file(str(f)))
            except Exception:
                pass

    def test_products_extracted(self):
        """Test that products are extracted from files."""
        products_found = 0
        for doc in self.docs:
            products_found += len(doc.products)

        self.assertGreater(products_found, 0, "Should extract at least one product")

    def test_product_name_present(self):
        """Test product names are extracted."""
        for doc in self.docs:
            for product in doc.products:
                if product.product_name:
                    self.assertIsInstance(product.product_name, str)

    def test_ndc_format(self):
        """Test NDC codes are in correct format."""
        ndc_pattern = r'^\d{4,5}-\d{3,4}(-\d{1,2})?$'

        for doc in self.docs:
            for product in doc.products:
                for ndc in product.ndc.product_ndcs:
                    self.assertRegex(ndc, ndc_pattern, f"Invalid product NDC: {ndc}")
                for ndc in product.ndc.package_ndcs:
                    self.assertRegex(ndc, ndc_pattern, f"Invalid package NDC: {ndc}")

    def test_ingredients_have_names(self):
        """Test that extracted ingredients have names."""
        for doc in self.docs:
            for product in doc.products:
                for ingredient in product.ingredients:
                    self.assertIsNotNone(ingredient.name)
                    self.assertIsInstance(ingredient.name, str)

    def test_ingredient_roles(self):
        """Test ingredient roles are valid."""
        valid_roles = {'active', 'inactive', 'other'}

        for doc in self.docs:
            for product in doc.products:
                for ingredient in product.ingredients:
                    self.assertIn(ingredient.role, valid_roles)

    def test_unii_format(self):
        """Test UNII codes are in correct format (10 alphanumeric chars)."""
        unii_pattern = r'^[A-Z0-9]{10}$'

        for doc in self.docs:
            for product in doc.products:
                for ingredient in product.ingredients:
                    if ingredient.unii:
                        self.assertRegex(
                            ingredient.unii,
                            unii_pattern,
                            f"Invalid UNII: {ingredient.unii}"
                        )


class TestSectionExtraction(unittest.TestCase):
    """Test section extraction."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('prescription_*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
        else:
            cls.doc = None

    def test_sections_extracted(self):
        """Test that sections are extracted."""
        if self.doc is None:
            self.skipTest("No prescription sample files available")

        self.assertGreater(len(self.doc.sections), 0)

    def test_section_codes_present(self):
        """Test section codes are extracted."""
        if self.doc is None:
            self.skipTest("No prescription sample files available")

        sections_with_codes = [s for s in self.doc.sections if s.code]
        self.assertGreater(len(sections_with_codes), 0)

    def test_section_text_extraction(self):
        """Test section text is extracted."""
        if self.doc is None:
            self.skipTest("No prescription sample files available")

        sections_with_text = [s for s in self.doc.sections if s.text_plain]
        self.assertGreater(len(sections_with_text), 0)

    def test_xhtml_preserved(self):
        """Test XHTML is preserved in text_xhtml field."""
        if self.doc is None:
            self.skipTest("No prescription sample files available")

        for section in self.doc.sections:
            if section.text_xhtml:
                # Should contain HTML-like tags
                self.assertIn('<', section.text_xhtml)
                self.assertIn('>', section.text_xhtml)

    def test_plain_text_normalized(self):
        """Test plain text has normalized whitespace."""
        if self.doc is None:
            self.skipTest("No prescription sample files available")

        for section in self.doc.sections:
            if section.text_plain:
                # Should not have excessive whitespace
                self.assertNotIn('  ', section.text_plain.strip())
                self.assertNotIn('\n\n', section.text_plain)


class TestDerivedFields(unittest.TestCase):
    """Test derived field computation."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        cls.docs = []
        for f in xml_files:
            try:
                cls.docs.append(cls.parser.parse_file(str(f)))
            except Exception:
                pass

    def test_merge_keys_present(self):
        """Test merge keys are generated."""
        for doc in self.docs:
            self.assertIsNotNone(doc.derived.merge_keys)
            self.assertIsInstance(doc.derived.merge_keys.primary, list)
            self.assertIsInstance(doc.derived.merge_keys.secondary, list)

    def test_section_presence_flags(self):
        """Test section presence flags are computed."""
        # At least some documents should have indications
        has_indications = any(
            doc.derived.section_presence_flags.indications_and_usage
            for doc in self.docs
        )
        self.assertTrue(has_indications, "At least one doc should have indications")

        # At least some should have warnings
        has_warnings = any(
            doc.derived.section_presence_flags.warnings_and_precautions
            for doc in self.docs
        )
        self.assertTrue(has_warnings, "At least one doc should have warnings")


class TestKnowledgeGraph(unittest.TestCase):
    """Test knowledge graph generation."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
            cls.kg = cls.parser.to_knowledge_graph(cls.doc)
        else:
            cls.doc = None
            cls.kg = None

    def test_kg_entities_created(self):
        """Test KG entities are created."""
        if self.kg is None:
            self.skipTest("No sample files available")

        self.assertGreater(len(self.kg.entities), 0)

    def test_kg_edges_created(self):
        """Test KG edges are created."""
        if self.kg is None:
            self.skipTest("No sample files available")

        self.assertGreater(len(self.kg.edges), 0)

    def test_entity_types(self):
        """Test expected entity types are present."""
        if self.kg is None:
            self.skipTest("No sample files available")

        entity_types = {e.entity_type for e in self.kg.entities}

        # Should have at least label_version
        self.assertIn('label_version', entity_types)

    def test_edge_types(self):
        """Test expected edge types are present."""
        if self.kg is None:
            self.skipTest("No sample files available")

        edge_types = {e.edge_type for e in self.kg.edges}

        # Should have some edges
        self.assertGreater(len(edge_types), 0)

    def test_kg_to_dict(self):
        """Test KG can be serialized to dict."""
        if self.kg is None:
            self.skipTest("No sample files available")

        kg_dict = self.kg.to_dict()
        self.assertIn('entities', kg_dict)
        self.assertIn('edges', kg_dict)

        # Should be JSON serializable
        json_str = json.dumps(kg_dict)
        self.assertIsInstance(json_str, str)


class TestJSONSerialization(unittest.TestCase):
    """Test JSON serialization."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
        else:
            cls.doc = None

    def test_to_dict(self):
        """Test document can be converted to dict."""
        if self.doc is None:
            self.skipTest("No sample files available")

        doc_dict = self.doc.to_dict()
        self.assertIsInstance(doc_dict, dict)
        self.assertIn('source', doc_dict)
        self.assertIn('spl', doc_dict)
        self.assertIn('products', doc_dict)

    def test_json_serializable(self):
        """Test document can be serialized to JSON."""
        if self.doc is None:
            self.skipTest("No sample files available")

        doc_dict = self.doc.to_dict()
        json_str = json.dumps(doc_dict)
        self.assertIsInstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        self.assertEqual(parsed['source']['dataset'], 'DailyMed')

    def test_no_private_fields_in_output(self):
        """Test private fields (starting with _) are not in output."""
        if self.doc is None:
            self.skipTest("No sample files available")

        doc_dict = self.doc.to_dict()
        json_str = json.dumps(doc_dict)

        # Should not contain _xpath or other private fields as keys
        self.assertNotIn('"_xpath":', json_str)
        self.assertNotIn('"_provenance":', json_str)

        # Check that dataclass private fields are stripped
        for product in doc_dict.get('products', []):
            self.assertNotIn('_xpath', product)
        for section in doc_dict.get('sections', []):
            self.assertNotIn('_xpath', section)


class TestRobustness(unittest.TestCase):
    """Test parser robustness with edge cases."""

    def test_parse_all_sample_files_without_crash(self):
        """Test all sample files can be parsed without crashing."""
        parser = SPLParser()
        xml_dir = Path(__file__).parent / 'xml_sample'

        errors = []
        for xml_file in xml_dir.glob('*.xml'):
            try:
                doc = parser.parse_file(str(xml_file))
                self.assertIsNotNone(doc)
            except Exception as e:
                errors.append(f"{xml_file.name}: {e}")

        if errors:
            self.fail(f"Parsing errors:\n" + "\n".join(errors))

    def test_empty_fields_handled(self):
        """Test empty/missing fields don't cause crashes."""
        parser = SPLParser()
        xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(xml_dir.glob('*.xml'))

        for xml_file in xml_files:
            doc = parser.parse_file(str(xml_file))

            # All these should exist and not crash
            _ = doc.spl.document_id.root
            _ = doc.spl.set_id.root
            _ = doc.spl.version_number
            _ = doc.spl.title
            _ = doc.labeler.name
            _ = doc.products
            _ = doc.sections

    def test_unicode_handling(self):
        """Test unicode characters are handled properly."""
        parser = SPLParser()
        xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(xml_dir.glob('*.xml'))

        for xml_file in xml_files:
            doc = parser.parse_file(str(xml_file))
            doc_dict = doc.to_dict()

            # Should be able to JSON encode (tests unicode handling)
            json_str = json.dumps(doc_dict, ensure_ascii=False)
            self.assertIsInstance(json_str, str)


class TestDirectoryParsing(unittest.TestCase):
    """Test directory parsing functionality."""

    def test_parse_directory(self):
        """Test parsing entire directory."""
        parser = SPLParser()
        xml_dir = Path(__file__).parent / 'xml_sample'

        if not xml_dir.exists():
            self.skipTest("xml_sample directory not found")

        docs = parser.parse_directory(str(xml_dir))
        self.assertGreater(len(docs), 0)

    def test_parse_directory_with_output(self):
        """Test parsing directory with output files."""
        parser = SPLParser()
        xml_dir = Path(__file__).parent / 'xml_sample'

        if not xml_dir.exists():
            self.skipTest("xml_sample directory not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = parser.parse_directory(str(xml_dir), output_dir=tmpdir)

            # Check output files were created
            output_files = list(Path(tmpdir).glob('*.json'))
            self.assertEqual(len(output_files), len(docs))


class TestSchemaCompliance(unittest.TestCase):
    """Test output complies with specified schema."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SPLParser()
        cls.xml_dir = Path(__file__).parent / 'xml_sample'
        xml_files = list(cls.xml_dir.glob('*.xml'))
        if xml_files:
            cls.doc = cls.parser.parse_file(str(xml_files[0]))
            cls.doc_dict = cls.doc.to_dict()
        else:
            cls.doc = None
            cls.doc_dict = None

    def test_source_schema(self):
        """Test source field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        source = self.doc_dict['source']
        self.assertEqual(source['dataset'], 'DailyMed')
        self.assertEqual(source['format'], 'SPL')
        self.assertIn('input_filename', source)
        self.assertIn('parsed_at', source)
        self.assertIn('parser_version', source)

    def test_spl_schema(self):
        """Test spl field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        spl = self.doc_dict['spl']
        self.assertIn('document_id', spl)
        self.assertIn('set_id', spl)
        self.assertIn('version_number', spl)
        self.assertIn('effective_time', spl)
        self.assertIn('title', spl)
        self.assertIn('document_type', spl)

    def test_labeler_schema(self):
        """Test labeler field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        labeler = self.doc_dict['labeler']
        self.assertIn('name', labeler)
        self.assertIn('org_ids', labeler)
        self.assertIsInstance(labeler['org_ids'], list)

    def test_products_schema(self):
        """Test products field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        products = self.doc_dict['products']
        self.assertIsInstance(products, list)

        for product in products:
            self.assertIn('product_name', product)
            self.assertIn('routes', product)
            self.assertIn('dosage_forms', product)
            self.assertIn('ndc', product)
            self.assertIn('regulatory', product)
            self.assertIn('ingredients', product)
            self.assertIn('packages', product)

    def test_sections_schema(self):
        """Test sections field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        sections = self.doc_dict['sections']
        self.assertIsInstance(sections, list)

        for section in sections:
            self.assertIn('code_system', section)
            self.assertIn('code', section)
            self.assertIn('display', section)
            self.assertIn('title', section)
            self.assertIn('text_xhtml', section)
            self.assertIn('text_plain', section)

    def test_derived_schema(self):
        """Test derived field complies with schema."""
        if self.doc_dict is None:
            self.skipTest("No sample files available")

        derived = self.doc_dict['derived']
        self.assertIn('merge_keys', derived)
        self.assertIn('section_presence_flags', derived)

        merge_keys = derived['merge_keys']
        self.assertIn('primary', merge_keys)
        self.assertIn('secondary', merge_keys)

        flags = derived['section_presence_flags']
        self.assertIn('boxed_warning', flags)
        self.assertIn('indications_and_usage', flags)
        self.assertIn('contraindications', flags)
        self.assertIn('warnings_and_precautions', flags)
        self.assertIn('storage_and_handling', flags)


if __name__ == '__main__':
    unittest.main(verbosity=2)
