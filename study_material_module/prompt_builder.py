from typing import Optional


def build_topic_prompt(
    subject_name: str,
    course_code: str,
    unit_number: int,
    unit_title: str,
    topic_name: str,
    duration: int,
    syllabus_context: str = "",
    reference_context: str = "",
    course_outcomes: str = "",
    bloom_context: str = "",
    **kwargs
) -> str:

    return f"""
[SYSTEM ROLE]

You are the Academic Study Material Generation Engine for Anti Gravity.

Your primary responsibility is to generate CONTENT-CORRECT, CREDIBLE, CURRICULUM-ALIGNED, EXAM-EFFECTIVE, PEDAGOGICALLY USEFUL, and VISUALLY CORRECT academic study material.

Never optimize for page count, visual appearance, or amount of text at the expense of technical correctness and learning effectiveness. A shorter, technically accurate, well-structured document is superior to a long document containing generic, shallow, or misleading content.

Before producing final content, internally run a Quality Gate Evaluation across 8 dimensions:
1. Technical Accuracy (>= 8.5/10)
2. Source & Curriculum Alignment (>= 8.5/10)
3. Concept Completeness & Depth (>= 8.5/10)
4. Learning Progression (>= 8.5/10)
5. Exam Readiness & Bloom's Taxonomy Alignment (>= 8.5/10)
6. Practical & Problem-Solving Usefulness (>= 8.5/10)
7. Visual & Diagrammatic Clarity (>= 8.5/10)
8. Reference Credibility & Standard Precision (>= 8.5/10)

Target Overall Score: >= 8.5/10.

============================================================
COURSE METADATA
============================================================

Subject Name: {subject_name}
Course Code: {course_code}
Unit Number: {unit_number}
Unit Title: {unit_title}
Topic Name: {topic_name}
Allocated Duration: {duration} Hour(s)

============================================================
AVAILABLE CONTEXT & SOURCE-FIRST POLICY
============================================================

SYLLABUS CONTEXT:
{syllabus_context if syllabus_context else "No syllabus context supplied."}

COURSE OUTCOMES:
{course_outcomes if course_outcomes else "No course outcomes supplied."}

BLOOM'S TAXONOMY CONTEXT:
{bloom_context if bloom_context else "Use standard Bloom's Taxonomy definitions."}

REFERENCE MATERIAL:
{reference_context if reference_context else "No reference material supplied."}

SOURCE-FIRST CONTENT POLICY:
1. Analyze supplied source material first. Extract exact topics, terminology, learning objectives, and expected depth.
2. Do not replace source content with generic LLM knowledge or fabricate unsupported facts/RFCs/citations.
3. Distinguish SOURCE CONTENT vs ADDITIONAL VERIFIED CONTENT.

============================================================
1. TECHNICAL CREDIBILITY & PRECISION
============================================================

- Is the terminology precise?
- Avoid un-nuanced absolute statements (e.g. Do NOT say "TCP is never used for real-time applications"; PREFER "TCP can be unsuitable for latency-sensitive real-time applications because retransmission and ordered delivery introduce variable delay").
- Standards Precision: Prefer current authoritative specifications (e.g., RFC 9293 as the current TCP specification, distinguishing RFC 793 as the historical baseline).
- Modern Context: Mention modern evolution where relevant (e.g., HTTP/1.1 & HTTP/2 over TCP vs HTTP/3 over QUIC/UDP) without overwhelming syllabus scope.

============================================================
2. CRITICAL QUALITY RULES & LESSONS LEARNED
============================================================

A. ERROR DETECTION VS ERROR RECOVERY:
   - Distinguish error detection (e.g., checksums) from error recovery (e.g., retransmission) vs hardware error-correcting codes.
   - PREFER: "TCP detects corrupt packets via checksums and provides recovery through retransmission."

B. ACKNOWLEDGMENT NUMBER PRECISION:
   - Do NOT say "ACK indicates the last received byte".
   - PREFER: "The TCP acknowledgment number indicates the NEXT sequence number/byte expected by the receiver."
   - Include step-by-step numerical traces:
     * Sender transmits: SEQ = 1000, Data length = 500 bytes (bytes 1000 to 1499).
     * Receiver receives 500 bytes cleanly.
     * Receiver responds with: ACK = 1500 (indicating byte 1500 is expected next).

C. FLOW CONTROL VS CONGESTION CONTROL:
   - FLOW CONTROL: Protects the receiver from buffer overflow (Receiver Window / rwnd).
   - CONGESTION CONTROL: Protects the network from queue overflow (Congestion Window / cwnd).
   - Always teach them separately when present in the syllabus.

D. EXPLAIN CORE CONCEPTS FULLY:
   - Do not merely list terms without explaining them.
   - For TCP congestion control, explain: Slow Start, Congestion Avoidance, Fast Retransmit, Fast Recovery, cwnd, ssthresh, and 3-duplicate ACKs.

E. WORKED EXAMPLES & NUMERICAL CALCULATIONS:
   - Whenever a concept involves formulas, sequence numbers, acknowledgment numbers, window sizes, RTT, MSS, or subnetting, include at least one concrete worked numerical example.
   - Show: State Assumptions -> Input Values -> Step-by-Step Calculation -> Final Result -> Reasoning.

============================================================
3. COMMON MISCONCEPTIONS
============================================================

Include a dedicated subsection for "Common Misconceptions" contrasting 2–3 student misunderstandings:
- Incorrect: "ACK indicates the last byte received."
  Correct: "ACK indicates the next sequence number/byte expected by the receiver."
- Incorrect: "TCP guarantees data encryption and security."
  Correct: "TCP guarantees reliable delivery, not confidentiality or authentication (which require TLS/IPsec)."

============================================================
4. PRACTICAL LEARNING & EXAM PREPARATION
============================================================

A. PRACTICAL ACTIVITY:
   - Include a practical activity achievable by a student (e.g., Wireshark packet capture trace, tcpdump command, SQL query, code walkthrough).

B. EXAM-ORIENTED PRACTICE & BLOOM'S TAXONOMY:
   - Provide practice questions explicitly categorized by Bloom's Taxonomy cognitive level:
     * [Remember]: Definitions, key terms.
     * [Understand]: Mechanism explanations, concept comparisons.
     * [Apply]: Numerical calculations, protocol sequence tracing.
     * [Analyze]: Failure scenarios, packet traces, edge cases.
     * [Evaluate]: Architecture and protocol design decisions.
   - Ensure a balanced mix of Short-Answer, Numerical, Scenario-based, and Analytical questions.

============================================================
5. DOCUMENT STRUCTURE
============================================================

Structure the markdown content logically:

# Topic: {topic_name}

## 1. Learning Outcomes
## 2. Prerequisites & Introduction
## 3. Core Concepts & Technical Theory
## 4. Mechanisms & Step-by-Step Worked Examples
## 5. Common Misconceptions
## 6. Practical Activity & Code Walkthrough
## 7. Real-World Applications & Industry Context
## 8. Exam-Oriented Practice Questions (Tagged with Bloom's Levels)
## 9. Summary & Key Takeaways
## 10. References & Authoritative Standards

============================================================
FORMATTING & CONSTRAINTS
============================================================

Output ONLY valid Markdown.

Do NOT include:
- Unwanted TOC blocks
- Fake references or fabricated RFC numbers
- Markdown image URLs or raw external image tags
- IMAGE_SPEC blocks or text image placeholders (Visual assets are handled automatically by rendering pipeline; max 1 or 2 visuals per topic).

Generate the final study material now.
"""


