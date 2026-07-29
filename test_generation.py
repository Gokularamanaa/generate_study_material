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
            "duration": 2,
            "pedagogy": [
                "Concept Mapping",
                "Problem-Based Learning",
                "Case Study"
            ]
        },
        {
            "topic_name": "UDP",
            "duration": 1,
            "pedagogy": [
                "Interactive Lecture",
                "Think-Pair-Share"
            ]
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

## 5. Pedagogy-Driven Activities
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

## 5. Pedagogy-Driven Activities
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

    @patch("study_material_module.main.generate_study_material_for_topic_async")
    @patch("study_material_module.main.asyncio.sleep", new_callable=AsyncMock)
    def test_generate_endpoint_mocked(self, mock_sleep, mock_generate):
        """
        Runs the topic-level API pipeline with mocked LLM API calls.
        Validates per-topic PDF compilation, course output folder creation, and response structure.
        """
        def mock_generate_side_effect(prompt, model_name=None):
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

        udp_res = json_data["topic_results"][1]
        self.assertEqual(udp_res["topic_name"], "UDP")
        self.assertEqual(udp_res["status"], "success")

        # Verify PDF file exists
        pdf_full_path = OUTPUT_DIR.parent / json_data["pdf_path"]
        self.assertTrue(pdf_full_path.exists(), f"PDF file {pdf_full_path} does not exist.")

        # Verify PDF contents using pypdf
        from pypdf import PdfReader
        reader = PdfReader(pdf_full_path)
        pdf_text = "\n".join([page.extract_text() for page in reader.pages])

        self.assertIn("Computer Networks", pdf_text)
        self.assertIn("CS3591", pdf_text)
        self.assertIn("Transport Layer", pdf_text)
        self.assertIn("TCP", pdf_text)
        self.assertIn("UDP", pdf_text)
        self.assertIn("Practice Questions", pdf_text)

        print("\n[Mocked Topic Test Pass] Generated combined Topic PDF exists and was verified!")

    @patch("study_material_module.main.generate_study_material_for_topic_async")
    @patch("study_material_module.main.asyncio.sleep", new_callable=AsyncMock)
    def test_topic_failure_resilience(self, mock_sleep, mock_generate):
        """
        Validates that if Topic 1 (TCP) fails, Topic 2 (UDP) still succeeds and generates the PDF.
        """
        def mock_generate_side_effect(prompt, model_name=None):
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

    def test_prompt_builder_pedagogy_integration(self):
        """
        Validates that build_topic_prompt correctly incorporates 12 sections and pedagogy strategies.
        """
        prompt = build_topic_prompt(
            subject_name="Computer Networks",
            course_code="CS3591",
            unit_number=2,
            unit_title="Transport Layer",
            topic_name="TCP",
            duration=2,
            pedagogy=["Concept Mapping", "Problem-Based Learning", "Case Study"]
        )

        self.assertIn("Concept Mapping Integration", prompt)
        self.assertIn("Problem-Based Learning Integration", prompt)
        self.assertIn("Case Study Integration", prompt)
        self.assertIn("## 1. Learning Outcomes", prompt)
        self.assertIn("## 2. Introduction", prompt)
        self.assertIn("## 3. Core Theory", prompt)
        self.assertIn("## 4. Visual Learning", prompt)
        self.assertIn("## 5. Pedagogy-Driven Activities", prompt)
        self.assertIn("## 6. Real-World Applications", prompt)
        self.assertIn("## 7. Industry Perspective", prompt)
        self.assertIn("## 8. Interview Preparation", prompt)
        self.assertIn("## 9. Laboratory Exercises", prompt)
        self.assertIn("## 10. Practice Questions", prompt)
        self.assertIn("## 11. Summary", prompt)
        self.assertIn("## 12. Further Learning", prompt)
        self.assertIn("15 Multiple Choice Questions (MCQs)", prompt)
        self.assertIn("10 Two-Mark Questions", prompt)
        self.assertIn("10 Five-Mark Questions", prompt)
        self.assertIn("5 Ten-Mark University Questions", prompt)
        self.assertIn("15 Viva Questions", prompt)

    def test_prompt_builder_images_and_hands_on(self):
        """
        Validates that build_topic_prompt properly handles 'diagram-based learning' and 'hands-on'.
        """
        prompt = build_topic_prompt(
            subject_name="Database Systems",
            course_code="CS3492",
            unit_number=1,
            unit_title="Relational Model",
            topic_name="B-Tree Indexing",
            duration=3,
            pedagogy=["diagram-based learning", "hands-on learning"]
        )

        self.assertIn("Diagram-Based & Visual Learning Integration", prompt)
        self.assertIn("Diagram-Based & Visual Learning Module", prompt)
        self.assertIn("Hands-On Learning Integration", prompt)
        self.assertIn("Hands-On Laboratory Activity", prompt)
        self.assertIn("B-Tree Indexing", prompt)

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
        Validates transformation of markdown images and Mermaid blocks into HTML image containers with Data URIs.
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
        self.assertIn('<div class="image-box"><img src="data:image/', cleaned)
        self.assertIn('alt="Figure 1: TCP Handshake"', cleaned)
        self.assertIn('<p class="figure-caption">Figure 1: TCP Handshake</p>', cleaned)
        self.assertIn('Visual System Architecture Diagram</p>', cleaned)

        # Test SVG fallback generator directly
        fallback_uri = generate_fallback_svg_data_uri("TCP State Diagram", "TCP")
        self.assertTrue(fallback_uri.startswith("data:image/svg+xml;base64,"))

    def test_auto_image_injection_when_missing(self):
        """
        Validates auto-injection of topic image when LLM output lacks image tags.
        """
        from study_material_module.pdf_generator import clean_markdown_for_pdf

        sample = """# Topic: B-Tree Indexing
## 3. Core Theory
Exhaustive theory.
## 4. Visual Learning
Explanation.
"""
        cleaned = clean_markdown_for_pdf(sample, topic_name="B-Tree Indexing")
        self.assertIn('<div class="image-box"><img src="data:image/', cleaned)
        self.assertIn('B-Tree Indexing Architectural & System Diagram', cleaned)


if __name__ == "__main__":
    unittest.main()

