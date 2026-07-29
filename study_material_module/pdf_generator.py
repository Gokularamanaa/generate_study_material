import os
import re
import base64
import logging
import html
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import markdown
from pygments.formatters import HtmlFormatter
from xhtml2pdf import pisa
from pypdf import PdfReader
from .schemas import TopicStudyMaterialRequest, TopicRequestItem, StudyMaterialRequest
from .config import OUTPUT_DIR
from .utils import slugify

logger = logging.getLogger(__name__)

# Professional University Study Guide CSS Stylesheet
DOCUMENT_CSS = """
@page cover_template {
    size: a4;
    margin: 0;
    background-color: #0f172a; /* Deep Slate 900 */
}

@page content_template {
    size: a4;
    margin-top: 2.3cm;
    margin-bottom: 2.3cm;
    margin-left: 2cm;
    margin-right: 2cm;
    @frame header_frame {
        -pdf-frame-content: header_content;
        top: 0.9cm;
        left: 2cm;
        height: 1cm;
        width: 17cm;
    }
    @frame footer_frame {
        -pdf-frame-content: footer_content;
        bottom: 0.9cm;
        left: 2cm;
        height: 1cm;
        width: 17cm;
    }
}

body {
    font-family: Helvetica, Arial, sans-serif;
    color: #1e293b; /* Slate 800 */
    line-height: 1.6;
    font-size: 9.5pt;
}

/* Headings Outline & Typography */
h1 {
    color: #0f172a; /* Slate 900 */
    font-size: 18pt;
    margin-top: 22px;
    margin-bottom: 14px;
    border-bottom: 2px solid #1e3a8a; /* Deep Blue 800 */
    padding-bottom: 6px;
    -pdf-outline: true;
    -pdf-level: 0;
}

h2 {
    color: #0f766e; /* Teal 700 */
    font-size: 14pt;
    margin-top: 18px;
    margin-bottom: 8px;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
    -pdf-outline: false;
}

h3 {
    color: #1e293b;
    font-size: 11pt;
    font-weight: bold;
    margin-top: 14px;
    margin-bottom: 6px;
    -pdf-outline: false;
}

p {
    margin-top: 0;
    margin-bottom: 10px;
    text-align: justify;
}

/* Lists */
ul, ol {
    margin-top: 0;
    margin-bottom: 10px;
    padding-left: 18px;
}

li {
    margin-bottom: 4px;
}

/* Callout Boxes & Highlighted Boxes */
blockquote {
    background-color: #f0f9ff;
    border-left: 4px solid #0284c7;
    padding: 8px 12px;
    margin: 12px 0;
    color: #0369a1;
    font-size: 9pt;
}

.callout {
    padding: 10px 14px;
    margin: 12px 0;
    font-size: 9pt;
    line-height: 1.5;
}

.callout-note {
    background-color: #f0f9ff;
    border-left: 4px solid #0284c7;
    color: #0369a1;
}

.callout-tip {
    background-color: #f0fdf4;
    border-left: 4px solid #16a34a;
    color: #15803d;
}

.callout-warning {
    background-color: #fffbe6;
    border-left: 4px solid #d97706;
    color: #b45309;
}

.callout-definition {
    background-color: #f8fafc;
    border-left: 4px solid #475569;
    color: #1e293b;
}

/* Professional Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
}

table th {
    background-color: #1e3a8a; /* Deep Blue 800 */
    color: #ffffff;
    padding: 8px 10px;
    font-weight: bold;
    border: 1px solid #cbd5e1;
    font-size: 9pt;
    text-align: left;
}

table td {
    padding: 7px 10px;
    border: 1px solid #e2e8f0;
    font-size: 8.5pt;
    vertical-align: top;
    background-color: #ffffff;
}

table tr:nth-child(even) td {
    background-color: #f8fafc;
}

/* Monospace & Code Syntax Highlighting */
code {
    font-family: Courier, monospace;
    font-size: 8pt;
    background-color: #f1f5f9;
    padding: 1px 4px;
    color: #991b1b;
}

pre, .codehilite {
    font-family: Courier, monospace;
    font-size: 8pt;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #6366f1; /* Indigo Accent */
    padding: 10px;
    margin: 14px 0;
}

/* Headers & Footers */
#header_content {
    font-size: 8.5pt;
    color: #64748b;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 3px;
}

#footer_content {
    text-align: center;
    font-size: 8.5pt;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding-top: 3px;
}

/* Course Metadata Table */
.info-table {
    margin-top: 18px;
}

.info-table th {
    background-color: #1e3a8a;
    width: 32%;
    color: #ffffff;
}

.info-table td {
    background-color: #f8fafc;
}

/* Image & Visual Diagram Styling */
.image-box {
    text-align: center;
    margin: 18px 0;
    page-break-inside: avoid;
}

img {
    max-width: 100%;
    height: auto;
    max-height: 420px;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    background-color: #ffffff;
}

.figure-caption {
    text-align: center;
    font-size: 9pt;
    font-weight: bold;
    color: #1e293b;
    background-color: #f1f5f9;
    padding: 5px 12px;
    border-radius: 0 0 6px 6px;
    border: 1.5px solid #cbd5e1;
    border-top: none;
    margin-top: -3px;
    margin-bottom: 12px;
    display: inline-block;
}
"""

RE_CALLOUT_ALERT = re.compile(r'>\s*\[\!(NOTE|TIP|WARNING|CAUTION|IMPORTANT|DEFINITION)\]\s*(.*?)(?=\n\n|\Z)', flags=re.DOTALL | re.IGNORECASE)
RE_CALLOUT_BOLD = re.compile(r'>\s*\*\*(Note|Tip|Warning|Caution|Important|Definition):\*\*\s*(.*?)(?=\n\n|\Z)', flags=re.DOTALL | re.IGNORECASE)

