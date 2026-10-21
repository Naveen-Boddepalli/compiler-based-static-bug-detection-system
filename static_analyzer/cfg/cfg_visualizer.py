"""CFG Visualizer generating Graphviz DOT, JSON graph descriptors, and standalone SVG."""

import html
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple, Optional
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
        """Generates a self-contained SVG diagram of the CFG using hierarchical layered layout."""
        if not self.cfg.blocks:
            return '<svg width="200" height="80"><text x="20" y="40">Empty CFG</text></svg>'

        node_width = 240
        line_height = 18
        header_height = 28
        spacing_x = 40
        spacing_y = 55

        # Theme colors
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

        # 1. Calculate heights for each block
        block_heights: Dict[int, int] = {}
        for b in self.cfg.blocks:
            inst_count = len(b.instructions)
            h = header_height + (inst_count * line_height) + 16
            block_heights[b.id] = max(55, h)

        # 2. Identify Entry and Exit
        entry = self.cfg.entry_block or self.cfg.blocks[0]
        exit_id = self.cfg.exit_block.id if self.cfg.exit_block else -1

        # 3. Detect back-edges (loops) using DFS
        visited: Set[int] = set()
        rec_stack: Set[int] = set()
        back_edges: Set[Tuple[int, int]] = set()

        def dfs(u: BasicBlock):
            visited.add(u.id)
            rec_stack.add(u.id)
            for succ in u.successors:
                if succ.id in rec_stack:
                    back_edges.add((u.id, succ.id))
                elif succ.id not in visited:
                    dfs(succ)
            rec_stack.remove(u.id)

        dfs(entry)

        # 4. Compute topological / longest-path layers on forward DAG
        layers: Dict[int, int] = {entry.id: 0}
        for _ in range(len(self.cfg.blocks)):
            changed = False
            for edge in self.cfg.edges:
                if (edge.from_block_id, edge.to_block_id) in back_edges or edge.to_block_id == exit_id:
                    continue
                if edge.from_block_id in layers:
                    cand = layers[edge.from_block_id] + 1
                    if cand > layers.get(edge.to_block_id, 0):
                        layers[edge.to_block_id] = cand
                        changed = True
            if not changed:
                break

        # Handle any unreachable blocks not reached from entry
        for b in self.cfg.blocks:
            if b.id != exit_id and b.id not in layers:
                succ_layers = [layers[s.id] for s in b.successors if s.id in layers and s.id != exit_id]
                layers[b.id] = max(0, min(succ_layers) - 1) if succ_layers else 1

        # Exit block is placed strictly at the bottom
        max_layer = max(layers.values()) if layers else 0
        if exit_id != -1:
            layers[exit_id] = max_layer + 1

        # 5. Group blocks into layers
        layer_groups: Dict[int, List[BasicBlock]] = defaultdict(list)
        for b in self.cfg.blocks:
            layer_groups[layers[b.id]].append(b)

        # Sort blocks within each layer horizontally (true/then on left, false/else/exit on right)
        def block_sort_key(b: BasicBlock):
            incoming_edges = [e for e in self.cfg.edges if e.to_block_id == b.id]
            has_true = any(e.kind == EdgeKind.TRUE_BRANCH for e in incoming_edges)
            has_false = any(e.kind == EdgeKind.FALSE_BRANCH for e in incoming_edges)
            if has_true and not has_false:
                return 0
            if "then" in b.label or "body" in b.label:
                return 1
            if not has_true and has_false:
                return 3
            if "else" in b.label or "exit" in b.label or "merge" in b.label:
                return 4
            return 2

        for lyr in layer_groups:
            layer_groups[lyr].sort(key=lambda b: (block_sort_key(b), b.id))

        # 6. Calculate canvas dimensions and 2D block positions
        max_blocks_in_layer = max(len(blocks) for blocks in layer_groups.values())
        has_back_edges = bool(back_edges)
        margin_left = 65 if has_back_edges else 40
        margin_right = 40

        content_width = max(520, max_blocks_in_layer * node_width + (max_blocks_in_layer - 1) * spacing_x)
        total_width = content_width + margin_left + margin_right

        positions: Dict[int, Tuple[int, int]] = {}
        cur_y = 30

        for lyr in sorted(layer_groups.keys()):
            row_blocks = layer_groups[lyr]
            k = len(row_blocks)
            row_width = k * node_width + (k - 1) * spacing_x
            start_row_x = margin_left + (content_width - row_width) // 2
            row_max_h = max(block_heights[b.id] for b in row_blocks)

            for i, b in enumerate(row_blocks):
                bx = start_row_x + i * (node_width + spacing_x)
                positions[b.id] = (bx, cur_y)

            cur_y += row_max_h + spacing_y

        total_height = cur_y + 15

        # 7. Render SVG markup
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="100%" height="{total_height}" class="cfg-svg">',
            '<defs>',
            '  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
            f'    <path d="M 0 0 L 10 5 L 0 10 z" fill="{text_secondary}"/>',
            '  </marker>',
            '  <marker id="arrow-true" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
            '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981"/>',
            '  </marker>',
            '  <marker id="arrow-false" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
            '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>',
            '  </marker>',
            '  <marker id="arrow-jump" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
            '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/>',
            '  </marker>',
            '</defs>'
        ]

        # 8. Render Edges
        for edge in self.cfg.edges:
            from_pos = positions.get(edge.from_block_id)
            to_pos = positions.get(edge.to_block_id)
            if not from_pos or not to_pos:
                continue

            fx, fy = from_pos
            fh = block_heights[edge.from_block_id]
            tx, ty = to_pos
            th = block_heights[edge.to_block_id]

            from_layer = layers.get(edge.from_block_id, 0)
            to_layer = layers.get(edge.to_block_id, 0)

            edge_color = text_secondary
            marker_id = "arrow"
            dash_attr = ""

            if edge.kind == EdgeKind.TRUE_BRANCH:
                edge_color = "#10b981"
                marker_id = "arrow-true"
            elif edge.kind == EdgeKind.FALSE_BRANCH:
                edge_color = "#ef4444"
                marker_id = "arrow-false"
            elif edge.kind == EdgeKind.RETURN:
                edge_color = "#94a3b8" if is_dark else "#64748b"
                dash_attr = ' stroke-dasharray="4 3"'
            elif edge.kind == EdgeKind.JUMP:
                edge_color = "#38bdf8"
                marker_id = "arrow-jump"
                dash_attr = ' stroke-dasharray="4 3"'

            # Case A: Loop Back-Edge (curves around the left outside margin)
            if (edge.from_block_id, edge.to_block_id) in back_edges or from_layer >= to_layer:
                start_x = fx
                start_y = fy + fh // 2
                end_x = tx
                end_y = ty + th // 2
                loop_x = min(fx, tx) - 45
                path_d = f"M {start_x} {start_y} C {loop_x} {start_y}, {loop_x} {end_y}, {end_x} {end_y}"

                svg_parts.append(
                    f'<path d="{path_d}" stroke="{edge_color}" stroke-width="2" fill="none" marker-end="url(#{marker_id})"{dash_attr}/>'
                )

                if edge.label:
                    lx = loop_x - 6
                    ly = (start_y + end_y) // 2
                    svg_parts.append(
                        f'<text x="{lx}" y="{ly}" fill="{edge_color}" font-family="monospace" font-size="11" text-anchor="end" font-weight="600" paint-order="stroke fill" stroke="{bg_card}" stroke-width="4px" stroke-linejoin="round">{html.escape(edge.label)}</text>'
                    )
                continue

            # Case B: Forward Edges (downward flow)
            # Separate start anchors for multiple outgoing branches
            from_outgoing = [e for e in self.cfg.edges if e.from_block_id == edge.from_block_id]
            if len(from_outgoing) > 1:
                if edge.kind == EdgeKind.TRUE_BRANCH:
                    start_x = fx + int(node_width * 0.35)
                elif edge.kind == EdgeKind.FALSE_BRANCH:
                    start_x = fx + int(node_width * 0.65)
                else:
                    start_x = fx + int(node_width * 0.5)
            else:
                start_x = fx + int(node_width * 0.5)

            start_y = fy + fh

            # Separate target anchors for multiple incoming edges
            to_incoming = [e for e in self.cfg.edges if e.to_block_id == edge.to_block_id]
            if len(to_incoming) > 1:
                if start_x < tx + node_width // 2:
                    end_x = tx + int(node_width * 0.35)
                elif start_x > tx + node_width // 2:
                    end_x = tx + int(node_width * 0.65)
                else:
                    end_x = tx + int(node_width * 0.5)
            else:
                end_x = tx + int(node_width * 0.5)

            end_y = ty

            mid_y = (start_y + end_y) // 2
            path_d = f"M {start_x} {start_y} C {start_x} {mid_y}, {end_x} {mid_y}, {end_x} {end_y}"

            svg_parts.append(
                f'<path d="{path_d}" stroke="{edge_color}" stroke-width="2" fill="none" marker-end="url(#{marker_id})"{dash_attr}/>'
            )

            # Edge Label with crisp halo background
            if edge.label:
                if edge.kind in (EdgeKind.TRUE_BRANCH, EdgeKind.FALSE_BRANCH):
                    lx = int(0.6 * start_x + 0.4 * end_x)
                    ly = int(0.6 * start_y + 0.4 * end_y) - 6
                    if edge.kind == EdgeKind.TRUE_BRANCH:
                        lx -= 10
                    else:
                        lx += 10
                else:
                    lx = (start_x + end_x) // 2
                    ly = mid_y - 6

                svg_parts.append(
                    f'<text x="{lx}" y="{ly}" fill="{edge_color}" font-family="monospace" font-size="11" text-anchor="middle" font-weight="600" paint-order="stroke fill" stroke="{bg_card}" stroke-width="4px" stroke-linejoin="round">{html.escape(edge.label)}</text>'
                )

        # 9. Render Blocks
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
