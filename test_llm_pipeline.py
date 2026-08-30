"""
Comprehensive test script for LLM4AE app AI annotation and prompts alignment
"""

import os
import sys
import unittest

# Add server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from llm_prompts import (
    ANNOTATION_GUIDE,
    ANNOTATION_GUIDE_VAERS,
    P2_TAG,
    P2_TAG_VAERS,
    P1_JSON,
    P1_JSON_VAERS,
    TAG_TO_LABEL,
    RAW_TO_LABEL,
    FAERS_TAGS,
    VAERS_TAGS,
)
from llm_annotation import (
    parse_tagged_output,
    build_boundary_map,
    map_predicted_spans_to_original,
    _extract_json_spans,
    sanitize_model_output,
    clean_span,
    normalize_label,
)
from ai_client import AIClient


class TestLLM4AEAppSync(unittest.TestCase):

    def test_schema_definitions(self):
        """Test that FAERS 17 categories and VAERS 14 categories exist in TAG_TO_LABEL."""
        # FAERS 17 categories
        expected_faers = {
            "SDRUG", "CDRUG", "ODRUG", "DOSE", "IND", "TREATMENT", "AE", "MAE",
            "DX", "LAB", "STATUS", "RO", "COD", "MHX", "FHX", "AGE", "SEX"
        }
        self.assertTrue(expected_faers.issubset(FAERS_TAGS))
        for tag in expected_faers:
            self.assertIn(tag, TAG_TO_LABEL)

        # VAERS 14 categories
        expected_vaers = {
            "SYM", "SDX", "PDX", "DX", "VAX", "MHX", "FHX", "LAB",
            "TEMPO", "DOSE", "STATUS", "TX", "AGE", "SEX"
        }
        self.assertTrue(expected_vaers.issubset(VAERS_TAGS))
        for tag in expected_vaers:
            self.assertIn(tag, TAG_TO_LABEL)

    def test_prompts_contain_required_tags_and_rules(self):
        """Test that P2_TAG and P2_TAG_VAERS include guidelines and proper instructions."""
        self.assertIn("sDrug", P2_TAG)
        self.assertIn("AE", P2_TAG)
        self.assertIn("<SDRUG>", P2_TAG)
        self.assertIn("<AE>", P2_TAG)

        self.assertIn("VAX", P2_TAG_VAERS)
        self.assertIn("<VAX>", P2_TAG_VAERS)
        self.assertIn("<SYM>", P2_TAG_VAERS)

        self.assertIn("JSON", P1_JSON.upper())
        self.assertIn("JSON", P1_JSON_VAERS.upper())

    def test_tagged_output_parsing_and_boundary_mapping(self):
        """Test XML tag extraction with case insensitivity and exact character offset mapping."""
        narrative = "A 64-year-old female patient took atenolol 50 mg daily for hypertension and developed severe acute pancreatitis."
        tagged_output = """```xml
A <AGE>64-year-old</AGE> <SEX>female</SEX> patient took <sDrug>atenolol</sDrug> <dose>50 mg daily</dose> for <ind>hypertension</ind> and developed <AE>severe acute pancreatitis</AE>.
```"""
        sanitized = sanitize_model_output(tagged_output)
        clean_text, parsed_spans, warnings = parse_tagged_output(sanitized)
        
        self.assertEqual(len(parsed_spans), 6)
        mapped_spans, meta = map_predicted_spans_to_original(clean_text, parsed_spans, narrative)
        
        self.assertEqual(len(mapped_spans), 6)
        
        # Verify exact character extraction from original narrative
        for sp in mapped_spans:
            extracted = narrative[sp["start"]:sp["end"]]
            self.assertEqual(extracted, sp["text"])

        # Check specific spans
        age_span = next(s for s in mapped_spans if s["label"] == "Age")
        self.assertEqual(age_span["text"], "64-year-old")

        sex_span = next(s for s in mapped_spans if s["label"] == "Sex")
        self.assertEqual(sex_span["text"], "female")

        sdrug_span = next(s for s in mapped_spans if s["label"] == "sDrug")
        self.assertEqual(sdrug_span["text"], "atenolol")

        dose_span = next(s for s in mapped_spans if s["label"] == "Dose")
        self.assertEqual(dose_span["text"], "50 mg daily")

        ind_span = next(s for s in mapped_spans if s["label"] == "IND")
        self.assertEqual(ind_span["text"], "hypertension")

        ae_span = next(s for s in mapped_spans if s["label"] == "AE")
        self.assertEqual(ae_span["text"], "severe acute pancreatitis")

    def test_vaers_tagged_output(self):
        """Test VAERS schema tagged output parsing."""
        narrative = "The 35 yo male received COVID-19 vaccine and reported chest tightness 2 hours post-vaccination."
        tagged_output = "<AGE>35 yo</AGE> <SEX>male</SEX> received <VAX>COVID-19 vaccine</VAX> and reported <SYM>chest tightness</SYM> <TEMPO>2 hours post-vaccination</TEMPO>."
        
        clean_text, parsed_spans, warnings = parse_tagged_output(tagged_output)
        mapped_spans, meta = map_predicted_spans_to_original(clean_text, parsed_spans, narrative)
        
        self.assertEqual(len(mapped_spans), 5)
        for sp in mapped_spans:
            self.assertEqual(narrative[sp["start"]:sp["end"]], sp["text"])

        vax_span = next(s for s in mapped_spans if s["label"] == "VAX")
        self.assertEqual(vax_span["text"], "COVID-19 vaccine")

        tempo_span = next(s for s in mapped_spans if s["label"] == "TEMPO")
        self.assertEqual(tempo_span["text"], "2 hours post-vaccination")

    def test_json_span_extraction(self):
        """Test JSON output parser and offset validation."""
        narrative = "Patient was prescribed Lisinopril for high blood pressure."
        json_output = """```json
{
  "spans": [
    {"label": "sDrug", "start": 23, "end": 33, "text": "Lisinopril"},
    {"label": "IND", "start": 38, "end": 57, "text": "high blood pressure"}
  ]
}
```"""
        spans = _extract_json_spans(json_output, narrative)
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0]["text"], "Lisinopril")
        self.assertEqual(spans[0]["label"], "sDrug")
        self.assertEqual(spans[1]["text"], "high blood pressure")
        self.assertEqual(spans[1]["label"], "IND")

    def test_ai_client_providers(self):
        """Test AIClient provider initialization for OpenAI/vLLM, Elsa (Claude 4.6 Sonnet), Gemini."""
        # Test vllm/openai provider
        client_openai = AIClient(provider="openai")
        self.assertEqual(client_openai.provider, "openai")

        # Test Elsa / Sonnet 4.6 routing
        try:
            client_sonnet = AIClient(provider="sonnet")
            self.assertEqual(client_sonnet.provider, "sonnet")
            self.assertEqual(client_sonnet.model_name, "CLAUDE_46_SONNET")
        except ValueError as e:
            # Expected if ELSA credentials are not configured in test environment
            self.assertTrue("ELSA_API_NAME" in str(e) or "ELSA_MODEL_ID" in str(e))


if __name__ == '__main__':
    unittest.main()