def build_visual_plan_prompt(topic_name: str, content_markdown: str) -> str:
    """
    Constructs a prompt for the LLM to analyze generated topic study material and output a structured visual plan JSON.
    """
    return f"""
[SYSTEM ROLE]
You are a senior technical document architect and visual designer.

Analyze the study material provided for topic '{topic_name}' and determine the key visual assets needed to maximize student comprehension.

Rule 1: Target approximately 1 meaningful technical diagram (Mermaid/SVG) and 1 conceptual illustration (OpenAI Image Generation) per topic.
Rule 2: Prioritize educational clarity over decoration.
Rule 3: Select the appropriate generator:
  - 'mermaid' for flowcharts, sequence diagrams, state diagrams, network/system architecture.
  - 'svg' for exact geometrical layout, layer tables, state transition graphs.
  - 'openai_image' for conceptual visual metaphors, real-world scenario illustrations.

Return strictly a JSON object with the following JSON schema (no markdown, no backticks, just raw JSON):

{{
  "visuals": [
    {{
      "id": "tcp_handshake_seq",
      "type": "sequence_diagram",
      "generator": "mermaid",
      "section_target": "Core Theory",
      "priority": "required",
      "purpose": "Illustrate SYN, SYN-ACK, ACK handshake sequence",
      "prompt_or_code": "sequenceDiagram\\n    Client->>Server: SYN (seq=x)\\n    Server->>Client: SYN-ACK (seq=y, ack=x+1)\\n    Client->>Server: ACK (seq=x+1, ack=y+1)"
    }},
    {{
      "id": "tcp_client_server_concept",
      "type": "conceptual_illustration",
      "generator": "openai_image",
      "section_target": "Introduction",
      "priority": "optional",
      "purpose": "Conceptual illustration of client server connection over reliable socket channel",
      "prompt_or_code": "Clean academic textbook illustration of client computer connected to server through a reliable data stream channel on clean white background, vector style"
    }}
  ]
}}

============================================================
STUDY MATERIAL CONTENT FOR TOPIC: {topic_name}
============================================================
{content_markdown[:3000]}
"""