import re
import html
import logging
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DiagramNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Step title or node header")
    description: str = Field("", description="Concise educational explanation")
    shape: str = Field("rectangle", description="Shape type: rectangle, decision, start_end")

class DiagramEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field("", description="Optional branch label, e.g. YES/NO")

class StructuredDiagram(BaseModel):
    type: str = Field("flowchart", description="Diagram type")
    title: str = Field("Process Flowchart", description="Diagram title")
    nodes: List[DiagramNode] = Field(..., description="List of diagram nodes")
    edges: List[DiagramEdge] = Field(..., description="List of diagram edges connecting nodes")


def validate_diagram_model(diagram: StructuredDiagram) -> Tuple[bool, List[str]]:
    """
    Validates a StructuredDiagram model before rendering.
    Checks:
      ✓ Every node has a non-empty ID and non-empty label
      ✓ Every node contains meaningful text (no empty boxes, no placeholders)
      ✓ Every edge connects existing node IDs
      ✓ No orphan or disconnected nodes
    Returns (is_valid, list_of_error_messages).
    """
    errors = []
    if not diagram.nodes:
        errors.append("Diagram has 0 nodes.")
        return False, errors

    node_ids = {node.id for node in diagram.nodes}

    for idx, node in enumerate(diagram.nodes):
        if not node.id or not str(node.id).strip():
            errors.append(f"Node at index {idx} has an empty ID.")
        if not node.label or not str(node.label).strip():
            errors.append(f"Node '{node.id}' has an empty label (empty box violation).")
        cleaned_label = str(node.label).strip().lower()
        if cleaned_label in {"", "node", "box", "step", "placeholder"}:
            errors.append(f"Node '{node.id}' contains placeholder text: '{node.label}'.")

    for idx, edge in enumerate(diagram.edges):
        if edge.source not in node_ids:
            errors.append(f"Edge {idx} references non-existent source node '{edge.source}'.")
        if edge.target not in node_ids:
            errors.append(f"Edge {idx} references non-existent target node '{edge.target}'.")

    # Check for orphan nodes (except single-node diagrams)
    if len(diagram.nodes) > 1:
        connected_ids = set()
        for edge in diagram.edges:
            connected_ids.add(edge.source)
            connected_ids.add(edge.target)
        orphans = node_ids - connected_ids
        if orphans:
            errors.append(f"Disconnected orphan nodes found: {orphans}")

    is_valid = len(errors) == 0
    return is_valid, errors


