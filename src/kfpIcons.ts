import { LabIcon } from '@jupyterlab/ui-components';

// KFP-ish icon set (keeps our blue accent but matches KFP UI semantics)
export const kfpPipelinesIcon = new LabIcon({
  name: 'kfp:pipelines',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="3" y="4" width="6" height="6" rx="1"></rect>' +
    '<rect x="15" y="4" width="6" height="6" rx="1"></rect>' +
    '<rect x="9" y="14" width="6" height="6" rx="1"></rect>' +
    '<path d="M9 7h6"></path>' +
    '<path d="M12 10v4"></path>' +
    '</svg>'
});

export const kfpExperimentsIcon = new LabIcon({
  name: 'kfp:experiments',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M20 6 9 17l-5-5"></path>' +
    '</svg>'
});

export const kfpRunsIcon = new LabIcon({
  name: 'kfp:runs',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="8" cy="6" r="2"></circle>' +
    '<path d="M8 8l2 4 3 2"></path>' +
    '<path d="M6 22l2-6"></path>' +
    '<path d="M10 22l2-5 5-2"></path>' +
    '</svg>'
});

export const kfpRecurringRunsIcon = new LabIcon({
  name: 'kfp:recurring-runs',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="8"></circle>' +
    '<path d="M12 8v5l3 2"></path>' +
    '</svg>'
});

export const kfpArtifactsIcon = new LabIcon({
  name: 'kfp:artifacts',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="7" cy="12" r="1.8"></circle>' +
    '<circle cx="12" cy="12" r="1.8"></circle>' +
    '<circle cx="17" cy="12" r="1.8"></circle>' +
    '</svg>'
});

export const kfpExecutionsIcon = new LabIcon({
  name: 'kfp:executions',
  svgstr:
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="#4285f4" stroke="#4285f4" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">' +
    '<polygon points="9 7 19 12 9 17"></polygon>' +
    '</svg>'
});
