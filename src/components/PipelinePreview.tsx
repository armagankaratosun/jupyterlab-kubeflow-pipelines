import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface PipelinePreviewProps {
  pipeline: any; // The inspected pipeline object
}

const PipelinePreview: React.FC<PipelinePreviewProps> = ({ pipeline }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pipeline) return;

    // Initialize mermaid
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        htmlLabels: true,
        curve: 'basis'
      }
    });

    // Generate mermaid graph from pipeline structure
    const generateMermaidGraph = (p: any) => {
      let graph = 'graph TD;\n';

      // Extract graph from component_spec or pipeline_spec
      let tasks: any = {};

      // Try different locations for tasks
      if (p.pipeline_spec && p.pipeline_spec.root) {
        // KFP v2 IR style
        tasks = p.pipeline_spec.root.dag.tasks || {};
      } else if (
        p.component_spec &&
        p.component_spec.implementation &&
        p.component_spec.implementation.graph
      ) {
        // KFP v2 component spec style
        tasks = p.component_spec.implementation.graph.tasks || {};
      }

      // If no tasks found (maybe simple component or parsing failed), show single node
      if (Object.keys(tasks).length === 0) {
        const name = p.display_name || p.name;
        const safeName = name.replace(/[^a-zA-Z0-9]/g, '_');
        return `graph TD;\n    ${safeName}["${name}"];`;
      }

      // Build nodes and edges
      Object.keys(tasks).forEach((taskName) => {
        const task = tasks[taskName];
        const safeTaskName = taskName.replace(/[^a-zA-Z0-9]/g, '_');
        const label = task.componentRef?.name || taskName;

        graph += `    ${safeTaskName}["${label}"];\n`;

        // Dependencies
        if (task.dependentTasks) {
          task.dependentTasks.forEach((dep: string) => {
            const safeDep = dep.replace(/[^a-zA-Z0-9]/g, '_');
            graph += `    ${safeDep} --> ${safeTaskName};\n`;
          });
        }
      });

      return graph;
    };

    const renderGraph = async () => {
      if (containerRef.current) {
        try {
          const graphDefinition = generateMermaidGraph(pipeline);
          const { svg } = await mermaid.render(
            `mermaid-${Date.now()}`,
            graphDefinition
          );
          containerRef.current.innerHTML = svg;
        } catch (err) {
          console.error('Failed to render mermaid graph', err);
          containerRef.current.innerHTML =
            '<div class="jp-KfpMessage">Preview not available for this pipeline structure.</div>';
        }
      }
    };

    renderGraph();
  }, [pipeline]);

  return (
    <div
      className="jp-KfpPipelinePreview"
      style={{
        border: '1px solid var(--jp-border-color2)',
        borderRadius: '4px',
        padding: '12px',
        backgroundColor: 'var(--jp-layout-color1)',
        minHeight: '200px',
        display: 'flex',
        justifyContent: 'center',
        overflow: 'auto'
      }}
    >
      <div ref={containerRef} style={{ width: '100%' }} />
    </div>
  );
};

export default PipelinePreview;
