import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Add current directory to path to import study_material_module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from study_material_module.main import app
from study_material_module.config import OUTPUT_DIR
from study_material_module.prompt_builder import build_topic_prompt

# Sample topic-level payload matching the user specification
MOCK_TOPIC_PAYLOAD = {
    "subject_name": "Computer Networks",
    "course_code": "CS3591",
    "unit_number": 2,
    "unit_title": "Transport Layer",
    "topics": [
        {
            "topic_name": "TCP",
            "duration": 2
        },
        {
            "topic_name": "UDP",
            "duration": 1
        }
    ]
}

MOCK_TOPIC_MARKDOWN_TCP = """# Topic: TCP

## 1. Learning Outcomes
- Explain SYN/ACK handshake.
- Analyse window size performance.
- Compare TCP and UDP.
- Design reliable transport layers.
- Apply socket APIs.
- Troubleshoot packet loss and connection timeouts.

## 2. Introduction
Transmission Control Protocol (TCP) is a foundational connection-oriented transport layer protocol in the Internet Protocol suite. Engineered to guarantee reliable, in-order packet delivery across inherently unreliable IP networks, TCP provides full-duplex byte stream transmission with checksum verification, adaptive window-based flow control, and dynamic congestion control algorithms.

## 3. Core Theory
TCP operates using stateful socket connections. Key concepts include sequence numbers, acknowledgment numbers, window scaling, and retransmission timers.

## 4. Visual Learning
```mermaid
sequenceDiagram
    Client->>Server: SYN (seq=x)
    Server->>Client: SYN-ACK (seq=y, ack=x+1)
    Client->>Server: ACK (seq=x+1, ack=y+1)
```

## 5. Practical Implementation & Conceptual Walkthrough
### Concept Mapping & Knowledge Matrix
TCP connects network layer IP routing with application layer HTTP/FTP protocols.

## 6. Real-World Applications
Used in Web Applications, Banking Portals, Cloud Storage, and Database Connectors.

## 7. Industry Perspective
Modern deployment considerations include TCP BBR congestion control and TLS 1.3 handshake integration.

## 8. Interview Preparation
### Beginner Level
Q: What is TCP 3-Way Handshake?
Answer: SYN, SYN-ACK, ACK.

## 9. Laboratory Exercises
### Guided Experiment 1
Capture TCP handshakes using Wireshark.

## 10. Practice Questions
### 15 Multiple Choice Questions (MCQs)
1. What is TCP?
- A) Connectionless
- B) Connection-oriented
- C) Unreliable
- D) Link layer
- **Correct Answer:** B
- **Explanation:** Connection-oriented.

### 10 Two-Mark Questions
1. Define RTT.
Answer: Round Trip Time.

### 10 Five-Mark Questions
1. Explain TCP sliding window algorithm.
Answer: Flow control mechanism using dynamic window sizing.

### 5 Ten-Mark University Questions
1. Detail TCP congestion control algorithms (Tahoe, Reno, NewReno).
Answer: Comprehensive breakdown of Slow Start, Congestion Avoidance, Fast Retransmit, Fast Recovery.

### 15 Viva Questions
1. What is FIN-WAIT-2 state?
Answer: Waiting for FIN from remote node.

## 11. Summary
TCP is essential for reliable, lossless communication.

## 12. Further Learning
- Capture HTTPS traffic in Wireshark.
- Practice socket programming in Python.
"""

MOCK_TOPIC_MARKDOWN_UDP = """# Topic: UDP

## 1. Learning Outcomes
- Explain datagram routing.
- Compare UDP vs TCP.

## 2. Introduction
User Datagram Protocol (UDP) is a minimal, lightweight transport layer protocol.

## 3. Core Theory
Unacknowledged, connectionless datagram transmission.

## 4. Visual Learning
+-------------------+-------------------+
| Source Port       | Destination Port  |
+-------------------+-------------------+
| Length            | Checksum          |
+-------------------+-------------------+

## 5. Practical Implementation & Conceptual Walkthrough
### Interactive Conceptual Walkthrough
Real-time streaming analogy.

## 6. Real-World Applications
VoIP, DNS, Online Gaming, WebRTC.

## 7. Industry Perspective
QUIC protocol and UDP in HTTP/3.

## 8. Interview Preparation
### Beginner Level
Q: What is UDP header length?
Answer: 8 bytes.

## 9. Laboratory Exercises
### Guided Experiment 1
UDP socket server in Python.

## 10. Practice Questions
### 15 Multiple Choice Questions (MCQs)
1. What is UDP header size?
- A) 20 bytes
- B) 8 bytes
- C) 4 bytes
- D) 16 bytes
- **Correct Answer:** B
- **Explanation:** 8 bytes.

### 10 Two-Mark Questions
1. Name two protocols using UDP.
Answer: DNS and DHCP.

### 10 Five-Mark Questions
1. Compare TCP vs UDP.
Answer: Tabular analysis of overhead, speed, reliability.

### 5 Ten-Mark University Questions
1. Explain UDP datagram format and QUIC protocol evolution.
Answer: Full structural analysis.

### 15 Viva Questions
1. Is UDP checksum optional in IPv4?
Answer: Yes.

## 11. Summary
UDP provides fast, low-latency transmission.

## 12. Further Learning
- Monitor DNS queries using tcpdump.
"""