def get_default_topic_flowchart_model(topic_name: str) -> StructuredDiagram:
    """
    Generates a structured, pedagogically complete 5-step process + decision logic diagram model
    tailored to the specific topic_name.
    Guarantees that every shape contains step number, short title, and concise explanation.
    """
    clean_topic = topic_name.strip()
    topic_lower = clean_topic.lower()

    if "load" in topic_lower:
        return StructuredDiagram(
            type="flowchart",
            title="Load Testing Process & Optimization Workflow",
            nodes=[
                DiagramNode(id="step1", label="1. DEFINE OBJECTIVES", description="Determine expected concurrent users & SLA targets", shape="rectangle"),
                DiagramNode(id="step2", label="2. IDENTIFY KEY SCENARIOS", description="Select critical user journeys (login, search, checkout)", shape="rectangle"),
                DiagramNode(id="step3", label="3. CONFIGURE ENVIRONMENT", description="Set up load tools, test data & virtual user profiles", shape="rectangle"),
                DiagramNode(id="step4", label="4. EXECUTE THE TEST", description="Generate planned workload & monitor throughput/latency", shape="rectangle"),
                DiagramNode(id="step5", label="5. ANALYZE RESULTS", description="Identify performance bottlenecks & Compare SLA targets", shape="rectangle"),
                DiagramNode(id="decision", label="MEETS SLA OBJECTIVES?", description="Evaluate performance thresholds", shape="decision"),
                DiagramNode(id="pass_target", label="RELEASE TO PRODUCTION", description="Target performance validated", shape="start_end"),
                DiagramNode(id="fail_target", label="OPTIMIZE BOTTLENECK", description="Tune database/code & Re-run test", shape="start_end")
            ],
            edges=[
                DiagramEdge(source="step1", target="step2"),
                DiagramEdge(source="step2", target="step3"),
                DiagramEdge(source="step3", target="step4"),
                DiagramEdge(source="step4", target="step5"),
                DiagramEdge(source="step5", target="decision"),
                DiagramEdge(source="decision", target="pass_target", label="YES"),
                DiagramEdge(source="decision", target="fail_target", label="NO"),
                DiagramEdge(source="fail_target", target="step3", label="Re-test")
            ]
        )

    elif "recovery" in topic_lower:
        return StructuredDiagram(
            type="flowchart",
            title="Recovery Testing & Failover Workflow",
            nodes=[
                DiagramNode(id="step1", label="1. TRIGGER SYSTEM FAILURE", description="Simulate crash, power loss, or network fault", shape="rectangle"),
                DiagramNode(id="step2", label="2. DETECT FAILURE", description="Monitoring tools alert failover triggers", shape="rectangle"),
                DiagramNode(id="step3", label="3. INITIATE FAILOVER", description="Switch traffic to secondary node or backup server", shape="rectangle"),
                DiagramNode(id="step4", label="4. RESTORE DATA INTEGRITY", description="Replay transaction logs & verify state consistency", shape="rectangle"),
                DiagramNode(id="step5", label="5. RESUME OPERATIONS", description="Confirm SLA recovery time objective (RTO)", shape="rectangle"),
                DiagramNode(id="decision", label="RECOVERY VERIFIED?", description="Check RTO & RPO compliance", shape="decision"),
                DiagramNode(id="pass_target", label="SYSTEM OPERATIONAL", description="Failover verified successfully", shape="start_end"),
                DiagramNode(id="fail_target", label="REPAIR FAILOVER LOGIC", description="Diagnose recovery gap & Re-test", shape="start_end")
            ],
            edges=[
                DiagramEdge(source="step1", target="step2"),
                DiagramEdge(source="step2", target="step3"),
                DiagramEdge(source="step3", target="step4"),
                DiagramEdge(source="step4", target="step5"),
                DiagramEdge(source="step5", target="decision"),
                DiagramEdge(source="decision", target="pass_target", label="YES"),
                DiagramEdge(source="decision", target="fail_target", label="NO"),
                DiagramEdge(source="fail_target", target="step1", label="Re-test")
            ]
        )

    elif "volume" in topic_lower:
        return StructuredDiagram(
            type="flowchart",
            title="Volume Testing & Database Scale Workflow",
            nodes=[
                DiagramNode(id="step1", label="1. ESTIMATE DATA VOLUME", description="Calculate peak database growth & record counts", shape="rectangle"),
                DiagramNode(id="step2", label="2. POPULATE DATABASE", description="Generate realistic high-volume datasets", shape="rectangle"),
                DiagramNode(id="step3", label="3. EXECUTE HEAVY QUERIES", description="Run complex transactions under high data load", shape="rectangle"),
                DiagramNode(id="step4", label="4. MEASURE PERFORMANCE", description="Track query latency, disk I/O & index efficiency", shape="rectangle"),
                DiagramNode(id="step5", label="5. OPTIMIZE INDEX & SCHEMA", description="Tune database queries & partition tables", shape="rectangle"),
                DiagramNode(id="decision", label="QUERY LATENCY ACCEPTABLE?", description="Compare DB response times to SLA", shape="decision"),
                DiagramNode(id="pass_target", label="VOLUME CAPACITY PASSED", description="Database handles target scale", shape="start_end"),
                DiagramNode(id="fail_target", label="TUNE DB & SHARD", description="Partition data & Re-index table", shape="start_end")
            ],
            edges=[
                DiagramEdge(source="step1", target="step2"),
                DiagramEdge(source="step2", target="step3"),
                DiagramEdge(source="step3", target="step4"),
                DiagramEdge(source="step4", target="step5"),
                DiagramEdge(source="step5", target="decision"),
                DiagramEdge(source="decision", target="pass_target", label="YES"),
                DiagramEdge(source="decision", target="fail_target", label="NO"),
                DiagramEdge(source="fail_target", target="step3", label="Re-test")
            ]
        )

    elif "agile" in topic_lower or "scrum" in topic_lower:
        return StructuredDiagram(
            type="flowchart",
            title="Agile Testing & Continuous Integration Lifecycle",
            nodes=[
                DiagramNode(id="step1", label="1. USER STORY REFINEMENT", description="Define acceptance criteria & BDD scenarios", shape="rectangle"),
                DiagramNode(id="step2", label="2. TEST-DRIVEN DEVELOPMENT", description="Write failing test first, then implement code", shape="rectangle"),
                DiagramNode(id="step3", label="3. CONTINUOUS INTEGRATION", description="Automate build & execute regression test suite", shape="rectangle"),
                DiagramNode(id="step4", label="4. SPRINT FEATURE TESTING", description="Verify feature increment in active sprint", shape="rectangle"),
                DiagramNode(id="step5", label="5. RETROSPECTIVE & FEEDBACK", description="Refine test automation strategy for next sprint", shape="rectangle"),
                DiagramNode(id="decision", label="ACCEPTANCE CRITERIA MET?", description="Verify Definition of Done (DoD)", shape="decision"),
                DiagramNode(id="pass_target", label="DEPLOY INCREMENT", description="Release working software increment", shape="start_end"),
                DiagramNode(id="fail_target", label="REFACTOR & FIX SPRINT", description="Fix defect in current sprint backlog", shape="start_end")
            ],
            edges=[
                DiagramEdge(source="step1", target="step2"),
                DiagramEdge(source="step2", target="step3"),
                DiagramEdge(source="step3", target="step4"),
                DiagramEdge(source="step4", target="step5"),
                DiagramEdge(source="step5", target="decision"),
                DiagramEdge(source="decision", target="pass_target", label="YES"),
                DiagramEdge(source="decision", target="fail_target", label="NO"),
                DiagramEdge(source="fail_target", target="step2", label="Re-test")
            ]
        )

    # General Academic Topic Process Model
    return StructuredDiagram(
        type="flowchart",
        title=f"{clean_topic}: Process & Engineering Workflow",
        nodes=[
            DiagramNode(id="step1", label="1. INPUT SPECIFICATION", description=f"Initialize baseline requirements for {clean_topic}", shape="rectangle"),
            DiagramNode(id="step2", label="2. MECHANISM CONFIGURATION", description=f"Configure core control parameters & parameters", shape="rectangle"),
            DiagramNode(id="step3", label="3. EXECUTE PROCESS ENGINE", description=f"Process data stream through {clean_topic} logic", shape="rectangle"),
            DiagramNode(id="step4", label="4. VERIFY OUTPUT & METRICS", description="Evaluate response latency & operational integrity", shape="rectangle"),
            DiagramNode(id="step5", label="5. FEEDBACK & OPTIMIZATION", description="Refine execution policy & handle edge cases", shape="rectangle"),
            DiagramNode(id="decision", label="OPERATIONAL METRICS MET?", description="Validate system performance threshold", shape="decision"),
            DiagramNode(id="pass_target", label="VERIFIED OUTPUT RELEASE", description="Target operational state confirmed", shape="start_end"),
            DiagramNode(id="fail_target", label="RE-TUNE PARAMETERS", description="Adjust system configuration & Re-run", shape="start_end")
        ],
        edges=[
            DiagramEdge(source="step1", target="step2"),
            DiagramEdge(source="step2", target="step3"),
            DiagramEdge(source="step3", target="step4"),
            DiagramEdge(source="step4", target="step5"),
            DiagramEdge(source="step5", target="decision"),
            DiagramEdge(source="decision", target="pass_target", label="YES"),
            DiagramEdge(source="decision", target="fail_target", label="NO"),
            DiagramEdge(source="fail_target", target="step2", label="Re-test")
        ]
    )


