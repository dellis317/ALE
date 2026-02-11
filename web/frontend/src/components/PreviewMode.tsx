import { CheckSquare, List, Shield, Tag } from 'lucide-react';
import Badge from './Badge';

interface PreviewModeProps {
  yamlContent: string;
}

/**
 * Simple YAML parser that extracts agentic library structure from raw YAML text.
 * This is a basic line-by-line parser (no external YAML library needed).
 */
function parseYamlContent(content: string): ParsedLibrary {
  const result: ParsedLibrary = {
    name: '',
    version: '',
    description: '',
    specVersion: '',
    complexity: '',
    tags: [],
    capabilities: [],
    languageAgnostic: true,
    overview: '',
    instructions: [],
    guardrails: [],
    validation: [],
  };

  if (!content.trim()) return result;

  // Simple state-machine line parser
  const lines = content.split('\n');
  let currentSection = '';
  let currentItem: Record<string, string> = {};
  let inManifest = false;
  let itemIndex = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimEnd();
    const stripped = trimmed.trim();

    if (!stripped || stripped.startsWith('#')) continue;

    // Detect indentation level
    const indent = line.length - line.trimStart().length;

    // Top-level keys
    if (indent === 0 || (indent <= 2 && stripped.endsWith(':'))) {
      if (stripped === 'agentic_library:') continue;
    }

    // Section detection (indent level 2-4 typically)
    if (stripped === 'manifest:') {
      inManifest = true;
      currentSection = 'manifest';
      continue;
    }
    if (stripped === 'overview:' || stripped.startsWith('overview:')) {
      inManifest = false;
      currentSection = 'overview';
      const val = extractValue(stripped, 'overview');
      if (val) result.overview = val;
      continue;
    }
    if (stripped === 'instructions:') {
      inManifest = false;
      currentSection = 'instructions';
      itemIndex = -1;
      continue;
    }
    if (stripped === 'guardrails:') {
      inManifest = false;
      currentSection = 'guardrails';
      itemIndex = -1;
      continue;
    }
    if (stripped === 'validation:') {
      inManifest = false;
      currentSection = 'validation';
      itemIndex = -1;
      continue;
    }
    if (stripped === 'capability_dependencies:') {
      inManifest = false;
      currentSection = 'capability_dependencies';
      continue;
    }

    // Parse manifest keys
    if (inManifest && currentSection === 'manifest') {
      if (stripped.startsWith('name:')) result.name = extractValue(stripped, 'name');
      if (stripped.startsWith('version:')) result.version = extractValue(stripped, 'version');
      if (stripped.startsWith('description:')) result.description = extractValue(stripped, 'description');
      if (stripped.startsWith('spec_version:')) result.specVersion = extractValue(stripped, 'spec_version');
      if (stripped.startsWith('complexity:')) result.complexity = extractValue(stripped, 'complexity');
      if (stripped.startsWith('language_agnostic:')) {
        result.languageAgnostic = extractValue(stripped, 'language_agnostic') !== 'false';
      }
      if (stripped.startsWith('tags:')) {
        currentSection = 'tags';
        continue;
      }
      continue;
    }

    // Parse tags list
    if (currentSection === 'tags') {
      if (stripped.startsWith('- ')) {
        result.tags.push(stripped.slice(2).trim().replace(/^['"]|['"]$/g, ''));
      } else if (!stripped.startsWith('-') && stripped.includes(':')) {
        // Moved to a new section
        currentSection = 'manifest';
        inManifest = true;
        i--; // Re-process this line
      }
      continue;
    }

    // Parse instructions
    if (currentSection === 'instructions') {
      if (stripped.startsWith('- ')) {
        // New instruction item
        if (itemIndex >= 0 && currentItem.title) {
          result.instructions.push({ ...currentItem } as InstructionItem);
        }
        currentItem = {};
        itemIndex++;
        // Parse inline key
        const afterDash = stripped.slice(2).trim();
        if (afterDash.startsWith('step:')) {
          currentItem.step = extractValue(afterDash, 'step');
        }
        continue;
      }
      if (indent >= 4 && itemIndex >= 0) {
        if (stripped.startsWith('step:')) currentItem.step = extractValue(stripped, 'step');
        if (stripped.startsWith('title:')) currentItem.title = extractValue(stripped, 'title');
        if (stripped.startsWith('description:')) currentItem.description = extractValue(stripped, 'description');
        if (stripped.startsWith('code_sketch:')) currentItem.code_sketch = extractValue(stripped, 'code_sketch');
        if (stripped.startsWith('notes:')) currentItem.notes = extractValue(stripped, 'notes');
      }
      continue;
    }

    // Parse guardrails
    if (currentSection === 'guardrails') {
      if (stripped.startsWith('- ')) {
        if (itemIndex >= 0 && currentItem.rule) {
          result.guardrails.push({ ...currentItem } as GuardrailItem);
        }
        currentItem = {};
        itemIndex++;
        const afterDash = stripped.slice(2).trim();
        if (afterDash.startsWith('rule:')) {
          currentItem.rule = extractValue(afterDash, 'rule');
        }
        continue;
      }
      if (indent >= 4 && itemIndex >= 0) {
        if (stripped.startsWith('rule:')) currentItem.rule = extractValue(stripped, 'rule');
        if (stripped.startsWith('severity:')) currentItem.severity = extractValue(stripped, 'severity');
        if (stripped.startsWith('rationale:')) currentItem.rationale = extractValue(stripped, 'rationale');
      }
      continue;
    }

    // Parse validation
    if (currentSection === 'validation') {
      if (stripped.startsWith('- ')) {
        if (itemIndex >= 0 && currentItem.description) {
          result.validation.push({ ...currentItem } as ValidationItem);
        }
        currentItem = {};
        itemIndex++;
        const afterDash = stripped.slice(2).trim();
        if (afterDash.startsWith('description:')) {
          currentItem.description = extractValue(afterDash, 'description');
        }
        continue;
      }
      if (indent >= 4 && itemIndex >= 0) {
        if (stripped.startsWith('description:')) currentItem.description = extractValue(stripped, 'description');
        if (stripped.startsWith('test_approach:')) currentItem.test_approach = extractValue(stripped, 'test_approach');
        if (stripped.startsWith('expected_behavior:')) currentItem.expected_behavior = extractValue(stripped, 'expected_behavior');
      }
      continue;
    }

    // Parse capability_dependencies
    if (currentSection === 'capability_dependencies') {
      if (stripped.startsWith('- ')) {
        const cap = stripped.slice(2).trim().replace(/^['"]|['"]$/g, '');
        result.capabilities.push(cap);
      }
      continue;
    }
  }

  // Flush last items
  if (currentSection === 'instructions' && itemIndex >= 0 && currentItem.title) {
    result.instructions.push({ ...currentItem } as InstructionItem);
  }
  if (currentSection === 'guardrails' && itemIndex >= 0 && currentItem.rule) {
    result.guardrails.push({ ...currentItem } as GuardrailItem);
  }
  if (currentSection === 'validation' && itemIndex >= 0 && currentItem.description) {
    result.validation.push({ ...currentItem } as ValidationItem);
  }

  return result;
}

function extractValue(line: string, key: string): string {
  const prefix = key + ':';
  const idx = line.indexOf(prefix);
  if (idx === -1) return '';
  let val = line.slice(idx + prefix.length).trim();
  // Remove surrounding quotes
  if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
    val = val.slice(1, -1);
  }
  return val;
}

interface InstructionItem {
  step?: string;
  title?: string;
  description?: string;
  code_sketch?: string;
  notes?: string;
}

interface GuardrailItem {
  rule?: string;
  severity?: string;
  rationale?: string;
}

interface ValidationItem {
  description?: string;
  test_approach?: string;
  expected_behavior?: string;
}

interface ParsedLibrary {
  name: string;
  version: string;
  description: string;
  specVersion: string;
  complexity: string;
  tags: string[];
  capabilities: string[];
  languageAgnostic: boolean;
  overview: string;
  instructions: InstructionItem[];
  guardrails: GuardrailItem[];
  validation: ValidationItem[];
}

function SeverityBadge({ severity }: { severity: string }) {
  const variant =
    severity === 'must'
      ? 'error'
      : severity === 'should'
        ? 'warning'
        : 'info';
  return <Badge label={severity} variant={variant} />;
}

export default function PreviewMode({ yamlContent }: PreviewModeProps) {
  const parsed = parseYamlContent(yamlContent);

  if (!yamlContent.trim()) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <p className="text-sm">No content to preview</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview / Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {parsed.name || 'Untitled Library'}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              {parsed.version && (
                <span className="text-sm text-gray-500">v{parsed.version}</span>
              )}
              {parsed.specVersion && (
                <span className="text-xs text-gray-400">spec {parsed.specVersion}</span>
              )}
              {parsed.complexity && (
                <Badge
                  label={parsed.complexity}
                  variant={
                    parsed.complexity === 'simple'
                      ? 'success'
                      : parsed.complexity === 'moderate'
                        ? 'warning'
                        : 'error'
                  }
                />
              )}
            </div>
          </div>
          {parsed.languageAgnostic && (
            <Badge label="Language Agnostic" variant="info" />
          )}
        </div>

        {parsed.description && (
          <p className="text-sm text-gray-600 mt-2">{parsed.description}</p>
        )}

        {parsed.overview && (
          <p className="text-sm text-gray-600 mt-2 italic">{parsed.overview}</p>
        )}

        {/* Tags */}
        {parsed.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-4">
            {parsed.tags.map((tag) => (
              <Badge key={tag} label={tag} variant="info" />
            ))}
          </div>
        )}

        {/* Capabilities */}
        {parsed.capabilities.length > 0 && (
          <div className="mt-3">
            <span className="text-xs font-medium text-gray-500 mr-2">Capabilities:</span>
            <div className="inline-flex flex-wrap gap-1.5">
              {parsed.capabilities.map((cap) => (
                <Badge key={cap} label={cap} variant="default" />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      {parsed.instructions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <List size={16} className="text-indigo-600" />
            Instructions ({parsed.instructions.length} step{parsed.instructions.length !== 1 ? 's' : ''})
          </h3>
          <div className="space-y-3">
            {parsed.instructions.map((step, i) => (
              <div
                key={i}
                className="bg-white rounded-xl border border-gray-200 p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-indigo-600">
                      {step.step || i + 1}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-900 text-sm">
                      {step.title || `Step ${i + 1}`}
                    </h4>
                    {step.description && (
                      <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                    )}
                    {step.code_sketch && (
                      <pre className="mt-2 text-xs font-mono bg-gray-50 p-3 rounded-lg text-gray-700 overflow-x-auto whitespace-pre-wrap">
                        {step.code_sketch}
                      </pre>
                    )}
                    {step.notes && (
                      <p className="text-xs text-gray-500 mt-2 italic">Note: {step.notes}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Guardrails */}
      {parsed.guardrails.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Shield size={16} className="text-indigo-600" />
            Guardrails ({parsed.guardrails.length})
          </h3>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {parsed.guardrails.map((guardrail, i) => (
              <div key={i} className="p-4 flex items-start gap-3">
                <div className="mt-0.5">
                  <CheckSquare size={16} className="text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm text-gray-900">{guardrail.rule}</span>
                    {guardrail.severity && (
                      <SeverityBadge severity={guardrail.severity} />
                    )}
                  </div>
                  {guardrail.rationale && (
                    <p className="text-xs text-gray-500">{guardrail.rationale}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation Criteria */}
      {parsed.validation.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Tag size={16} className="text-indigo-600" />
            Validation Criteria ({parsed.validation.length})
          </h3>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {parsed.validation.map((item, i) => (
              <div key={i} className="p-4">
                <p className="text-sm font-medium text-gray-900 mb-1">{item.description}</p>
                {item.test_approach && (
                  <p className="text-xs text-gray-600">
                    <span className="font-medium">Test:</span> {item.test_approach}
                  </p>
                )}
                {item.expected_behavior && (
                  <p className="text-xs text-gray-600">
                    <span className="font-medium">Expected:</span> {item.expected_behavior}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state for unparsed content */}
      {!parsed.name && parsed.instructions.length === 0 && parsed.guardrails.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">
            Could not parse library structure from the YAML content.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Ensure the content follows the Agentic Library YAML format.
          </p>
        </div>
      )}
    </div>
  );
}