RE_MERMAID_BLOCK = re.compile(r'```mermaid\s*\n(.*?)```', flags=re.DOTALL | re.IGNORECASE)
RE_MARKDOWN_IMAGE = re.compile(r'\!\[([^\]]*)\]\(([^)]+)\)', flags=re.IGNORECASE)

REMOVED_SECTION_PATTERNS = [
    r'final\s+revision\s+notes',
    r'final\s+course\s+revision\s+guide',
    r'revision\s+notes',
    r'course\s+revision\s+guide',
    r'glossary(?:\s+of\s+(?:technical|key)\s+terms)?',
    r'references(?:\s*(&|and)\s*academic\s+reading)?',
    r'textbook\s+list',
    r'nptel\s+resources',
]

RE_HEADING = re.compile(r'^\s*(#{1,6})\s+(.*)$')


def remove_unwanted_sections(md_content: str) -> str:
    """
    Strips out forbidden sections (TOC, Glossary, Revision Notes, References) from Markdown content.
    """
    if not md_content or not isinstance(md_content, str):
        return md_content

    lines = md_content.splitlines()
    result_lines = []
    skipping_level = None

    for line in lines:
        match = RE_HEADING.match(line)
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()

            is_removed = any(
                re.search(pat, heading_text, re.IGNORECASE)
                for pat in REMOVED_SECTION_PATTERNS
            )

            if is_removed:
                if skipping_level is None or level <= skipping_level:
                    skipping_level = level
                continue
            else:
                if skipping_level is not None and level <= skipping_level:
                    skipping_level = None

        if skipping_level is not None:
            continue

        result_lines.append(line)

    return "\n".join(result_lines)


