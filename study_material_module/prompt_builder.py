from typing import List

def build_topic_prompt(
    subject_name: str,
    course_code: str,
    unit_number: int,
    unit_title: str,
    topic_name: str,
    duration: int,
    pedagogy: List[str]
) -> str:
    """
    Constructs the prompt to generate comprehensive, textbook + lab manual grade study material
    for a single topic across 12 mandatory sections, driven by pedagogy recommendations.
    """
    pedagogy_str = ", ".join(pedagogy) if pedagogy else "Standard University Academic Instruction"
    
    pedagogy_instructions = []
    pedagogy_modules = []

    # Process all requested pedagogies with flexible keyword matching
    for p in (pedagogy or []):
        p_lower = p.lower()
        if any(k in p_lower for k in ["diagram-based", "diagram based", "visual", "visualization", "image", "graphics", "diagram", "illustration", "figure"]):
            pedagogy_instructions.append(
                "- **Diagram-Based & Visual Learning Integration**: Generate vivid visual architecture diagrams, flowcharts, layer diagrams, network topology diagrams, sequence diagrams, and packet-flow illustrations using Mermaid (` ```mermaid `) code blocks and clean ASCII art."
            )
            pedagogy_modules.append(
                f"### Diagram-Based & Visual Learning Module\nProvide comprehensive Mermaid flowcharts (` ```mermaid `), ASCII architecture diagrams, layer interaction diagrams, and packet flow illustrations for {topic_name}, accompanied by labeled component interaction notes."
            )
        elif any(k in p_lower for k in ["concept mapping", "concept map", "mind map", "knowledge map", "dependency tree"]):
            pedagogy_instructions.append(
                "- **Concept Mapping Integration**: Incorporate explicit concept maps, relationship diagrams, dependency trees, knowledge maps, and structural connection matrices showing prerequisites and advanced topics."
            )
            pedagogy_modules.append(
                f"### Concept Mapping & Knowledge Matrix\nProvide a structured hierarchical concept map, dependency tree, and relationship matrix detailing how {topic_name} connects to prerequisites and real-world systems."
            )
        elif any(k in p_lower for k in ["hands-on", "hands on", "handson", "practical", "lab", "coding", "code", "exercise", "workshop"]):
            pedagogy_instructions.append(
                "- **Hands-On Learning Integration**: Include practical laboratory activities complete with Objective, Required Software/Tools (e.g. Wireshark, Packet Tracer, DevTools, Linux CLI, Postman/APIs), Step-by-step Procedure, Expected Observations, and Reflection Questions."
            )
            pedagogy_modules.append(
                f"### Hands-On Laboratory Activity\nProvide a full practical hands-on lab exercise for {topic_name} containing:\n- **Objective**: Clear learning goal\n- **Required Tools**: Software and CLI utility requirements\n- **Step-by-step Procedure**: Explicit commands and execution steps\n- **Expected Observations**: Terminal outputs and packet traces\n- **Reflection Questions**: 3 analytical questions on experimental outcomes."
            )
        elif any(k in p_lower for k in ["problem-based", "problem based", "problem solving", "problem-solving", "problem"]):
            pedagogy_instructions.append(
                "- **Problem-Based Learning Integration**: Present realistic engineering scenarios including Problem Statement, System Context, Engineering Constraints, Student Task, Guided Hints, Complete Solution, and Detailed Explanation."
            )
            pedagogy_modules.append(
                f"### Problem-Based Engineering Challenge\nPresent a realistic enterprise engineering scenario involving {topic_name} featuring:\n- **Problem Statement & Context**: Detailed background\n- **System Constraints**: Performance, bandwidth, or latency limits\n- **Student Task**: Engineering design/troubleshooting task\n- **Hints & Model Solution**: Step-by-step mathematical/architectural solution."
            )
        elif any(k in p_lower for k in ["demonstration", "demo", "guided walkthrough"]):
            pedagogy_instructions.append(
                "- **Demonstration Integration**: Provide step-by-step guided demonstrations students can perform independently (e.g., opening Developer Tools, capturing packet headers, inspecting TCP handshakes, analyzing response codes)."
            )
            pedagogy_modules.append(
                f"### Guided Self-Performance Demonstration\nProvide a step-by-step hands-on demonstration for {topic_name} (e.g., using Browser DevTools, Wireshark, or Linux commands) with exact clicks, commands, expected inspection outputs, and protocol header breakdowns."
            )
        elif "case study" in p_lower or "case-study" in p_lower:
            pedagogy_instructions.append(
                "- **Case Study Integration**: Include a dedicated enterprise industry case study inspired by systems like Google, Netflix, Amazon, Cloudflare, or Banking Systems, detailing Technical Background, Problem Faced, Solution Adopted, Architectural Decisions, and Lessons Learned."
            )
            pedagogy_modules.append(
                f"### Real-World Industry Case Study\nDetail a real-world enterprise case study (e.g., Google, Netflix, Cloudflare, Amazon, or Global Banking) where {topic_name} was critical, covering requirements, architectural trade-offs, failures, and lessons learned."
            )
        elif any(k in p_lower for k in ["think-pair-share", "think pair share", "peer instruction", "peer learning"]):
            pedagogy_instructions.append(
                "- **Think-Pair-Share & Peer Instruction Integration**: Include reflective discussion prompts, peer debate scenarios, and conceptual checkpoint questions."
            )
            pedagogy_modules.append(
                f"### Interactive Checkpoints & Peer Discussion Activities\nProvide 3 reflective discussion prompts, peer debate scenarios, and self-assessment conceptual questions for {topic_name}."
            )
        elif any(k in p_lower for k in ["interactive lecture", "interactive"]):
            pedagogy_instructions.append(
                "- **Interactive Lecture Integration**: Emphasize intuitive explanations, step-by-step analogies, interactive conceptual checkpoints, and visual walkthroughs."
            )
            pedagogy_modules.append(
                f"### Interactive Conceptual Walkthrough\nProvide intuitive real-world analogies, step-by-step conceptual walkthroughs, and inline reflection checkpoints for {topic_name}."
            )
        elif any(k in p_lower for k in ["simulation", "trace"]):
            pedagogy_instructions.append(
                "- **Simulation & Execution Trace Integration**: Include step-by-step execution traces, state transformation tables, and simulated runtime scenarios."
            )
            pedagogy_modules.append(
                f"### Simulation & State Execution Trace\nProvide a step-by-step simulation trace matrix showing state changes, variables, and runtime behavior for {topic_name}."
            )
        else:
            pedagogy_instructions.append(
                f"- **{p} Integration**: Tailor explanations, diagrams, and exercises specifically to emphasize the {p} methodology."
            )
            pedagogy_modules.append(
                f"### {p} Learning Module\nProvide specialized content, examples, and targeted exercises reflecting {p} principles for {topic_name}."
            )

    pedagogy_guidance_text = "\n".join(pedagogy_instructions) if pedagogy_instructions else "- Adapt tone and explanations to standard university-level pedagogy."
    pedagogy_modules_text = "\n\n".join(pedagogy_modules) if pedagogy_modules else f"### Pedagogy Integration Notes\nDetailed academic explanations and practical context tailored for {topic_name}."

    return f"""**[SYSTEM INSTRUCTIONS]**
You are a distinguished university professor and principal engineering author. Your objective is to generate comprehensive, textbook-grade study material combined with a practical laboratory manual for a SINGLE specific topic of a university course.

The output must read like a professionally published engineering textbook (such as Tanenbaum, Kurose & Ross, or Silberschatz) combined with an industry-grade lab manual. Avoid short summaries, brief notes, or high-level overviews—explain all concepts thoroughly and deeply.

Generate content ONLY for the topic: "{topic_name}". Do NOT generate content for any other topics.

**[COURSE & TOPIC METADATA]**
- Subject Name: {subject_name}
- Course Code: {course_code}
- Unit Number: {unit_number}
- Unit Title: {unit_title}
- Topic Name: {topic_name}
- Allocated Duration: {duration} Hour(s)
- Selected Pedagogy Recommendations: {pedagogy_str}

---
**[PEDAGOGY INSTRUCTIONAL REQUIREMENTS]**
The study material presentation MUST adapt to the requested pedagogy recommendations:
{pedagogy_guidance_text}

---
**[GENERATION RULES & CONSTRAINTS]**
1. STRICT FORMATTING: Output ONLY valid Markdown. Do not include introductory greetings, acknowledgments, or markdown code block wrappers around the whole document.
2. XHTML2PDF COMPATIBILITY: Use standard Markdown headings, tables, bold text, and bullet points.
3. DETAILED DEPTH: Avoid concise bullet points. Write exhaustive, academic explanations for every subsection.
4. CODE & DIAGRAM BLOCKS: All code, commands, pseudocode, and Mermaid diagrams must be wrapped in syntax-highlighted code blocks (e.g. ```python, ```bash, ```mermaid, etc.).
5. NO UNWANTED SECTIONS: Do NOT include Table of Contents, Glossary, Revision Notes, References, or content for other topics/units.
6. TOPIC-BASED IMAGES & VISUAL ILLUSTRATIONS: Include at least 2 to 3 topic-specific educational diagram image tags using standard Markdown format `![Figure X: Labeled Diagram Title](https://image.pollinations.ai/prompt/technical%20educational%20diagram%20architecture%20flowchart%20of%20{topic_name}%20computer%20science%20engineering)` or Mermaid code blocks (` ```mermaid `) to visually demonstrate key architectural mechanisms. Ensure image URL prompts explicitly incorporate the topic name "{topic_name}".

---
**[REQUIRED 12-SECTION TOPIC STRUCTURE]**
Begin the output directly with: `# Topic: {topic_name}`.

Follow strictly with these 12 main sections in this exact order:

## 1. Learning Outcomes
Describe in detail what the learner will be able to do after completing this topic across Bloom's Taxonomy levels:
- **Explain**: Fundamental mechanisms and definitions.
- **Analyse**: Architectural trade-offs and performance characteristics.
- **Compare**: Alternative protocols, data structures, or implementations.
- **Design**: Engineering solutions and system architectures.
- **Apply**: Practical algorithms, configurations, and tools.
- **Troubleshoot**: Operational failures, bottlenecks, and security vulnerabilities.

## 2. Introduction
Provide an exhaustive, engaging introduction to {topic_name} of AT LEAST 400–600 words. Cover:
- Historical background and origin.
- Engineering motivation and why the topic exists.
- Fundamental importance in modern computer science / engineering.
- Evolution of the technology over time.

## 3. Core Theory
Exhaustive textbook-level theoretical breakdown of {topic_name}. Explain every concept thoroughly without summarising:
- **Definitions & Terminology**: Precision definitions of all technical terms.
- **Internal Working**: Step-by-step operational mechanics.
- **Architecture & Components**: Structural elements and subsystems.
- **Data Flow & Protocol Flow**: Detailed message exchanges and data paths (Include image tag: `![Figure 1: {topic_name} Structural Component Diagram](https://image.pollinations.ai/prompt/detailed%20technical%20diagram%20schematic%20of%20{topic_name}%20architecture%20components)`).
- **Design Rationale**: Why the system was engineered this way.
- **Advantages & Limitations**: In-depth analysis of benefits, constraints, and operational bottlenecks.

## 4. Visual Learning
Provide visual diagrammatic representations and topic-specific images to explain {topic_name} deeply:
- **Topic Architecture & System Diagrams**: Include a high-resolution educational diagram image: `![Figure 2: Labeled Architecture Diagram for {topic_name}](https://image.pollinations.ai/prompt/technical%20educational%20diagram%20architecture%20flowchart%20of%20{topic_name}%20computer%20science%20engineering)`
- **Sequence & Flowchart Diagrams**: Labeled system layout using Mermaid (` ```mermaid `) or ASCII art.
- **Communication & State Diagrams**: State transition diagrams and message flow illustrations.
- **Comparison Tables**: Detailed feature matrix comparing {topic_name} with related technologies.

## 5. Pedagogy-Driven Activities
{pedagogy_modules_text}

## 6. Real-World Applications
Provide practical engineering breakdowns (not brief bullets) showing how {topic_name} is implemented in:
- **Cloud Computing**: AWS, Azure, GCP infrastructure.
- **Cyber Security**: Threat vectors, encryption, authentication.
- **Web Applications**: Scale, caching, API gateways.
- **Banking & Enterprise**: High-availability financial systems.
- **Healthcare & IoT**: Low-latency, reliable embedded devices.
- **AI & Mobile Applications**: Data pipelines, mobile client optimizations.

## 7. Industry Perspective
Describe real-world commercial engineering practices:
- **Current Industry Usage**: How top tech companies deploy {topic_name}.
- **Modern Technologies & Tools**: Production tools, frameworks, and standards.
- **Best Practices & Guidelines**: Engineering rules of thumb.
- **Implementation & Performance Challenges**: Bottlenecks, latency, scalability obstacles.
- **Security Considerations**: Vulnerabilities and mitigation strategies.

## 8. Interview Preparation
Provide technical interview questions grouped into 3 skill levels:
- **Beginner Level**: 2 questions with complete answers, technical explanation, and common candidate mistakes.
- **Intermediate Level**: 2 questions with complete answers, architectural explanation, and common candidate mistakes.
- **Advanced Level**: 2 questions with system design answers, technical trade-off explanation, and common candidate mistakes.

## 9. Laboratory Exercises
Provide at least 4 practical exercises formatted like an engineering lab manual:
1. **Guided Experiment 1**: Objective, Software/Hardware Requirements, Step-by-step Procedure, Expected Outcome.
2. **Guided Experiment 2**: Objective, Requirements, Step-by-step Procedure, Expected Outcome.
3. **Mini Project**: Realistic mini engineering project with specifications and implementation steps.
4. **Debugging Exercise & Implementation Challenge**: Broken scenario, failure symptom, debugging procedure, and verified fix code.

## 10. Practice Questions
Provide an extensive exam preparation section with complete answers and model solutions:
- **### 15 Multiple Choice Questions (MCQs)**: Exactly 15 MCQs with 4 options (A, B, C, D), clear **Correct Answer**, and detailed technical explanation for every question.
- **### 10 Two-Mark Questions**: Exactly 10 short university exam questions with concise model answers.
- **### 10 Five-Mark Questions**: Exactly 10 medium analytical/descriptive questions with structured answers.
- **### 5 Ten-Mark University Questions**: Exactly 5 comprehensive essay/problem questions with detailed model answers.
- **### 15 Viva Questions**: Exactly 15 oral examination questions with expert answers.

## 11. Summary
A comprehensive summary covering:
- Important core concepts.
- Key terminology reference list.
- Common student misconceptions and pitfalls.
- Industry best practices & practical tips.

## 12. Further Learning
- **Suggested Laboratory Activities**: Advanced self-study experiments.
- **Additional Practice Tasks**: Challenge problems.
- **Real-World Observation Exercises**: Field/network observation tasks (e.g. capturing traffic, checking DNS/HTTP headers).
- **Self-Assessment Checklist**: Bulleted checklist of key competencies for students to verify.
"""


def build_unit_prompt(*args, **kwargs) -> str:
    """
    Legacy wrapper for backward compatibility.
    """
    if "unit_title" in kwargs and "subject_name" in kwargs:
        topic_name = kwargs.get("unit_title", "General Topic")
        return build_topic_prompt(
            subject_name=kwargs.get("subject_name", ""),
            course_code=kwargs.get("course_code", ""),
            unit_number=kwargs.get("unit_number", 1),
            unit_title=kwargs.get("unit_title", ""),
            topic_name=topic_name,
            duration=kwargs.get("duration", 1),
            pedagogy=kwargs.get("pedagogy", [])
        )
    return ""
