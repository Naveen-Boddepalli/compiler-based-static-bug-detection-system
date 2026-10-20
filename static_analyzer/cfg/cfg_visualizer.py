"""CFG Visualizer generating Graphviz DOT, JSON graph descriptors, and standalone SVG."""

import html
from typing import Dict, Any, List
from .basic_block import ControlFlowGraph, BasicBlock, EdgeKind


class CFGVisualizer:
    """Generates visual representations of Control Flow Graphs."""

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg

    def to_dot(self) -> str:
        """Generates standard Graphviz DOT format representation."""
        lines = [
            f'digraph "{self.cfg.function_name}" {{',
            '    rankdir=TB;',
            '    node [shape=box, style="filled,rounded", fontname="Courier", fontsize=11, margin=0.2];',
            '    edge [fontname="Courier", fontsize=10];',
            ''
        ]

        for block in self.cfg.blocks:
            label_parts = [f"<b>{block.label}</b>"]
            if block.instructions:
                label_parts.append("---")
                for inst in block.instructions:
                    esc_text = html.escape(inst.text)
                    label_parts.append(esc_text)

            label_html = f"<{ '<br align=\"left\"/>'.join(label_parts) }>"

            # Styling based on reachability and role
            if not block.is_reachable and not block.is_exit:
                color = '#ffcccc'
                border = '#cc0000'
            elif block.is_entry:
                color = '#e6f3ff'
                border = '#0066cc'
            elif block.is_exit:
                color = '#e6ffe6'
                border = '#009933'
            else:
                color = '#f9f9f9'
                border = '#cccccc'

            lines.append(f'    b{block.id} [label={label_html}, fillcolor="{color}", color="{border}"];')

        lines.append('')
        for edge in self.cfg.edges:
            attrs = []
            if edge.kind == EdgeKind.TRUE_BRANCH:
                attrs.append('label="true", color="#008800", fontcolor="#008800"')
            elif edge.kind == EdgeKind.FALSE_BRANCH:
                attrs.append('label="false", color="#cc0000", fontcolor="#cc0000"')
            elif edge.kind == EdgeKind.RETURN:
                attrs.append('label="return", color="#666666", style="dashed"')
            elif edge.kind == EdgeKind.JUMP:
                attrs.append('label="jump", color="#0055aa", style="dashed"')

            attr_str = f" [{', '.join(attrs)}]" if attrs else ""
            lines.append(f'    b{edge.from_block_id} -> b{edge.to_block_id}{attr_str};')

        lines.append('}')
        return '\n'.join(lines)

    def to_svg(self, is_dark: bool = False) -> str:
        """Generates a self-contained SVG diagram of the CFG without requiring external graphviz."""
        if not self.cfg.blocks:
            return '<svg width="200" height="80"><text x="20" y="40">Empty CFG</text></svg>'

        # Simple hierarchical layout
        node_width = 240
        line_height = 18
        header_height = 28
        padding_y = 40

        # Colors
        bg_card = "#1e222b" if is_dark else "#ffffff"
        text_primary = "#f0f6fc" if is_dark else "#0f172a"
        text_secondary = "#8b949e" if is_dark else "#64748b"
        border_normal = "#30363d" if is_dark else "#e2e8f0"
        border_unreachable = "#ef4444"
        bg_unreachable = "#3b1212" if is_dark else "#fef2f2"
        border_entry = "#38bdf8"
        bg_entry = "#082f49" if is_dark else "#f0f9ff"
        border_exit = "#4ade80"
        bg_exit = "#052e16" if is_dark else "#f0fdf4"

        # Calculate heights for each block
        block_heights = {}
        for b in self.cfg.blocks:
            inst_count = len(b.instructions)
            h = header_height + (inst_count * line_height) + 16
            block_heights[b.id] = max(55, h)

        # Place blocks vertically in order with slight branching horizontal offsets
        positions = {}
        cur_y = 30
        branch_offset = 0

        for b in self.cfg.blocks:
            # Shift branches slightly for visual separation
            x = 180
            if "then" in b.label:
                x = 60
            elif "else" in b.label:
                x = 300

            positions[b.id] = (x, cur_y)
            cur_y += block_heights[b.id] + padding_y

        total_width = 540
        total_height = cur_y + 20

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="100%" height="{total_height}" class="cfg-svg">',
            '<defs>',
            '  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            f'    <path d="M 0 0 L 10 5 L 0 10 z" fill="{text_secondary}"/>',
            '  </marker>',
            '  <marker id="arrow-true" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981"/>',
            '  </marker>',
            '  <marker id="arrow-false" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>',
            '  </marker>',
            '</defs>'
        ]

        # Render edges first
        for edge in self.cfg.edges:
            from_pos = positions.get(edge.from_block_id)
            to_pos = positions.get(edge.to_block_id)
            if not from_pos or not to_pos:
                continue

            fx, fy = from_pos
            fh = block_heights[edge.from_block_id]
            tx, ty = to_pos

            # Start at bottom center of from_block, end at top center of to_block
            start_x = fx + node_width // 2
            start_y = fy + fh
            end_x = tx + node_width // 2
            end_y = ty

            edge_color = text_secondary
            marker_id = "arrow"

            if edge.kind == EdgeKind.TRUE_BRANCH:
                edge_color = "#10b981"
                marker_id = "arrow-true"
            elif edge.kind == EdgeKind.FALSE_BRANCH:
                edge_color = "#ef4444"
                marker_id = "arrow-false"

            # Curved path or straight line
            mid_y = (start_y + end_y) // 2
            path_d = f"M {start_x} {start_y} C {start_x} {mid_y}, {end_x} {mid_y}, {end_x} {end_y}"

            svg_parts.append(
                f'<path d="{path_d}" stroke="{edge_color}" stroke-width="2" fill="none" marker-end="url(#{marker_id})"/>'
            )

            # Label on edge
            if edge.label:
                lx = (start_x + end_x) // 2
                ly = mid_y - 4
                svg_parts.append(
                    f'<text x="{lx}" y="{ly}" fill="{edge_color}" font-family="monospace" font-size="11" text-anchor="middle" font-weight="600">{html.escape(edge.label)}</text>'
                )

        # Render blocks
        for b in self.cfg.blocks:
            x, y = positions[b.id]
            h = block_heights[b.id]

            fill_c = bg_card
            border_c = border_normal
            badge_text = ""

            if not b.is_reachable and not b.is_exit:
                fill_c = bg_unreachable
                border_c = border_unreachable
                badge_text = "UNREACHABLE"
            elif b.is_entry:
                fill_c = bg_entry
                border_c = border_entry
                badge_text = "ENTRY"
            elif b.is_exit:
                fill_c = bg_exit
                border_c = border_exit
                badge_text = "EXIT"

            svg_parts.append(f'<g class="cfg-node" data-block-id="{b.id}">')
            svg_parts.append(
                f'  <rect x="{x}" y="{y}" width="{node_width}" height="{h}" rx="6" ry="6" fill="{fill_c}" stroke="{border_c}" stroke-width="1.5"/>'
            )

            # Header
            header_y = y + 18
            svg_parts.append(
                f'  <text x="{x + 12}" y="{header_y}" fill="{text_primary}" font-family="monospace" font-size="12" font-weight="bold">{html.escape(b.label)}</text>'
            )

            if badge_text:
                svg_parts.append(
                    f'  <text x="{x + node_width - 12}" y="{header_y}" fill="{border_c}" font-family="monospace" font-size="10" text-anchor="end" font-weight="bold">[{badge_text}]</text>'
                )

            # Divider
            div_y = y + header_height
            svg_parts.append(
                f'  <line x1="{x}" y1="{div_y}" x2="{x + node_width}" y2="{div_y}" stroke="{border_c}" stroke-width="1" stroke-opacity="0.4"/>'
            )

            # Instructions
            inst_y = div_y + 16
            for inst in b.instructions:
                esc_inst = html.escape(inst.text)
                if len(esc_inst) > 28:
                    esc_inst = esc_inst[:25] + "..."
                svg_parts.append(
                    f'  <text x="{x + 12}" y="{inst_y}" fill="{text_secondary}" font-family="monospace" font-size="11">{esc_inst}</text>'
                )
                inst_y += line_height

            svg_parts.append('</g>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)