def generate_simple_labeled_diagram_svg(title: str, topic_name: str = "") -> str:
    """
    Generates a clean, simple, highly visible, and explicitly labeled educational vector SVG diagram.
    Uses high-contrast white background, crisp component boxes, labeled arrows, and bold readable text.
    Guarantees 100% explicit labels for all components, fields, and states.
    """
    clean_title = html.escape(title or "Technical Diagram")
    clean_topic = html.escape(topic_name or "Protocol").strip()
    topic_upper = clean_topic.upper()
    title_lower = clean_title.lower()
    topic_lower = clean_topic.lower()
    combined_text = f"{title_lower} {topic_lower}"

    # Determine diagram archetype based on title & topic keywords
    is_sequence = any(k in combined_text for k in ("sequence", "handshake", "flow", "communication", "interaction", "exchange", "transmission"))
    is_header = any(k in combined_text for k in ("header", "format", "packet", "segment", "datagram", "frame", "field", "bit"))
    is_component = any(k in combined_text for k in ("component", "structural", "internal", "buffer", "engine", "reassembler", "segmenter"))
    is_concept = any(k in combined_text for k in ("concept", "map", "matrix", "dependency", "tree", "knowledge", "relationship"))
    is_state = any(k in combined_text for k in ("state", "transition", "fsm", "machine", "status", "lifecycle"))
    is_architecture = any(k in combined_text for k in ("architecture", "layer", "stack", "tier", "overview"))

    if is_sequence:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="310" viewBox="0 0 680 310">
            <!-- Canvas Base -->
            <rect width="680" height="310" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#1e3a8a" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">SEQUENCE &amp; PROTOCOL FLOW: {topic_upper}</text>

            <!-- Node 1: Client/Sender -->
            <rect x="50" y="55" width="170" height="40" fill="#1e293b" rx="6"/>
            <text x="135" y="80" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" fill="#38bdf8" text-anchor="middle">CLIENT / SENDER (TX)</text>

            <!-- Node 2: Server/Receiver -->
            <rect x="460" y="55" width="170" height="40" fill="#0f766e" rx="6"/>
            <text x="545" y="80" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">SERVER / RECEIVER (RX)</text>

            <!-- Vertical Lifelines -->
            <line x1="135" y1="95" x2="135" y2="265" stroke="#94a3b8" stroke-width="2" stroke-dasharray="5,5"/>
            <line x1="545" y1="95" x2="545" y2="265" stroke="#94a3b8" stroke-width="2" stroke-dasharray="5,5"/>

            <!-- Arrow 1: Connection Request -->
            <line x1="140" y1="125" x2="535" y2="125" stroke="#0284c7" stroke-width="2.5"/>
            <polygon points="540,125 530,119 530,131" fill="#0284c7"/>
            <rect x="210" y="110" width="260" height="24" fill="#e0f2fe" rx="4" stroke="#0284c7" stroke-width="1.5"/>
            <text x="340" y="126" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#0369a1" text-anchor="middle">Step 1: Connection Request (SYN, Seq=X)</text>

            <!-- Arrow 2: Response & ACK -->
            <line x1="540" y1="170" x2="145" y2="170" stroke="#0d9488" stroke-width="2.5"/>
            <polygon points="140,170 150,164 150,176" fill="#0d9488"/>
            <rect x="200" y="155" width="280" height="24" fill="#ccfbf1" rx="4" stroke="#0d9488" stroke-width="1.5"/>
            <text x="340" y="171" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#0f766e" text-anchor="middle">Step 2: Response &amp; ACK (SYN-ACK, Ack=X+1)</text>

            <!-- Arrow 3: Established Data Transfer -->
            <line x1="140" y1="215" x2="535" y2="215" stroke="#16a34a" stroke-width="2.5"/>
            <polygon points="540,215 530,209 530,221" fill="#16a34a"/>
            <rect x="200" y="200" width="280" height="24" fill="#dcfce7" rx="4" stroke="#16a34a" stroke-width="1.5"/>
            <text x="340" y="216" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#15803d" text-anchor="middle">Step 3: Established Data Transfer (ACK, Payload)</text>

            <!-- Footer Badge -->
            <rect x="150" y="260" width="380" height="24" fill="#f1f5f9" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="276" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">Connection State: Active Full-Duplex Data Transmission</text>
        </svg>'''

    elif is_header:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="295" viewBox="0 0 680 295">
            <!-- Canvas Base -->
            <rect width="680" height="295" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#0f766e" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">PACKET HEADER &amp; FIELD FORMAT: {topic_upper}</text>

            <!-- Bit Position Labels -->
            <text x="40" y="60" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#475569">Bit 0</text>
            <text x="340" y="60" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#475569" text-anchor="middle">Bit 16</text>
            <text x="640" y="60" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#475569" text-anchor="end">Bit 31</text>

            <!-- Row 1: Source & Dest Port -->
            <rect x="40" y="68" width="295" height="38" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.5" rx="4"/>
            <text x="187" y="91" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#0369a1" text-anchor="middle">Source Port Number (16 Bits)</text>
            <text x="187" y="102" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#0284c7" text-anchor="middle">[Sending Process Identifier]</text>

            <rect x="345" y="68" width="295" height="38" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.5" rx="4"/>
            <text x="492" y="91" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#0369a1" text-anchor="middle">Destination Port Number (16 Bits)</text>
            <text x="492" y="102" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#0284c7" text-anchor="middle">[Receiving Process Identifier]</text>

            <!-- Row 2: Sequence Number -->
            <rect x="40" y="112" width="600" height="38" fill="#ccfbf1" stroke="#0d9488" stroke-width="1.5" rx="4"/>
            <text x="340" y="133" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#0f766e" text-anchor="middle">Sequence Number (32 Bits)</text>
            <text x="340" y="145" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#0d9488" text-anchor="middle">[In-Order Packet Sequence &amp; Reassembly Control]</text>

            <!-- Row 3: Checksum & Length -->
            <rect x="40" y="156" width="295" height="38" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="4"/>
            <text x="187" y="177" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#b45309" text-anchor="middle">Segment / Packet Length (16 Bits)</text>
            <text x="187" y="189" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#d97706" text-anchor="middle">[Header + Data Byte Count]</text>

            <rect x="345" y="156" width="295" height="38" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="4"/>
            <text x="492" y="177" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#b45309" text-anchor="middle">Header &amp; Data Checksum (16 Bits)</text>
            <text x="492" y="189" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#d97706" text-anchor="middle">[Error Detection &amp; Integrity Verification]</text>

            <!-- Row 4: Payload -->
            <rect x="40" y="200" width="600" height="42" fill="#f1f5f9" stroke="#64748b" stroke-width="1.5" rx="4"/>
            <text x="340" y="222" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#334155" text-anchor="middle">Application Data Payload (Variable Length)</text>
            <text x="340" y="235" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">[User Application Messages, Encrypted Data Stream, or Raw Datagram]</text>

            <!-- Footer Note -->
            <text x="340" y="275" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#475569" text-anchor="middle">Explicit Field Breakdown: Colors indicate Header Control vs Data Payload</text>
        </svg>'''

    elif is_component:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="300" viewBox="0 0 680 300">
            <!-- Canvas Base -->
            <rect width="680" height="300" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#1e3a8a" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">INTERNAL STRUCTURAL COMPONENTS: {topic_upper}</text>

            <!-- Tx Application Buffer -->
            <rect x="30" y="60" width="170" height="60" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" rx="5"/>
            <text x="115" y="85" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#1d4ed8" text-anchor="middle">1. TX BUFFER</text>
            <text x="115" y="105" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#3b82f6" text-anchor="middle">Application Data Stream</text>

            <!-- Arrow 1 -> 2 -->
            <line x1="200" y1="90" x2="250" y2="90" stroke="#0284c7" stroke-width="2"/>
            <polygon points="255,90 247,85 247,95" fill="#0284c7"/>

            <!-- Segmenter & Header Formatter -->
            <rect x="255" y="60" width="170" height="60" fill="#ccfbf1" stroke="#0f766e" stroke-width="1.5" rx="5"/>
            <text x="340" y="85" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#0f766e" text-anchor="middle">2. SEGMENTER &amp; HEADER</text>
            <text x="340" y="105" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#115e59" text-anchor="middle">Port &amp; Seq Num Formatting</text>

            <!-- Arrow 2 -> 3 -->
            <line x1="425" y1="90" x2="475" y2="90" stroke="#0284c7" stroke-width="2"/>
            <polygon points="480,90 472,85 472,95" fill="#0284c7"/>

            <!-- Checksum & Error Engine -->
            <rect x="480" y="60" width="170" height="60" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="5"/>
            <text x="565" y="85" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#b45309" text-anchor="middle">3. CHECKSUM MODULE</text>
            <text x="565" y="105" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#d97706" text-anchor="middle">16-Bit CRC &amp; Verification</text>

            <!-- Arrow 3 down to 4 -->
            <line x1="565" y1="120" x2="565" y2="165" stroke="#0284c7" stroke-width="2"/>
            <polygon points="565,170 560,162 570,162" fill="#0284c7"/>

            <!-- Flow Control & Network Interface -->
            <rect x="480" y="170" width="170" height="60" fill="#e0e7ff" stroke="#6366f1" stroke-width="1.5" rx="5"/>
            <text x="565" y="195" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#4338ca" text-anchor="middle">4. FLOW &amp; SOCKET CONTROL</text>
            <text x="565" y="215" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#6366f1" text-anchor="middle">Sliding Window &amp; Timers</text>

            <!-- Arrow 4 left to 5 -->
            <line x1="480" y1="200" x2="430" y2="200" stroke="#0284c7" stroke-width="2"/>
            <polygon points="425,200 433,195 433,205" fill="#0284c7"/>

            <!-- Reassembly Engine -->
            <rect x="255" y="170" width="170" height="60" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5" rx="5"/>
            <text x="340" y="195" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#15803d" text-anchor="middle">5. REASSEMBLY ENGINE</text>
            <text x="340" y="215" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#16a34a" text-anchor="middle">In-Order Packet Sorting</text>

            <!-- Arrow 5 left to 6 -->
            <line x1="255" y1="200" x2="205" y2="200" stroke="#0284c7" stroke-width="2"/>
            <polygon points="200,200 208,195 208,205" fill="#0284c7"/>

            <!-- Rx Application Buffer -->
            <rect x="30" y="170" width="170" height="60" fill="#f1f5f9" stroke="#64748b" stroke-width="1.5" rx="5"/>
            <text x="115" y="195" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#334155" text-anchor="middle">6. RX BUFFER</text>
            <text x="115" y="215" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#64748b" text-anchor="middle">Delivered Application Data</text>

            <!-- Bottom Status -->
            <rect x="140" y="250" width="400" height="24" fill="#f8fafc" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="266" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#475569" text-anchor="middle">Data Pipeline: Bi-directional Transmission, Packetizing &amp; Verification</text>
        </svg>'''

    elif is_concept:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="295" viewBox="0 0 680 295">
            <!-- Canvas Base -->
            <rect width="680" height="295" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#0f766e" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">CONCEPT MAP &amp; KNOWLEDGE MATRIX: {topic_upper}</text>

            <!-- Center Node -->
            <rect x="240" y="115" width="200" height="55" fill="#1e293b" rx="6" stroke="#0f766e" stroke-width="2"/>
            <text x="340" y="140" font-family="Helvetica, Arial, sans-serif" font-size="13" font-weight="bold" fill="#38bdf8" text-anchor="middle">{topic_upper}</text>
            <text x="340" y="157" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#94a3b8" text-anchor="middle">Transport Layer Protocol</text>

            <!-- Node 1: Top Left - Prerequisites -->
            <rect x="30" y="55" width="180" height="50" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" rx="5"/>
            <text x="120" y="77" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#1d4ed8" text-anchor="middle">1. PREREQUISITES</text>
            <text x="120" y="93" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#3b82f6" text-anchor="middle">IP Layer &amp; Port Sockets</text>
            <line x1="210" y1="90" x2="250" y2="120" stroke="#3b82f6" stroke-width="1.5"/>

            <!-- Node 2: Top Right - Core Mechanics -->
            <rect x="470" y="55" width="180" height="50" fill="#ccfbf1" stroke="#0d9488" stroke-width="1.5" rx="5"/>
            <text x="560" y="77" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#0f766e" text-anchor="middle">2. CORE MECHANICS</text>
            <text x="560" y="93" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#0d9488" text-anchor="middle">Checksum &amp; Packet Flags</text>
            <line x1="470" y1="90" x2="430" y2="120" stroke="#0d9488" stroke-width="1.5"/>

            <!-- Node 3: Bottom Left - Applications -->
            <rect x="30" y="180" width="180" height="50" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5" rx="5"/>
            <text x="120" y="202" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#15803d" text-anchor="middle">3. APPLICATIONS</text>
            <text x="120" y="218" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#16a34a" text-anchor="middle">Web, Cloud, Streaming, DNS</text>
            <line x1="210" y1="195" x2="250" y2="165" stroke="#16a34a" stroke-width="1.5"/>

            <!-- Node 4: Bottom Right - Control & Security -->
            <rect x="470" y="180" width="180" height="50" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="5"/>
            <text x="560" y="202" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#b45309" text-anchor="middle">4. CONTROL &amp; SECURITY</text>
            <text x="560" y="218" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#d97706" text-anchor="middle">Flow Control &amp; Encryption</text>
            <line x1="470" y1="195" x2="430" y2="165" stroke="#d97706" stroke-width="1.5"/>

            <!-- Bottom Badge -->
            <rect x="180" y="255" width="320" height="22" fill="#f1f5f9" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="270" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#475569" text-anchor="middle">Hierarchical Concept Mapping &amp; Dependencies</text>
        </svg>'''

    elif is_state:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="270" viewBox="0 0 680 270">
            <!-- Canvas Base -->
            <rect width="680" height="270" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#4338ca" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">STATE TRANSITION &amp; FINITE STATE MACHINE: {topic_upper}</text>

            <!-- State 1 -->
            <rect x="30" y="100" width="130" height="50" fill="#e0e7ff" stroke="#6366f1" stroke-width="2" rx="25"/>
            <text x="95" y="122" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#4338ca" text-anchor="middle">CLOSED</text>
            <text x="95" y="137" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#6366f1" text-anchor="middle">Idle / Initial State</text>

            <!-- Arrow 1 -> 2 -->
            <line x1="160" y1="125" x2="195" y2="125" stroke="#4338ca" stroke-width="2"/>
            <polygon points="200,125 192,120 192,130" fill="#4338ca"/>

            <!-- State 2 -->
            <rect x="200" y="100" width="130" height="50" fill="#e0f2fe" stroke="#0284c7" stroke-width="2" rx="25"/>
            <text x="265" y="122" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#0369a1" text-anchor="middle">SYN_SENT / LISTEN</text>
            <text x="265" y="137" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#0284c7" text-anchor="middle">Handshake In Progress</text>

            <!-- Arrow 2 -> 3 -->
            <line x1="330" y1="125" x2="365" y2="125" stroke="#0284c7" stroke-width="2"/>
            <polygon points="370,125 362,120 362,130" fill="#0284c7"/>

            <!-- State 3 -->
            <rect x="370" y="100" width="140" height="50" fill="#dcfce7" stroke="#16a34a" stroke-width="2" rx="25"/>
            <text x="440" y="122" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#15803d" text-anchor="middle">ESTABLISHED</text>
            <text x="440" y="137" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#16a34a" text-anchor="middle">Data Exchange Active</text>

            <!-- Arrow 3 -> 4 -->
            <line x1="510" y1="125" x2="545" y2="125" stroke="#16a34a" stroke-width="2"/>
            <polygon points="550,125 542,120 542,130" fill="#16a34a"/>

            <!-- State 4 -->
            <rect x="550" y="100" width="100" height="50" fill="#fef3c7" stroke="#d97706" stroke-width="2" rx="25"/>
            <text x="600" y="122" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#b45309" text-anchor="middle">TERMINATED</text>
            <text x="600" y="137" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#d97706" text-anchor="middle">Connection Closed</text>

            <!-- Event Action Labels below arrows -->
            <rect x="40" y="180" width="140" height="35" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>
            <text x="110" y="196" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">Event 1: Open Call</text>
            <text x="110" y="208" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#64748b" text-anchor="middle">Send SYN Packet</text>

            <rect x="200" y="180" width="140" height="35" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>
            <text x="270" y="196" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">Event 2: ACK Recv</text>
            <text x="270" y="208" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#64748b" text-anchor="middle">Complete Handshake</text>

            <rect x="360" y="180" width="140" height="35" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>
            <text x="430" y="196" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">Event 3: Full-Duplex</text>
            <text x="430" y="208" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#64748b" text-anchor="middle">Stream Payload Data</text>

            <rect x="520" y="180" width="130" height="35" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>
            <text x="585" y="196" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">Event 4: Close / FIN</text>
            <text x="585" y="208" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#64748b" text-anchor="middle">Clean Teardown</text>

            <text x="340" y="248" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#475569" text-anchor="middle">Protocol Finite State Machine (FSM) Lifecycle</text>
        </svg>'''

    elif is_architecture:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="290" viewBox="0 0 680 290">
            <!-- Canvas Base -->
            <rect width="680" height="290" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            
            <!-- Header Bar -->
            <rect width="680" height="42" fill="#1e3a8a" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">SYSTEM ARCHITECTURE &amp; PROTOCOL STACK: {topic_upper}</text>

            <!-- Tier 1: Application Layer -->
            <rect x="50" y="55" width="580" height="42" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" rx="5"/>
            <text x="340" y="74" font-family="Helvetica, Arial, sans-serif" font-size="11.5" font-weight="bold" fill="#1d4ed8" text-anchor="middle">APPLICATION LAYER (HTTP / HTTPS / DNS / SSH / FTP)</text>
            <text x="340" y="89" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#3b82f6" text-anchor="middle">Data Origin &amp; User Process Interaction [Generates Application Payload]</text>

            <!-- Arrow Down -->
            <line x1="340" y1="97" x2="340" y2="112" stroke="#0284c7" stroke-width="2"/>
            <polygon points="340,116 335,108 345,108" fill="#0284c7"/>

            <!-- Tier 2: Core Topic Layer -->
            <rect x="50" y="118" width="580" height="50" fill="#ccfbf1" stroke="#0f766e" stroke-width="2.5" rx="5"/>
            <text x="340" y="139" font-family="Helvetica, Arial, sans-serif" font-size="13" font-weight="bold" fill="#0f766e" text-anchor="middle">TRANSPORT LAYER: {topic_upper}</text>
            <text x="340" y="157" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#115e59" text-anchor="middle">Port Multiplexing | Segment Header | Flow Control | Error Verification</text>

            <!-- Arrow Down -->
            <line x1="340" y1="168" x2="340" y2="183" stroke="#0284c7" stroke-width="2"/>
            <polygon points="340,187 335,179 345,179" fill="#0284c7"/>

            <!-- Tier 3: Network Layer -->
            <rect x="50" y="189" width="580" height="42" fill="#f1f5f9" stroke="#64748b" stroke-width="1.5" rx="5"/>
            <text x="340" y="208" font-family="Helvetica, Arial, sans-serif" font-size="11.5" font-weight="bold" fill="#334155" text-anchor="middle">NETWORK LAYER (INTERNET PROTOCOL - IP)</text>
            <text x="340" y="223" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#64748b" text-anchor="middle">Logical IP Addressing &amp; Packet Routing Across Internet Gateways</text>

            <!-- Bottom Note -->
            <rect x="140" y="248" width="400" height="24" fill="#f8fafc" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="264" font-family="Helvetica, Arial, sans-serif" font-size="9.5" font-weight="bold" fill="#475569" text-anchor="middle">Data Encapsulation Flow: Application Data -&gt; Segment -&gt; IP Packet</text>
        </svg>'''

    else:
        # Generic Crisp Flowchart Diagram
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="270" viewBox="0 0 680 270">
            <!-- Canvas Base -->
            <rect width="680" height="270" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>

            <!-- Header Bar -->
            <rect width="680" height="42" fill="#0f766e" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">CONCEPTUAL FLOWCHART: {clean_title.upper()}</text>

            <!-- Box 1: Input / Origin -->
            <rect x="40" y="68" width="165" height="70" fill="#eff6ff" stroke="#3b82f6" stroke-width="2" rx="6"/>
            <text x="122" y="98" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" fill="#1d4ed8" text-anchor="middle">INPUT DATA</text>
            <text x="122" y="118" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#3b82f6" text-anchor="middle">Origin &amp; Request Stream</text>

            <!-- Arrow 1 -->
            <line x1="205" y1="103" x2="252" y2="103" stroke="#0284c7" stroke-width="2.5"/>
            <polygon points="257,103 249,98 249,108" fill="#0284c7"/>

            <!-- Box 2: Core Processing -->
            <rect x="259" y="58" width="162" height="90" fill="#ccfbf1" stroke="#0f766e" stroke-width="2.5" rx="6"/>
            <text x="340" y="88" font-family="Helvetica, Arial, sans-serif" font-size="13" font-weight="bold" fill="#0f766e" text-anchor="middle">{topic_upper}</text>
            <text x="340" y="108" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#115e59" text-anchor="middle">CORE PROTOCOL</text>
            <text x="340" y="128" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#0f766e" text-anchor="middle">Formatting &amp; Controls</text>

            <!-- Arrow 2 -->
            <line x1="421" y1="103" x2="468" y2="103" stroke="#0284c7" stroke-width="2.5"/>
            <polygon points="473,103 465,98 465,108" fill="#0284c7"/>

            <!-- Box 3: Output / Result -->
            <rect x="475" y="68" width="165" height="70" fill="#f0fdf4" stroke="#16a34a" stroke-width="2" rx="6"/>
            <text x="557" y="98" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" fill="#15803d" text-anchor="middle">OUTPUT / RESULT</text>
            <text x="557" y="118" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#16a34a" text-anchor="middle">Verified Delivery Target</text>

            <!-- Bottom Attribute Badges -->
            <rect x="40" y="175" width="180" height="50" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="130" y="196" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">1. High Reliability</text>
            <text x="130" y="213" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">Error Detection &amp; Checking</text>

            <rect x="250" y="175" width="180" height="50" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="340" y="196" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">2. Explicit Controls</text>
            <text x="340" y="213" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">Flow &amp; Sequence Tracking</text>

            <rect x="460" y="175" width="180" height="50" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="550" y="196" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">3. Standard Compliant</text>
            <text x="550" y="213" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">RFC Standard Specifications</text>
        </svg>'''

    b64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64}"


def generate_fallback_svg_data_uri(title: str, topic_name: str = "Topic Architecture") -> str:
    """Backward-compatible alias for generate_simple_labeled_diagram_svg."""
    return generate_simple_labeled_diagram_svg(title, topic_name)


def fetch_image_as_data_uri(url: str, title: str = "", topic_name: str = "") -> str:
    """
    Returns a simple, clean, explicitly labeled educational vector SVG diagram.
    AI prompt image URLs (e.g. Pollinations AI, Unsplash, external web links) are replaced with crisp, labeled educational SVG diagrams.
    """
    if not url or not isinstance(url, str):
        return generate_simple_labeled_diagram_svg(title, topic_name)
    
    url = url.strip()
    if url.startswith("data:image/"):
        return url

    # Replace AI image generation URLs with clear labeled SVG diagrams
    url_lower = url.lower()
    if any(domain in url_lower for domain in ("pollinations.ai", "dalle", "midjourney", "stable-diffusion", "placeholder")):
        return generate_simple_labeled_diagram_svg(title, topic_name)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        import httpx
        with httpx.Client(timeout=4.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and len(resp.content) > 100:
                content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                if "html" not in content_type and "text" not in content_type and "xml" not in content_type:
                    b64 = base64.b64encode(resp.content).decode("utf-8")
                    return f"data:{content_type};base64,{b64}"
    except Exception as e:
        logger.debug(f"httpx image fetch failed for '{url}': {str(e)}")

    return generate_simple_labeled_diagram_svg(title, topic_name)


def clean_markdown_for_pdf(md_content: str, topic_name: str = "") -> str:
    """
    Cleans markdown content and transforms callout markers, images, and Mermaid blocks into styled HTML for PDF rendering.
    Pre-fetches image URLs into base64 Data URIs to ensure 100% reliable PDF rendering.
    """
    if not md_content or not isinstance(md_content, str):
        return "Study material could not be generated."

    md_content = remove_unwanted_sections(md_content)

    # 0. Check if image tags exist; if missing, auto-inject a topic-based image tag
    has_images = bool(RE_MARKDOWN_IMAGE.search(md_content) or RE_MERMAID_BLOCK.search(md_content))
    if not has_images and topic_name:
        encoded_topic = urllib.parse.quote(topic_name)
        auto_img_tag = (
            f"\n\n![Figure 1: {topic_name} Architectural & System Diagram]"
            f"(https://image.pollinations.ai/prompt/technical%20educational%20diagram%20architecture%20flowchart%20of%20{encoded_topic}%20computer%20science%20engineering)\n\n"
        )
        if "## 4. Visual Learning" in md_content:
            md_content = md_content.replace("## 4. Visual Learning", "## 4. Visual Learning" + auto_img_tag)
        elif "## 3. Core Theory" in md_content:
            md_content = md_content.replace("## 3. Core Theory", "## 3. Core Theory" + auto_img_tag)
        else:
            md_content += auto_img_tag

    # 1. Transform Mermaid code blocks into rendered visual image tags
    def replace_mermaid(match):
        mermaid_code = match.group(1).strip()
        code_lower = mermaid_code.lower()
        if "sequencediagram" in code_lower:
            m_title = f"{topic_name} Protocol Sequence & Handshake Diagram"
        elif "statediagram" in code_lower:
            m_title = f"{topic_name} State Transition & FSM Diagram"
        elif "classdiagram" in code_lower:
            m_title = f"{topic_name} Component & Class Structure Diagram"
        elif "gantt" in code_lower:
            m_title = f"{topic_name} Execution Timeline & Schedule"
        else:
            m_title = f"{topic_name} Visual System Architecture Diagram"

        try:
            encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
            img_url = f"https://mermaid.ink/png/{encoded}"
            data_uri = fetch_image_as_data_uri(img_url, title=m_title, topic_name=topic_name)
            return f'\n<div class="image-box"><img src="{data_uri}" alt="{html.escape(m_title)}"/><p class="figure-caption">{html.escape(m_title)}</p></div>\n'
        except Exception:
            return match.group(0)

    md_content = RE_MERMAID_BLOCK.sub(replace_mermaid, md_content)

    # 2. Transform Markdown image tags ![alt](url) into styled HTML figure containers
    def replace_image(match):
        alt_text = match.group(1).strip() or f"{topic_name} Architectural Diagram"
        img_url = match.group(2).strip()
        data_uri = fetch_image_as_data_uri(img_url, title=alt_text, topic_name=topic_name)
        return f'\n<div class="image-box"><img src="{data_uri}" alt="{alt_text}"/><p class="figure-caption">{alt_text}</p></div>\n'

    md_content = RE_MARKDOWN_IMAGE.sub(replace_image, md_content)

    # 3. Transform Callout boxes
    def replace_callout(match):
        kind = match.group(1).lower()
        body = match.group(2).strip()
        if any(kw in kind for kw in ("warning", "caution", "important")):
            css_class = "callout-warning"
            title = "WARNING"
        elif "tip" in kind:
            css_class = "callout-tip"
            title = "TIP"
        elif "definition" in kind:
            css_class = "callout-definition"
            title = "DEFINITION"
        else:
            css_class = "callout-note"
            title = "NOTE"
        return f'<div class="callout {css_class}"><strong>{title}</strong><br/>{body}</div>'

    md_content = RE_CALLOUT_ALERT.sub(replace_callout, md_content)
    md_content = RE_CALLOUT_BOLD.sub(replace_callout, md_content)
    return md_content



def generate_topic_pdf(
    request: TopicStudyMaterialRequest,
    successful_topics: List[Tuple[TopicRequestItem, str]],
    output_dir: Path
) -> Dict[str, Any]:
    """
    Compiles generated study material for one or more topics into a structured HTML PDF layout containing:
      - Cover Page
      - Topic Information Page
      - Topic Study Material & Practice Section (separated by page breaks)
    Returns dict containing relative pdf_path and page count.
    """
    logger.info(f"Initializing PDF generation process for {len(successful_topics)} topic(s)...")

    generation_date = datetime.now().strftime("%Y-%m-%d")
    topic_names = [topic_item.topic_name for topic_item, _ in successful_topics]
    topic_names_str = ", ".join(topic_names)
    total_duration = sum(topic_item.duration for topic_item, _ in successful_topics)
    
    all_pedagogy_set = set()
    for topic_item, _ in successful_topics:
        all_pedagogy_set.update(topic_item.pedagogy)
    all_pedagogy_str = ", ".join(sorted(all_pedagogy_set)) if all_pedagogy_set else "Standard Academic Instruction"

    # 1. Executive Cover Page HTML
    cover_html = f"""
    <pdf:nexttemplate name="cover_template" />
    <h1 style="font-size: 0.1pt; color: #0f172a; margin: 0; padding: 0; border: none; page-break-before: avoid; -pdf-outline: true;">Cover Page</h1>
    <div style="padding: 2.5cm 2cm 2cm 2cm; color: #ffffff;">
        <div style="margin-top: 2.5cm; border-bottom: 2px solid #0d9488; padding-bottom: 15px;">
            <p style="font-size: 10pt; color: #38bdf8; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;">
                PEDAGOGY-DRIVEN STUDY MATERIAL & REFERENCE
            </p>
            <h1 style="font-size: 26pt; color: #ffffff; margin: 8px 0; font-weight: bold; line-height: 1.2; border: none; page-break-before: avoid; -pdf-outline: false;">
                {request.subject_name}
            </h1>
            <p style="font-size: 13pt; color: #94a3b8; margin-top: 6px;">
                Course Code: <strong>{request.course_code}</strong>
            </p>
        </div>
        
        <div style="margin-top: 2cm; background-color: #1e293b; padding: 18px; border-left: 4px solid #0d9488;">
            <p style="font-size: 13pt; font-weight: bold; color: #38bdf8; margin-bottom: 4px;">
                Unit {request.unit_number}: {request.unit_title}
            </p>
            <p style="font-size: 16pt; font-weight: bold; color: #ffffff; margin-bottom: 8px;">
                Topic(s): {topic_names_str}
            </p>
            <p style="font-size: 10pt; color: #cbd5e1; margin-top: 6px;">
                Duration: <strong>{total_duration} Hours</strong>
            </p>
            <p style="font-size: 10pt; color: #cbd5e1; margin-top: 4px;">
                Selected Pedagogy: <strong>{all_pedagogy_str}</strong>
            </p>
        </div>
        
        <div style="margin-top: 3cm; font-size: 9pt; color: #94a3b8; line-height: 1.5;">
            <p>Generation Date: <strong>{generation_date}</strong></p>
            <p>University Study Material Module</p>
        </div>
    </div>
    """

    # 2. Topic Information Page HTML
    topic_rows = []
    for topic_item, _ in successful_topics:
        p_str = ", ".join(topic_item.pedagogy) if topic_item.pedagogy else "Standard Academic"
        topic_rows.append(f"""
        <tr>
            <td><strong>{topic_item.topic_name}</strong></td>
            <td>{topic_item.duration} Hour(s)</td>
            <td>{p_str}</td>
        </tr>
        """)
    topic_rows_html = "\n".join(topic_rows)

    topic_info_html = f"""
    <pdf:nexttemplate name="content_template" />
    <h1 style="page-break-before: always;">Topic Information</h1>
    <p>This study guide contains detailed academic material and practice exercises generated for the specified topic(s):</p>
    <table class="info-table">
        <tr>
            <th>Subject Name</th>
            <td>{request.subject_name} ({request.course_code})</td>
        </tr>
        <tr>
            <th>Unit Details</th>
            <td>Unit {request.unit_number}: {request.unit_title}</td>
        </tr>
        <tr>
            <th>Total Duration</th>
            <td>{total_duration} Hours</td>
        </tr>
        <tr>
            <th>Generation Date</th>
            <td>{generation_date}</td>
        </tr>
    </table>

    <h3 style="margin-top: 20px;">Included Topics Overview</h3>
    <table>
        <thead>
            <tr>
                <th>Topic Name</th>
                <th>Duration</th>
                <th>Pedagogy Recommendations</th>
            </tr>
        </thead>
        <tbody>
            {topic_rows_html}
        </tbody>
    </table>
    """

    # 3. Topic Material Content HTML
    md_parser = markdown.Markdown(extensions=['extra', 'codehilite'])
    topic_sections_html = []

    for topic_item, raw_md in successful_topics:
        cleaned_md = clean_markdown_for_pdf(raw_md, topic_name=topic_item.topic_name)
        html_body = md_parser.convert(cleaned_md)

        topic_sections_html.append(f"""
        <div style="page-break-before: always;">
            {html_body}
        </div>
        """)

    all_topics_content_html = "\n".join(topic_sections_html)

    # 4. Pygments syntax highlighting CSS
    pygments_css = HtmlFormatter(style='friendly').get_style_defs('.codehilite')

    # 5. Assemble Full HTML Document
    full_html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        {DOCUMENT_CSS}
        {pygments_css}
    </style>
    </head>
    <body>
        <!-- Header & Footer Definitions -->
        <div id="header_content">
            <table style="width:100%; border:0; margin:0;">
                <tr>
                    <td style="border:0; padding:0; text-align:left; color:#64748b; font-size:8.5pt;">
                        {request.course_code} - {request.subject_name} (Unit {request.unit_number})
                    </td>
                    <td style="border:0; padding:0; text-align:right; color:#64748b; font-size:8.5pt;">
                        Topics: {topic_names_str}
                    </td>
                </tr>
            </table>
        </div>
        
        <div id="footer_content">
            Page <pdf:pagenumber /> of <pdf:pagecount />
        </div>
        
        <!-- Main Document Flow -->
        {cover_html}
        {topic_info_html}
        {all_topics_content_html}
    </body>
    </html>
    """

    # Output filename generation
    slug_parts = [slugify(t[0].topic_name) for t in successful_topics]
    combined_slug = "_".join(slug_parts)
    if len(combined_slug) > 50:
        combined_slug = f"{slug_parts[0]}_and_{len(slug_parts)-1}_more"
    pdf_filename = f"Unit_{request.unit_number}_{combined_slug}.pdf"
    pdf_path = output_dir / pdf_filename

    # Render PDF using xhtml2pdf
    logger.info(f"Compiling PDF for {len(successful_topics)} topic(s): {pdf_path}")
    with open(pdf_path, "wb") as f:
        pisa_status = pisa.CreatePDF(full_html, dest=f)

    if pisa_status.err != 0:
        logger.error(f"xhtml2pdf failed for topic PDF generation with status code {pisa_status.err}")
        raise RuntimeError(f"Failed to generate topic PDF. Status: {pisa_status.err}")

    # Read page count using pypdf
    try:
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
    except Exception as e:
        logger.warning(f"Failed to read PDF page count: {str(e)}")
        page_count = 0

    logger.info(f"Successfully generated topic PDF: {pdf_path} (Pages: {page_count})")

    rel_path = Path("output") / output_dir.name / pdf_filename

    return {
        "pdf_path": rel_path.as_posix(),
        "pages": page_count
    }


def generate_unit_pdf(request, unit, unit_markdown, output_dir):
    """
    Legacy helper for backward compatibility.
    """
    from .schemas import TopicStudyMaterialRequest, TopicRequestItem
    if isinstance(request, TopicStudyMaterialRequest):
        req = request
    else:
        req = TopicStudyMaterialRequest(
            subject_name=getattr(request, "subject_name", "Subject"),
            course_code=getattr(request, "course_code", "COURSE101"),
            unit_number=getattr(unit, "unit_number", 1),
            unit_title=getattr(unit, "unit_title", "Unit Title"),
            topics=[TopicRequestItem(topic_name=getattr(unit, "unit_title", "Topic"), duration=1, pedagogy=[])]
        )

    successful = [(req.topics[0], unit_markdown)]
    return generate_topic_pdf(req, successful, output_dir)