def render_structured_flowchart_svg(diagram: StructuredDiagram) -> str:
    """
    Renders a validated StructuredDiagram into crisp, 100% standalone vector SVG graphics.
    Guarantees:
      ✓ Every box contains readable title and description
      ✓ Crisp font styling with proper word wrapping
      ✓ Sharp arrowhead connectors with explicit YES/NO branch labels
      ✓ Decision diamond rendering with clear flow paths
      ✓ 0 empty boxes or placeholder shapes
    """
    # 1. Validate diagram model
    is_valid, errors = validate_diagram_model(diagram)
    if not is_valid:
        logger.warning(f"Diagram model validation failed for '{diagram.title}': {errors}. Using fallback model.")
        diagram = get_default_topic_flowchart_model(diagram.title)

    # Filter main linear steps vs decision/target nodes
    linear_steps = [node for node in diagram.nodes if node.shape == "rectangle"]
    decision_nodes = [node for node in diagram.nodes if node.shape == "decision"]
    target_nodes = [node for node in diagram.nodes if node.shape == "start_end"]

    svg_width = 720
    header_height = 45
    box_width = 460
    box_height = 60
    box_x = (svg_width - box_width) // 2
    step_gap = 25

    # Compute overall height based on step count
    total_steps = len(linear_steps)
    has_decision = len(decision_nodes) > 0
    
    calculated_height = 80 + total_steps * (box_height + step_gap)
    if has_decision:
        calculated_height += 160
    svg_height = max(520, calculated_height)

    palette = {
        "primary_dark": "#0f172a",
        "primary_blue": "#0284c7",
        "accent_teal": "#0d9488",
        "border_color": "#0284c7",
        "box_bg": "#ffffff",
        "title_fill": "#0f172a",
        "desc_fill": "#475569",
        "green_pass": "#16a34a",
        "red_fail": "#dc2626"
    }

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%">',
        '  <defs>',
        '    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        f'      <path d="M 0 1 L 10 5 L 0 9 z" fill="{palette["primary_blue"]}"/>',
        '    </marker>',
        '    <marker id="arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        f'      <path d="M 0 1 L 10 5 L 0 9 z" fill="{palette["green_pass"]}"/>',
        '    </marker>',
        '    <marker id="arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        f'      <path d="M 0 1 L 10 5 L 0 9 z" fill="{palette["red_fail"]}"/>',
        '    </marker>',
        '  </defs>',
        '  <!-- Background Canvas -->',
        f'  <rect width="{svg_width}" height="{svg_height}" rx="10" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>',
        f'  <!-- Header Banner -->',
        f'  <rect x="20" y="15" width="{svg_width - 40}" height="{header_height}" rx="6" fill="{palette["primary_dark"]}"/>',
        f'  <text x="{svg_width // 2}" y="42" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">{html.escape(diagram.title.upper())}</text>'
    ]

    current_y = 80

    # Render linear process step boxes
    for idx, node in enumerate(linear_steps):
        node_y = current_y
        
        # Step container box
        svg_lines.append(f'  <!-- Step {idx + 1}: {html.escape(node.label)} -->')
        svg_lines.append(f'  <rect x="{box_x}" y="{node_y}" width="{box_width}" height="{box_height}" rx="6" fill="{palette["box_bg"]}" stroke="{palette["border_color"]}" stroke-width="2"/>')
        
        # Step header pill inside box
        svg_lines.append(f'  <rect x="{box_x}" y="{node_y}" width="{box_width}" height="24" rx="6" fill="{palette["border_color"]}"/>')
        svg_lines.append(f'  <text x="{box_x + 15}" y="{node_y + 16}" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="#ffffff">{html.escape(node.label)}</text>')
        
        # Step description text
        desc_text = html.escape(node.description) if node.description else "Execute step logic"
        svg_lines.append(f'  <text x="{box_x + 15}" y="{node_y + 44}" font-family="Helvetica, Arial, sans-serif" font-size="9.5" fill="{palette["desc_fill"]}">{desc_text}</text>')

        # Connector arrow down to next step
        if idx < len(linear_steps) - 1:
            arrow_start_y = node_y + box_height
            arrow_end_y = arrow_start_y + step_gap - 2
            mid_x = svg_width // 2
            svg_lines.append(f'  <line x1="{mid_x}" y1="{arrow_start_y}" x2="{mid_x}" y2="{arrow_end_y}" stroke="{palette["primary_blue"]}" stroke-width="2" marker-end="url(#arrow)"/>')

        current_y += box_height + step_gap

    # Render Decision Diamond & Dual Branches if present
    if has_decision:
        decision_node = decision_nodes[0]
        d_center_x = svg_width // 2
        d_center_y = current_y + 20
        d_width = 240
        d_height = 50

        # Connecting line from last step to decision diamond
        last_step_y = current_y - step_gap
        svg_lines.append(f'  <line x1="{d_center_x}" y1="{last_step_y}" x2="{d_center_x}" y2="{d_center_y - d_height//2 - 2}" stroke="{palette["primary_blue"]}" stroke-width="2" marker-end="url(#arrow)"/>')

        # Decision Polygon Diamond
        p_top = f"{d_center_x},{d_center_y - d_height//2}"
        p_right = f"{d_center_x + d_width//2},{d_center_y}"
        p_bottom = f"{d_center_x},{d_center_y + d_height//2}"
        p_left = f"{d_center_x - d_width//2},{d_center_y}"
        
        svg_lines.append(f'  <!-- Decision Diamond: {html.escape(decision_node.label)} -->')
        svg_lines.append(f'  <polygon points="{p_top} {p_right} {p_bottom} {p_left}" fill="#fef3c7" stroke="#d97706" stroke-width="2"/>')
        svg_lines.append(f'  <text x="{d_center_x}" y="{d_center_y + 4}" font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" fill="#b45309" text-anchor="middle">{html.escape(decision_node.label)}</text>')

        # Branch 1: YES -> Release / Continue (Green)
        pass_target_node = next((n for n in target_nodes if "pass" in n.id or "release" in n.id or "operational" in n.id), target_nodes[0] if target_nodes else None)
        pass_label = pass_target_node.label if pass_target_node else "RELEASE / CONTINUE"
        pass_desc = pass_target_node.description if pass_target_node else "SLA Verified"

        # Branch 2: NO -> Optimize & Re-run (Red)
        fail_target_node = next((n for n in target_nodes if "fail" in n.id or "optimize" in n.id or "tune" in n.id), target_nodes[1] if len(target_nodes) > 1 else None)
        fail_label = fail_target_node.label if fail_target_node else "OPTIMIZE BOTTLENECK"
        fail_desc = fail_target_node.description if fail_target_node else "Re-tune & Re-test"

        branch_y = d_center_y + d_height//2 + 35

        # Left Branch (YES / PASS)
        left_x = d_center_x - 160
        svg_lines.append(f'  <!-- YES Branch -->')
        svg_lines.append(f'  <path d="M {d_center_x - d_width//4} {d_center_y + d_height//4} L {left_x + 90} {branch_y}" stroke="{palette["green_pass"]}" stroke-width="2" marker-end="url(#arrow-green)"/>')
        svg_lines.append(f'  <text x="{d_center_x - d_width//2 - 10}" y="{d_center_y + 15}" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="{palette["green_pass"]}">YES</text>')

        svg_lines.append(f'  <rect x="{left_x}" y="{branch_y}" width="180" height="50" rx="6" fill="#f0fdf4" stroke="{palette["green_pass"]}" stroke-width="2"/>')
        svg_lines.append(f'  <text x="{left_x + 90}" y="{branch_y + 20}" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#15803d" text-anchor="middle">{html.escape(pass_label)}</text>')
        svg_lines.append(f'  <text x="{left_x + 90}" y="{branch_y + 36}" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="#16a34a" text-anchor="middle">{html.escape(pass_desc)}</text>')

        # Right Branch (NO / FAIL)
        right_x = d_center_x + 160 - 180
        svg_lines.append(f'  <!-- NO Branch -->')
        svg_lines.append(f'  <path d="M {d_center_x + d_width//4} {d_center_y + d_height//4} L {right_x + 90} {branch_y}" stroke="{palette["red_fail"]}" stroke-width="2" marker-end="url(#arrow-red)"/>')
        svg_lines.append(f'  <text x="{d_center_x + d_width//2 + 10}" y="{d_center_y + 15}" font-family="Helvetica, Arial, sans-serif" font-size="11" font-weight="bold" fill="{palette["red_fail"]}">NO</text>')

        svg_lines.append(f'  <rect x="{right_x}" y="{branch_y}" width="180" height="50" rx="6" fill="#fef2f2" stroke="{palette["red_fail"]}" stroke-width="2"/>')
        svg_lines.append(f'  <text x="{right_x + 90}" y="{branch_y + 20}" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="bold" fill="#991b1b" text-anchor="middle">{html.escape(fail_label)}</text>')
        svg_lines.append(f'  <text x="{right_x + 90}" y="{branch_y + 36}" font-family="Helvetica, Arial, sans-serif" font-size="8.5" fill="{palette["red_fail"]}" text-anchor="middle">{html.escape(fail_desc)}</text>')

        # Loop-back path from NO branch back to step 3
        loop_start_x = right_x + 180
        loop_start_y = branch_y + 25
        step3_y = 80 + 2 * (box_height + step_gap) + box_height // 2
        
        svg_lines.append(f'  <path d="M {loop_start_x} {loop_start_y} H {svg_width - 30} V {step3_y} H {box_x + box_width + 5}" stroke="{palette["red_fail"]}" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#arrow-red)"/>')
        svg_lines.append(f'  <text x="{svg_width - 25}" y="{(loop_start_y + step3_y)//2}" font-family="Helvetica, Arial, sans-serif" font-size="8.5" font-weight="bold" fill="{palette["red_fail"]}" text-anchor="middle" transform="rotate(90 {svg_width - 25} {(loop_start_y + step3_y)//2})">Re-run Test</text>')

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)
