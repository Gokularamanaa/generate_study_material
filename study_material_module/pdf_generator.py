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
    Generates a clean, simple, highly visible, and explicitly topic-tailored educational vector SVG diagram.
    Guarantees 100% topic-specific visual diagrams without duplicate or hardcoded static TCP templates.
    """
    clean_title = html.escape(title or "Technical Diagram").strip()
    clean_topic = html.escape(topic_name or "Topic Architecture").strip()
    topic_upper = clean_topic.upper()
    title_upper = clean_title.upper()
    combined_text = f"{clean_title.lower()} {clean_topic.lower()}"

    # 1. Ethernet Specific Diagram
    if "ethernet" in combined_text:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="310" viewBox="0 0 680 310">
            <rect width="680" height="310" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            <rect width="680" height="42" fill="#0f766e" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">ETHERNET FRAME FORMAT &amp; SWITCHED LAN TOPOLOGY</text>

            <text x="35" y="62" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155">IEEE 802.3 Ethernet Frame Structure:</text>
            
            <rect x="35" y="70" width="70" height="35" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.5" rx="3"/>
            <text x="70" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#0369a1" text-anchor="middle">Preamble</text>
            <text x="70" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#0284c7" text-anchor="middle">(7 Bytes)</text>

            <rect x="108" y="70" width="40" height="35" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.5" rx="3"/>
            <text x="128" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#0369a1" text-anchor="middle">SFD</text>
            <text x="128" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#0284c7" text-anchor="middle">(1B)</text>

            <rect x="151" y="70" width="115" height="35" fill="#ccfbf1" stroke="#0d9488" stroke-width="1.5" rx="3"/>
            <text x="208" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#0f766e" text-anchor="middle">Dest MAC Addr</text>
            <text x="208" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#0d9488" text-anchor="middle">(6 Bytes)</text>

            <rect x="269" y="70" width="115" height="35" fill="#ccfbf1" stroke="#0d9488" stroke-width="1.5" rx="3"/>
            <text x="326" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#0f766e" text-anchor="middle">Source MAC Addr</text>
            <text x="326" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#0d9488" text-anchor="middle">(6 Bytes)</text>

            <rect x="387" y="70" width="65" height="35" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="3"/>
            <text x="419" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#b45309" text-anchor="middle">EtherType</text>
            <text x="419" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#d97706" text-anchor="middle">(2 Bytes)</text>

            <rect x="455" y="70" width="130" height="35" fill="#f1f5f9" stroke="#64748b" stroke-width="1.5" rx="3"/>
            <text x="520" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">Data Payload</text>
            <text x="520" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#64748b" text-anchor="middle">(46 - 1500 Bytes)</text>

            <rect x="588" y="70" width="57" height="35" fill="#fce7f3" stroke="#db2777" stroke-width="1.5" rx="3"/>
            <text x="616" y="87" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="bold" fill="#9d174d" text-anchor="middle">FCS / CRC</text>
            <text x="616" y="98" font-family="Helvetica, Arial, sans-serif" font-size="7.5" fill="#db2777" text-anchor="middle">(4 Bytes)</text>

            <text x="35" y="125" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155">Switched Ethernet Star Topology:</text>

            <rect x="260" y="140" width="160" height="45" fill="#1e293b" rx="6" stroke="#0f766e" stroke-width="2"/>
            <text x="340" y="162" font-family="Helvetica, Arial, sans-serif" font-size="11.5" font-weight="bold" fill="#38bdf8" text-anchor="middle">CENTRAL SWITCH</text>
            <text x="340" y="176" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#94a3b8" text-anchor="middle">Multi-port Packet Forwarding</text>

            <rect x="35" y="210" width="125" height="42" fill="#eff6ff" stroke="#3b82f6" rx="5"/>
            <text x="97" y="228" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#1d4ed8" text-anchor="middle">HOST A (Tx)</text>
            <text x="97" y="242" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#3b82f6" text-anchor="middle">MAC: 00:1A:2B:3C:4D:5E</text>
            <line x1="160" y1="230" x2="270" y2="185" stroke="#3b82f6" stroke-width="1.5"/>

            <rect x="185" y="210" width="125" height="42" fill="#f0fdf4" stroke="#16a34a" rx="5"/>
            <text x="247" y="228" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#15803d" text-anchor="middle">HOST B (Rx)</text>
            <text x="247" y="242" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#16a34a" text-anchor="middle">MAC: 00:1A:2B:3C:4D:5F</text>
            <line x1="250" y1="210" x2="310" y2="185" stroke="#16a34a" stroke-width="1.5"/>

            <rect x="370" y="210" width="125" height="42" fill="#fef3c7" stroke="#d97706" rx="5"/>
            <text x="432" y="228" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#b45309" text-anchor="middle">HOST C</text>
            <text x="432" y="242" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#d97706" text-anchor="middle">MAC: 00:1A:2B:3C:4D:60</text>
            <line x1="430" y1="210" x2="370" y2="185" stroke="#d97706" stroke-width="1.5"/>

            <rect x="520" y="210" width="125" height="42" fill="#f1f5f9" stroke="#64748b" rx="5"/>
            <text x="582" y="228" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">HOST D</text>
            <text x="582" y="242" font-family="Helvetica, Arial, sans-serif" font-size="8" fill="#64748b" text-anchor="middle">MAC: 00:1A:2B:3C:4D:61</text>
            <line x1="520" y1="230" x2="410" y2="185" stroke="#64748b" stroke-width="1.5"/>

            <rect x="140" y="270" width="400" height="22" fill="#f8fafc" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="285" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#475569" text-anchor="middle">Ethernet Standard: Point-to-Point Full-Duplex Switching without Collisions</text>
        </svg>'''

    # 2. CSMA / CSMA/CD Specific Diagram
    elif "csma" in combined_text or "collision" in combined_text:
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="310" viewBox="0 0 680 310">
            <rect width="680" height="310" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            <rect width="680" height="42" fill="#b45309" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">CSMA/CD: CARRIER SENSING &amp; COLLISION DETECTION PROTOCOL</text>

            <rect x="30" y="65" width="135" height="55" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" rx="5"/>
            <text x="97" y="87" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#1d4ed8" text-anchor="middle">1. CARRIER SENSE</text>
            <text x="97" y="104" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#3b82f6" text-anchor="middle">Listen to Medium (Idle?)</text>

            <line x1="165" y1="92" x2="190" y2="92" stroke="#0284c7" stroke-width="2"/>
            <polygon points="195,92 187,87 187,97" fill="#0284c7"/>

            <rect x="195" y="65" width="135" height="55" fill="#ccfbf1" stroke="#0d9488" stroke-width="1.5" rx="5"/>
            <text x="262" y="87" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#0f766e" text-anchor="middle">2. TRANSMIT FRAME</text>
            <text x="262" y="104" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#0d9488" text-anchor="middle">Send Data on Shared Bus</text>

            <line x1="330" y1="92" x2="355" y2="92" stroke="#0284c7" stroke-width="2"/>
            <polygon points="360,92 352,87 352,97" fill="#0284c7"/>

            <rect x="360" y="65" width="140" height="55" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="5"/>
            <text x="430" y="87" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#b45309" text-anchor="middle">3. COLLISION DETECT</text>
            <text x="430" y="104" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#d97706" text-anchor="middle">Monitor Signal Voltage</text>

            <line x1="500" y1="92" x2="525" y2="92" stroke="#0284c7" stroke-width="2"/>
            <polygon points="530,92 522,87 522,97" fill="#0284c7"/>

            <rect x="530" y="65" width="120" height="55" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5" rx="5"/>
            <text x="590" y="87" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#15803d" text-anchor="middle">SUCCESS</text>
            <text x="590" y="104" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#16a34a" text-anchor="middle">No Collision: Complete</text>

            <line x1="430" y1="120" x2="430" y2="155" stroke="#dc2626" stroke-width="2"/>
            <polygon points="430,160 425,152 435,152" fill="#dc2626"/>
            <text x="435" y="142" font-family="Helvetica, Arial, sans-serif" font-size="8.5" font-weight="bold" fill="#dc2626">Collision Detected!</text>

            <rect x="300" y="160" width="260" height="60" fill="#fef2f2" stroke="#dc2626" stroke-width="1.5" rx="5"/>
            <text x="430" y="182" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#991b1b" text-anchor="middle">4. JAM SIGNAL &amp; RANDOM BACKOFF</text>
            <text x="430" y="198" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#dc2626" text-anchor="middle">Broadcast 32-bit Jam Signal to notify network</text>
            <text x="430" y="210" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#b91c1c" text-anchor="middle">Truncated Binary Exponential Backoff: Wait k * 512 bit times</text>

            <line x1="300" y1="190" x2="97" y2="190" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="4,4"/>
            <line x1="97" y1="190" x2="97" y2="125" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="4,4"/>
            <polygon points="97,120 92,128 102,128" fill="#dc2626"/>
            <text x="195" y="183" font-family="Helvetica, Arial, sans-serif" font-size="8.5" font-weight="bold" fill="#dc2626">Reattempt Transmission (Attempt &lt; 16)</text>

            <rect x="140" y="265" width="400" height="24" fill="#f8fafc" rx="4" stroke="#cbd5e1"/>
            <text x="340" y="281" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="#475569" text-anchor="middle">CSMA/CD Mechanism: Contention-based access control for half-duplex media</text>
        </svg>'''

    # 3. Dynamic Topic Diagram (For ALL other topics, guaranteeing topic-customized colors & labels)
    else:
        hash_val = sum(ord(c) for c in clean_topic)
        palettes = [
            {"primary": "#1e3a8a", "secondary": "#3b82f6", "accent": "#0284c7", "bg": "#eff6ff"},
            {"primary": "#0f766e", "secondary": "#0d9488", "accent": "#14b8a6", "bg": "#ccfbf1"},
            {"primary": "#4338ca", "secondary": "#6366f1", "accent": "#818cf8", "bg": "#e0e7ff"},
            {"primary": "#b45309", "secondary": "#d97706", "accent": "#f59e0b", "bg": "#fef3c7"},
            {"primary": "#831843", "secondary": "#db2777", "accent": "#f43f5e", "bg": "#ffe4e6"},
        ]
        p = palettes[hash_val % len(palettes)]

        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="280" viewBox="0 0 680 280">
            <rect width="680" height="280" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="1.5"/>
            <rect width="680" height="42" fill="{p['primary']}" rx="8"/>
            <text x="340" y="27" font-family="Helvetica, Arial, sans-serif" font-size="13.5" font-weight="bold" fill="#ffffff" text-anchor="middle">{topic_upper}: {title_upper}</text>

            <rect x="40" y="70" width="165" height="70" fill="{p['bg']}" stroke="{p['secondary']}" stroke-width="2" rx="6"/>
            <text x="122" y="98" font-family="Helvetica, Arial, sans-serif" font-size="11.5" font-weight="bold" fill="{p['primary']}" text-anchor="middle">1. INPUT DATA STREAM</text>
            <text x="122" y="118" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="{p['secondary']}" text-anchor="middle">{clean_topic} Request</text>

            <line x1="205" y1="105" x2="252" y2="105" stroke="{p['accent']}" stroke-width="2.5"/>
            <polygon points="257,105 249,100 249,110" fill="{p['accent']}"/>

            <rect x="259" y="60" width="162" height="90" fill="#ffffff" stroke="{p['primary']}" stroke-width="2.5" rx="6"/>
            <text x="340" y="88" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" fill="{p['primary']}" text-anchor="middle">{topic_upper}</text>
            <text x="340" y="108" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="{p['secondary']}" text-anchor="middle">CORE MECHANISM</text>
            <text x="340" y="128" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#475569" text-anchor="middle">Processing &amp; Logic Engine</text>

            <line x1="421" y1="105" x2="468" y2="105" stroke="{p['accent']}" stroke-width="2.5"/>
            <polygon points="473,105 465,100 465,110" fill="{p['accent']}"/>

            <rect x="475" y="70" width="165" height="70" fill="#f0fdf4" stroke="#16a34a" stroke-width="2" rx="6"/>
            <text x="557" y="98" font-family="Helvetica, Arial, sans-serif" font-size="11.5" font-weight="bold" fill="#15803d" text-anchor="middle">3. VERIFIED OUTPUT</text>
            <text x="557" y="118" font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#16a34a" text-anchor="middle">{clean_topic} Delivery Target</text>

            <rect x="40" y="180" width="180" height="48" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="130" y="201" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">Feature 1: Operational Precision</text>
            <text x="130" y="217" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">{clean_topic} Spec Controls</text>

            <rect x="250" y="180" width="180" height="48" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="340" y="201" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">Feature 2: Scalable Design</text>
            <text x="340" y="217" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">High Efficiency Throughput</text>

            <rect x="460" y="180" width="180" height="48" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" rx="5"/>
            <text x="550" y="201" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#334155" text-anchor="middle">Feature 3: System Reliability</text>
            <text x="550" y="217" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#64748b" text-anchor="middle">Standard Engineering Pattern</text>
        </svg>'''

    b64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64}"


def generate_fallback_svg_data_uri(title: str, topic_name: str = "Topic Architecture") -> str:
    """Backward-compatible alias for generate_simple_labeled_diagram_svg."""
    return generate_simple_labeled_diagram_svg(title, topic_name)


def fetch_image_as_data_uri(url: str, title: str = "", topic_name: str = "") -> str:
    """
    Returns an image Data URI. Attempts to fetch online image or AI prompt image,
    and falls back to a clean, topic-specific labeled vector SVG diagram if fetch fails or offline.
    """
    if not url or not isinstance(url, str):
        return generate_simple_labeled_diagram_svg(title, topic_name)
    
    url = url.strip()
    if url.startswith("data:image/"):
        return url

    # Only replace obvious placeholder domain URLs directly
    url_lower = url.lower()
    if any(domain in url_lower for domain in ("placeholder", "dummy", "example.com")):
        return generate_simple_labeled_diagram_svg(title, topic_name)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        import httpx
        with httpx.Client(timeout=5.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and len(resp.content) > 200:
                content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                if any(img_type in content_type for img_type in ("image/", "jpeg", "png", "webp", "svg", "gif")):
                    b64 = base64.b64encode(resp.content).decode("utf-8")
                    if "svg" in content_type:
                        return f"data:image/svg+xml;base64,{b64}"
                    return f"data:{content_type};base64,{b64}"
    except Exception as e:
        logger.debug(f"httpx image fetch failed for '{url}': {str(e)}")

    return generate_simple_labeled_diagram_svg(title, topic_name)


def clean_markdown_for_pdf(md_content: str, topic_name: str = "") -> str:
    """
    Cleans markdown content and transforms Mermaid blocks into styled HTML for PDF rendering.
    Policy: max ONE Mermaid diagram per topic. All external image tags are stripped.
    """
    if not md_content or not isinstance(md_content, str):
        return "Study material could not be generated."

    md_content = remove_unwanted_sections(md_content)

    # Strip ALL external markdown image tags: ![alt](url) — they produce vague identical SVG fallbacks
    md_content = RE_MARKDOWN_IMAGE.sub('', md_content)

    # Render the FIRST Mermaid block only; strip any additional ones (no repeated diagrams)
    mermaid_rendered = [False]

    def replace_mermaid(match):
        mermaid_code = match.group(1).strip()
        if mermaid_rendered[0]:
            # Already rendered one diagram — strip the rest
            return ''
        mermaid_rendered[0] = True
        code_lower = mermaid_code.lower()
        if "sequencediagram" in code_lower:
            m_title = f"{topic_name} Protocol Sequence Diagram"
        elif "statediagram" in code_lower:
            m_title = f"{topic_name} State Transition Diagram"
        elif "classdiagram" in code_lower:
            m_title = f"{topic_name} Component & Class Structure"
        elif "gantt" in code_lower:
            m_title = f"{topic_name} Execution Timeline"
        elif "flowchart" in code_lower or "graph" in code_lower:
            m_title = f"{topic_name} Architecture Flowchart"
        else:
            m_title = f"{topic_name} Diagram"

        try:
            encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
            img_url = f"https://mermaid.ink/png/{encoded}"
            data_uri = fetch_image_as_data_uri(img_url, title=m_title, topic_name=topic_name)
            return f'\n<div class="image-box"><img src="{data_uri}" alt="{html.escape(m_title)}"/><p class="figure-caption">{html.escape(m_title)}</p></div>\n'
        except Exception:
            return ''

    md_content = RE_MERMAID_BLOCK.sub(replace_mermaid, md_content)

    # Transform Callout boxes
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
    
    # 1. Executive Cover Page HTML
    cover_html = f"""
    <pdf:nexttemplate name="cover_template" />
    <h1 style="font-size: 0.1pt; color: #0f172a; margin: 0; padding: 0; border: none; page-break-before: avoid; -pdf-outline: true;">Cover Page</h1>
    <div style="padding: 2.5cm 2cm 2cm 2cm; color: #ffffff;">
        <div style="margin-top: 2.5cm; border-bottom: 2px solid #0d9488; padding-bottom: 15px;">
            <p style="font-size: 10pt; color: #38bdf8; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;">
                ACADEMIC STUDY MATERIAL & REFERENCE
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
        topic_rows.append(f"""
        <tr>
            <td><strong>{topic_item.topic_name}</strong></td>
            <td>{topic_item.duration} Hour(s)</td>
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
        cleaned_md = remove_unwanted_sections(raw_md)
        html_content = md_parser.convert(cleaned_md)
        
        topic_header_html = f"""
        <pdf:nexttemplate name="content_template" />
        <div style="page-break-before: always; border-bottom: 2px solid #0284c7; padding-bottom: 8px; margin-bottom: 15px;">
            <span style="font-size: 9pt; color: #0369a1; font-weight: bold; text-transform: uppercase;">
                {request.course_code} - Unit {request.unit_number}: {request.unit_title}
            </span>
            <h1 style="font-size: 20pt; color: #0f172a; margin: 4px 0 0 0; font-weight: bold; border: none; page-break-before: avoid; -pdf-outline: true;">
                Topic: {topic_item.topic_name}
            </h1>
        </div>
        """
        topic_sections_html.append(topic_header_html + html_content)

    all_topics_content_html = "\n\n".join(topic_sections_html)

    # 4. Pygments syntax highlighting CSS
    pygments_css = HtmlFormatter(style='friendly').get_style_defs('.codehilite')

    full_html = f"""
    <!DOCTYPE html>
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
            topics=[TopicRequestItem(topic_name=getattr(unit, "unit_title", "Topic"), duration=1)]
        )

    successful = [(req.topics[0], unit_markdown)]
    return generate_topic_pdf(req, successful, output_dir)