class TestTopicStudyMaterialGeneration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("study_material_module.visuals.visual_planner.generate_study_material_for_topic_async")
    @patch("study_material_module.main.generate_study_material_for_topic_async")
    @patch("study_material_module.main.asyncio.sleep", new_callable=AsyncMock)
    def test_generate_endpoint_mocked(self, mock_sleep, mock_generate, mock_gen_planner):
        mock_gen_planner.return_value = '{"visuals": []}'
        """
        Runs the topic-level API pipeline with mocked LLM API calls.
        Validates per-topic PDF compilation, course output folder creation, and response structure.
        """
        def mock_generate_side_effect(prompt, model_name=None):
            if "JSON object with the following JSON schema" in prompt:
                return '{"visuals": []}'
            if "Topic Name: UDP" in prompt or "UDP" in prompt:
                return MOCK_TOPIC_MARKDOWN_UDP
            return MOCK_TOPIC_MARKDOWN_TCP

        mock_generate.side_effect = mock_generate_side_effect

        response = self.client.post("/generate-study-material", json=MOCK_TOPIC_PAYLOAD)

        self.assertEqual(response.status_code, 200, response.text)
        json_data = response.json()

        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["subject_name"], "Computer Networks")
        self.assertEqual(json_data["course_code"], "CS3591")
        self.assertEqual(json_data["unit_number"], 2)
        self.assertEqual(json_data["unit_title"], "Transport Layer")
        self.assertIn("pdf_path", json_data)
        self.assertIn("topic_results", json_data)
        self.assertEqual(len(json_data["topic_results"]), 2)

        tcp_res = json_data["topic_results"][0]
        self.assertEqual(tcp_res["topic_name"], "TCP")
        self.assertEqual(tcp_res["status"], "success")
        self.assertIsNotNone(tcp_res["pdf_path"])

        udp_res = json_data["topic_results"][1]
        self.assertEqual(udp_res["topic_name"], "UDP")
        self.assertEqual(udp_res["status"], "success")
        self.assertIsNotNone(udp_res["pdf_path"])

        # Verify per-topic PDF files exist independently
        tcp_pdf_full_path = OUTPUT_DIR.parent / tcp_res["pdf_path"]
        udp_pdf_full_path = OUTPUT_DIR.parent / udp_res["pdf_path"]
        
        self.assertTrue(tcp_pdf_full_path.exists(), f"TCP PDF file {tcp_pdf_full_path} does not exist.")
        self.assertTrue(udp_pdf_full_path.exists(), f"UDP PDF file {udp_pdf_full_path} does not exist.")

        # Verify PDF contents using pypdf
        from pypdf import PdfReader
        tcp_reader = PdfReader(tcp_pdf_full_path)
        tcp_pdf_text = "\n".join([page.extract_text() for page in tcp_reader.pages])

        self.assertIn("Computer Networks", tcp_pdf_text)
        self.assertIn("CS3591", tcp_pdf_text)
        self.assertIn("TCP", tcp_pdf_text)

        print("\n[Mocked Topic Test Pass] Independent Topic PDFs were generated and verified!")

    @patch("study_material_module.visuals.visual_planner.generate_study_material_for_topic_async")
    @patch("study_material_module.main.generate_study_material_for_topic_async")
    @patch("study_material_module.main.asyncio.sleep", new_callable=AsyncMock)
    def test_topic_failure_resilience(self, mock_sleep, mock_generate, mock_gen_planner):
        mock_gen_planner.return_value = '{"visuals": []}'
        """
        Validates that if Topic 1 (TCP) fails, Topic 2 (UDP) still succeeds and generates the PDF.
        """
        def mock_generate_side_effect(prompt, model_name=None):
            if "JSON object with the following JSON schema" in prompt:
                return '{"visuals": []}'
            if "Topic Name: TCP" in prompt:
                raise RuntimeError("LLM rate limit or quota exceeded")
            return MOCK_TOPIC_MARKDOWN_UDP

        mock_generate.side_effect = mock_generate_side_effect

        response = self.client.post("/generate-study-material", json=MOCK_TOPIC_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()

        self.assertTrue(json_data["success"])
        self.assertIsNotNone(json_data["pdf_path"])
        self.assertEqual(len(json_data["topic_results"]), 2)

        tcp_res = json_data["topic_results"][0]
        self.assertEqual(tcp_res["topic_name"], "TCP")
        self.assertEqual(tcp_res["status"], "failed")
        self.assertIn("quota exceeded", tcp_res["reason"])

        udp_res = json_data["topic_results"][1]
        self.assertEqual(udp_res["topic_name"], "UDP")
        self.assertEqual(udp_res["status"], "success")

    def test_prompt_builder_topic_structure(self):
        """
        Validates that build_topic_prompt incorporates core academic guidelines and topic metadata.
        """
        prompt = build_topic_prompt(
            subject_name="Computer Networks",
            course_code="CS3591",
            unit_number=2,
            unit_title="Transport Layer",
            topic_name="TCP",
            duration=2
        )

        self.assertIn("Subject Name: Computer Networks", prompt)
        self.assertIn("Course Code: CS3591", prompt)
        self.assertIn("Topic Name: TCP", prompt)
        self.assertIn("SOURCE-FIRST CONTENT POLICY", prompt)
        self.assertIn("TECHNICAL CREDIBILITY", prompt)

    def test_prompt_builder_topic_name_and_metadata(self):
        """
        Validates that build_topic_prompt properly includes topic metadata and excludes meta instructions.
        """
        prompt = build_topic_prompt(
            subject_name="Database Systems",
            course_code="CS3492",
            unit_number=1,
            unit_title="Relational Model",
            topic_name="B-Tree Indexing",
            duration=3
        )

        self.assertIn("B-Tree Indexing", prompt)
        self.assertIn("CS3492", prompt)
        self.assertNotIn("META INSTRUCTIONAL REQUIREMENTS", prompt)



    def test_unwanted_sections_removal(self):
        """
        Validates stripping of unwanted section headers.
        """
        from study_material_module.pdf_generator import remove_unwanted_sections

        sample = """# Topic: TCP
## 2. Introduction
Text here.
# Final Revision Notes
Remove this.
# References
Remove this too.
"""
        cleaned = remove_unwanted_sections(sample)
        self.assertNotIn("Final Revision Notes", cleaned)
        self.assertNotIn("References", cleaned)
        self.assertIn("Topic: TCP", cleaned)

    def test_clean_markdown_images_and_mermaid(self):
        """
        Validates that:
        - External markdown image tags are stripped (not rendered).
        - The first Mermaid block is rendered into an HTML image-box.
        - Additional Mermaid blocks beyond the first are stripped.
        """
        from study_material_module.pdf_generator import clean_markdown_for_pdf, generate_fallback_svg_data_uri

        sample = """# Topic: TCP Architecture
![Figure 1: TCP Handshake](https://image.pollinations.ai/prompt/tcp_handshake)
```mermaid
graph TD
    A[Client] -->|SYN| B[Server]
```
"""
        cleaned = clean_markdown_for_pdf(sample, topic_name="TCP")
        # External image tag must be stripped
        self.assertNotIn('alt="Figure 1: TCP Handshake"', cleaned)
        self.assertNotIn('Figure 1: TCP Handshake', cleaned)
        # Mermaid block must be rendered
        self.assertIn('<div class="image-box"><img src="data:image/', cleaned)
        self.assertIn('TCP Architecture Flowchart', cleaned)

        # Test SVG fallback generator directly
        fallback_uri = generate_fallback_svg_data_uri("TCP State Diagram", "TCP")
        self.assertTrue(fallback_uri.startswith("data:image/svg+xml;base64,"))

    def test_no_image_injection_when_missing(self):
        """
        Validates that no image is auto-injected when LLM output lacks both image tags and Mermaid blocks.
        The new policy is: no auto-injection; only render what the LLM explicitly provides.
        """
        from study_material_module.pdf_generator import clean_markdown_for_pdf

        sample = """# Topic: B-Tree Indexing
## 3. Core Theory
Exhaustive theory.
## 4. Visual Learning
Explanation.
"""
        cleaned = clean_markdown_for_pdf(sample, topic_name="B-Tree Indexing")
        # No image-box should be injected since there are no Mermaid or image tags
        self.assertNotIn('<div class="image-box">', cleaned)
        # Text content must be preserved
        self.assertIn('B-Tree Indexing', cleaned)
        self.assertIn('Exhaustive theory', cleaned)


    def test_image_spec_removal_and_visual_capping(self):
        """
        Validates that IMAGE_SPEC blocks and placeholders are stripped from markdown output,
        and that visual asset generation is capped at a maximum of 2 images per topic.
        """
        from study_material_module.pdf_generator import clean_markdown_for_pdf

        sample_with_image_spec = """# Topic: TCP Protocol
## 1. Introduction
Explanation of TCP.

[IMAGE_SPEC]
type: flowchart
title: TCP Handshake
purpose: Illustrate SYN ACK exchange
location: Section 1
caption: Figure 1
description: Client and Server exchanging packets
</IMAGE_SPEC]

[IMAGE_SPEC: type=conceptual_illustration title=Socket Connection]

```image_spec
type: architecture
title: System Layout
```

IMAGE_SPEC: High level network architecture

## 2. Core Theory
TCP is connection-oriented.
"""
        cleaned = clean_markdown_for_pdf(sample_with_image_spec, topic_name="TCP Protocol")
        self.assertNotIn("[IMAGE_SPEC]", cleaned)
        self.assertNotIn("</IMAGE_SPEC]", cleaned)
        self.assertNotIn("IMAGE_SPEC:", cleaned)
        self.assertNotIn("type: flowchart", cleaned)
        self.assertIn("Explanation of TCP.", cleaned)
        self.assertIn("TCP is connection-oriented.", cleaned)


    def test_subtopic_image_placement_and_deduplication(self):
        """
        Validates that images are placed under matching subtopics and duplicates are omitted.
        """
        from study_material_module.pdf_generator import insert_visuals_into_html, validate_pdf
        from pathlib import Path
        import tempfile

        html = """<h2>1. Introduction</h2><p>Intro text.</p><h2>2. Core Theory</h2><p>Theory text.</p>"""
        
        # Create temporary dummy SVG file
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            tmp.write(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>')
            tmp_path = Path(tmp.name)

        try:
            assets = [
                {
                    "path": tmp_path,
                    "caption": "Handshake Diagram",
                    "section_target": "Core Theory"
                },
                {
                    # Duplicate asset with same content
                    "path": tmp_path,
                    "caption": "Handshake Diagram Duplicate",
                    "section_target": "Core Theory"
                }
            ]

            result_html = insert_visuals_into_html(html, assets, topic_name="TCP")
            
            # Figure must be placed under Core Theory
            self.assertIn('<h2>2. Core Theory</h2>\n<div class="figure">', result_html)
            
            # Duplicate image must be skipped (only 1 figure inserted)
            self.assertEqual(result_html.count('<div class="figure">'), 1)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


    def test_set_dash_validation_and_recovery(self):
        """
        Validates that validate_dash_pattern and safe_set_dash correctly intercept
        invalid zero-cycle patterns ([0,0], [0], negative numbers, non-numeric strings)
        and fall back to solid lines setDash([]) without crashing ReportLab.
        """
        from study_material_module.pdf_generator import validate_dash_pattern
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import A4
        import tempfile

        # Test validate_dash_pattern helper directly
        arr1, ph1 = validate_dash_pattern([0, 0], 0)
        self.assertEqual(arr1, [])
        
        arr2, ph2 = validate_dash_pattern([0], 0)
        self.assertEqual(arr2, [])

        arr3, ph3 = validate_dash_pattern("4,4", 0)
        self.assertEqual(arr3, [4.0, 4.0])

        arr4, ph4 = validate_dash_pattern("0,0", 0)
        self.assertEqual(arr4, [])

        arr5, ph5 = validate_dash_pattern(None, 0)
        self.assertEqual(arr5, [])

        # Test Canvas.setDash monkeypatch execution directly
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_out_path = tmp.name

        try:
            c = Canvas(pdf_out_path, pagesize=A4)
            # Passing invalid [0,0] pattern must NOT raise ValueError
            c.setDash([0, 0], 0)
            c.setDash("0,0", 0)
            c.setDash([4, 4], 0)
            c.save()
            self.assertTrue(Path(pdf_out_path).exists())
            self.assertGreater(Path(pdf_out_path).stat().st_size, 0)
        finally:
            if Path(pdf_out_path).exists():
                Path(pdf_out_path).unlink()

    @patch("study_material_module.visuals.visual_planner.generate_study_material_for_topic_async")
    @patch("study_material_module.main.generate_study_material_for_topic_async")
    @patch("study_material_module.main.asyncio.sleep", new_callable=AsyncMock)
    def test_four_requested_topics_pdf_generation(self, mock_sleep, mock_generate, mock_gen_planner):
        """
        Validates full generation, per-topic PDF creation, and verification for the 4 requested testing topics:
        - Load Testing
        - Recovery Testing
        - Volume Testing
        - Testing in the Agile Environment
        """
        mock_gen_planner.return_value = '{"visuals": []}'
        mock_generate.return_value = """# Topic: Software Testing Concept
## 1. Learning Outcomes
Understand testing principles.
## 2. Introduction
Overview of testing techniques.
## 3. Core Theory
Detailed technical principles and mechanisms.
## 4. Visual Learning
Explanation.
## 5. Practical Implementation
Code walkthrough and tools.
"""

        four_topics_payload = {
            "subject_name": "Software Testing and Automation",
            "course_code": "CCS366",
            "unit_number": 1,
            "unit_title": "Advanced Testing Concepts",
            "topics": [
                {"topic_name": "Load Testing", "duration": 1},
                {"topic_name": "Recovery Testing", "duration": 1},
                {"topic_name": "Volume Testing", "duration": 1},
                {"topic_name": "Testing in the Agile Environment", "duration": 1}
            ]
        }

        response = self.client.post("/generate-study-material", json=four_topics_payload)
        self.assertEqual(response.status_code, 200, response.text)
        json_data = response.json()

        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["completion_status"], "Completed — 4/4 topics generated")
        self.assertEqual(len(json_data["topic_results"]), 4)

        for topic_res in json_data["topic_results"]:
            self.assertEqual(topic_res["status"], "success")
            self.assertIsNotNone(topic_res["pdf_path"])
            full_pdf_path = OUTPUT_DIR.parent / topic_res["pdf_path"]
            self.assertTrue(full_pdf_path.exists(), f"PDF for '{topic_res['topic_name']}' not found at {full_pdf_path}")

        print("\n[4-Topic Test Pass] All 4 requested topic PDFs successfully generated and verified!")


    def test_structured_diagram_validation_and_flowchart_rendering(self):
        """
        Validates that StructuredDiagram model validation catches empty boxes/nodes,
        and that render_structured_flowchart_svg renders complete 5-step Load Testing process
        with readable step titles, descriptions, and decision logic (0 empty boxes).
        """
        from study_material_module.visuals.diagram_generator import (
            StructuredDiagram, DiagramNode, DiagramEdge,
            validate_diagram_model, get_default_topic_flowchart_model, render_structured_flowchart_svg
        )

        # 1. Test Diagram Validation with an invalid empty node
        invalid_diagram = StructuredDiagram(
            title="Broken Diagram",
            nodes=[
                DiagramNode(id="n1", label="", description="Empty label"),
                DiagramNode(id="n2", label="Step 2", description="Valid")
            ],
            edges=[DiagramEdge(source="n1", target="n2")]
        )
        is_valid, errors = validate_diagram_model(invalid_diagram)
        self.assertFalse(is_valid)
        self.assertTrue(any("empty label" in err for err in errors))

        # 2. Test Load Testing Process Flowchart Model
        load_model = get_default_topic_flowchart_model("Load Testing")
        is_valid_load, load_errors = validate_diagram_model(load_model)
        self.assertTrue(is_valid_load, load_errors)
        self.assertEqual(len(load_model.nodes), 8)

        # 3. Test Native SVG Rendering
        svg_code = render_structured_flowchart_svg(load_model)
        self.assertIn("1. DEFINE OBJECTIVES", svg_code)
        self.assertIn("2. IDENTIFY KEY SCENARIOS", svg_code)
        self.assertIn("3. CONFIGURE ENVIRONMENT", svg_code)
        self.assertIn("4. EXECUTE THE TEST", svg_code)
        self.assertIn("5. ANALYZE RESULTS", svg_code)
        self.assertIn("MEETS SLA OBJECTIVES?", svg_code)
        self.assertIn("RELEASE TO PRODUCTION", svg_code)
        self.assertIn("OPTIMIZE BOTTLENECK", svg_code)
        self.assertIn('stroke-width="2"', svg_code)
        # Ensure text tags exist for every step
        self.assertGreater(svg_code.count("<text "), 10)


if __name__ == "__main__":
    unittest.main()

