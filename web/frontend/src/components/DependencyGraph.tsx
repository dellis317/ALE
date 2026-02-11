import { useState, useMemo, useRef, useEffect } from 'react';
import type { IRDependency } from '../types';

interface DependencyGraphProps {
  imports: IRDependency[];
  modulePath: string;
}

interface GraphNode {
  id: string;
  label: string;
  fullPath: string;
  x: number;
  y: number;
  isExternal: boolean;
  isCurrent: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  kind: string;
  isExternal: boolean;
}

function truncateLabel(label: string, maxLen: number = 20): string {
  if (label.length <= maxLen) return label;
  const parts = label.split(/[./]/);
  if (parts.length > 1) {
    const last = parts[parts.length - 1];
    if (last.length <= maxLen) return last;
    return last.slice(0, maxLen - 3) + '...';
  }
  return label.slice(0, maxLen - 3) + '...';
}

function getModuleName(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/');
  const file = parts[parts.length - 1];
  return file.replace(/\.[^/.]+$/, '');
}

export default function DependencyGraph({ imports, modulePath }: DependencyGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const { nodes, edges } = useMemo(() => {
    if (!imports || imports.length === 0) {
      return { nodes: [], edges: [] };
    }

    const nodeMap = new Map<string, { isExternal: boolean; fullPath: string }>();
    const edgeList: GraphEdge[] = [];

    // Current module node
    const currentModuleName = getModuleName(modulePath);
    nodeMap.set(currentModuleName, { isExternal: false, fullPath: modulePath });

    // Process imports
    for (const imp of imports) {
      const targetName = truncateLabel(imp.target, 24);
      if (!nodeMap.has(targetName)) {
        nodeMap.set(targetName, {
          isExternal: imp.is_external,
          fullPath: imp.target,
        });
      }

      edgeList.push({
        source: targetName,
        target: currentModuleName,
        kind: imp.kind,
        isExternal: imp.is_external,
      });
    }

    // Separate into internal and external
    const internalNodes: string[] = [];
    const externalNodes: string[] = [];

    for (const [name, info] of nodeMap) {
      if (name === currentModuleName) continue;
      if (info.isExternal) {
        externalNodes.push(name);
      } else {
        internalNodes.push(name);
      }
    }

    // Sort for consistent ordering
    internalNodes.sort();
    externalNodes.sort();

    // Layout calculation
    const width = containerWidth;
    const nodeRadius = 28;
    const verticalSpacing = 70;
    const leftColumnX = width * 0.2;
    const centerX = width * 0.5;
    const rightColumnX = width * 0.8;

    const maxColumnNodes = Math.max(internalNodes.length, externalNodes.length, 1);
    const svgHeight = Math.max(300, (maxColumnNodes + 1) * verticalSpacing + 80);
    const centerY = svgHeight / 2;

    const graphNodes: GraphNode[] = [];

    // Current module node (center)
    const currentInfo = nodeMap.get(currentModuleName)!;
    graphNodes.push({
      id: currentModuleName,
      label: currentModuleName,
      fullPath: currentInfo.fullPath,
      x: centerX,
      y: centerY,
      isExternal: false,
      isCurrent: true,
    });

    // Internal dep nodes (left column)
    const internalStartY =
      centerY - ((internalNodes.length - 1) * verticalSpacing) / 2;
    internalNodes.forEach((name, i) => {
      const info = nodeMap.get(name)!;
      graphNodes.push({
        id: name,
        label: name,
        fullPath: info.fullPath,
        x: leftColumnX,
        y: internalStartY + i * verticalSpacing,
        isExternal: false,
        isCurrent: false,
      });
    });

    // External dep nodes (right column)
    const externalStartY =
      centerY - ((externalNodes.length - 1) * verticalSpacing) / 2;
    externalNodes.forEach((name, i) => {
      const info = nodeMap.get(name)!;
      graphNodes.push({
        id: name,
        label: name,
        fullPath: info.fullPath,
        x: rightColumnX,
        y: externalStartY + i * verticalSpacing,
        isExternal: true,
        isCurrent: false,
      });
    });

    return { nodes: graphNodes, edges: edgeList };
  }, [imports, modulePath, containerWidth]);

  if (!imports || imports.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        No dependencies found
      </div>
    );
  }

  const svgHeight = Math.max(
    300,
    (Math.max(
      nodes.filter((n) => !n.isCurrent && !n.isExternal).length,
      nodes.filter((n) => n.isExternal).length,
      1
    ) + 1) * 70 + 80
  );

  const activeNode = hoveredNode || selectedNode;

  const isEdgeHighlighted = (edge: GraphEdge) => {
    if (!activeNode) return false;
    return edge.source === activeNode || edge.target === activeNode;
  };

  const isEdgeDimmed = (edge: GraphEdge) => {
    if (!activeNode) return false;
    return !isEdgeHighlighted(edge);
  };

  const isNodeDimmed = (node: GraphNode) => {
    if (!activeNode) return false;
    if (node.id === activeNode) return false;
    // Check if connected to active node
    return !edges.some(
      (e) =>
        (e.source === activeNode && e.target === node.id) ||
        (e.target === activeNode && e.source === node.id)
    );
  };

  const getNodeColor = (node: GraphNode) => {
    if (node.isCurrent) return { fill: '#6366f1', stroke: '#4338ca', text: '#ffffff' };
    if (node.isExternal) return { fill: '#fb923c', stroke: '#ea580c', text: '#ffffff' };
    return { fill: '#3b82f6', stroke: '#2563eb', text: '#ffffff' };
  };

  const getEdgeColor = (edge: GraphEdge) => {
    if (isEdgeHighlighted(edge)) return '#6366f1';
    if (edge.isExternal) return '#fdba74';
    return '#93c5fd';
  };

  const nodeById = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div ref={containerRef} className="w-full">
      <svg
        ref={svgRef}
        width="100%"
        height={svgHeight}
        viewBox={`0 0 ${containerWidth} ${svgHeight}`}
        className="overflow-visible"
      >
        {/* Arrow marker definitions */}
        <defs>
          <marker
            id="arrowhead-default"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#93c5fd" />
          </marker>
          <marker
            id="arrowhead-external"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#fdba74" />
          </marker>
          <marker
            id="arrowhead-highlight"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#6366f1" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((edge, i) => {
          const sourceNode = nodeById.get(edge.source);
          const targetNode = nodeById.get(edge.target);
          if (!sourceNode || !targetNode) return null;

          const nodeRadius = 28;
          const dx = targetNode.x - sourceNode.x;
          const dy = targetNode.y - sourceNode.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist === 0) return null;

          const unitX = dx / dist;
          const unitY = dy / dist;

          const startX = sourceNode.x + unitX * nodeRadius;
          const startY = sourceNode.y + unitY * nodeRadius;
          const endX = targetNode.x - unitX * (nodeRadius + 10);
          const endY = targetNode.y - unitY * (nodeRadius + 10);

          const color = getEdgeColor(edge);
          const highlighted = isEdgeHighlighted(edge);
          const dimmed = isEdgeDimmed(edge);
          const markerId = highlighted
            ? 'arrowhead-highlight'
            : edge.isExternal
              ? 'arrowhead-external'
              : 'arrowhead-default';

          return (
            <line
              key={`edge-${i}`}
              x1={startX}
              y1={startY}
              x2={endX}
              y2={endY}
              stroke={color}
              strokeWidth={highlighted ? 2.5 : 1.5}
              opacity={dimmed ? 0.2 : 1}
              markerEnd={`url(#${markerId})`}
              className="transition-all duration-200"
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const colors = getNodeColor(node);
          const dimmed = isNodeDimmed(node);
          const isActive = node.id === activeNode;

          return (
            <g
              key={node.id}
              className="cursor-pointer transition-all duration-200"
              opacity={dimmed ? 0.3 : 1}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() =>
                setSelectedNode(selectedNode === node.id ? null : node.id)
              }
            >
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={isActive ? 32 : 28}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={isActive ? 3 : 2}
                className="transition-all duration-200"
              />

              {/* Node label (inside circle) */}
              <text
                x={node.x}
                y={node.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill={colors.text}
                fontSize={node.label.length > 10 ? 9 : 11}
                fontWeight="600"
                className="pointer-events-none select-none"
              >
                {truncateLabel(node.label, 12)}
              </text>

              {/* Full label below */}
              <text
                x={node.x}
                y={node.y + 42}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#6b7280"
                fontSize={10}
                className="pointer-events-none select-none"
              >
                {node.label}
              </text>

              {/* Tooltip on selected */}
              {selectedNode === node.id && node.fullPath !== node.label && (
                <g>
                  <rect
                    x={node.x - 100}
                    y={node.y - 55}
                    width={200}
                    height={22}
                    rx={4}
                    fill="#1e293b"
                    opacity={0.9}
                  />
                  <text
                    x={node.x}
                    y={node.y - 44}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="#ffffff"
                    fontSize={10}
                    fontFamily="monospace"
                    className="pointer-events-none select-none"
                  >
                    {truncateLabel(node.fullPath, 36)}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-indigo-500" />
          <span>Current module</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-blue-500" />
          <span>Internal dependency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-orange-400" />
          <span>External dependency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width={16} height={8}>
            <line x1={0} y1={4} x2={12} y2={4} stroke="#93c5fd" strokeWidth={2} />
            <polygon points="10,1 16,4 10,7" fill="#93c5fd" />
          </svg>
          <span>Import direction</span>
        </div>
      </div>
    </div>
  );
}
