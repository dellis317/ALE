import { useState } from 'react';
import { Save, X } from 'lucide-react';
import type { PolicyRule } from '../types';

const SCOPE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'file', label: 'File' },
  { value: 'directory', label: 'Directory' },
  { value: 'capability', label: 'Capability' },
  { value: 'library', label: 'Library' },
];

const ACTION_OPTIONS = [
  { value: 'allow', label: 'Allow' },
  { value: 'deny', label: 'Deny' },
  { value: 'require_approval', label: 'Require Approval' },
];

interface PolicyRuleEditorProps {
  rule?: PolicyRule;
  onSave: (rule: PolicyRule) => void;
  onCancel: () => void;
}

export default function PolicyRuleEditor({ rule, onSave, onCancel }: PolicyRuleEditorProps) {
  const [name, setName] = useState(rule?.name || '');
  const [description, setDescription] = useState(rule?.description || '');
  const [scope, setScope] = useState(rule?.scope || 'all');
  const [action, setAction] = useState(rule?.action || 'allow');
  const [patternsText, setPatternsText] = useState(rule?.patterns?.join(', ') || '');
  const [rationale, setRationale] = useState(rule?.rationale || '');

  function handleSave() {
    if (!name.trim()) return;
    const patterns = patternsText
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
    onSave({
      name: name.trim(),
      description: description.trim(),
      scope,
      action,
      patterns,
      conditions: rule?.conditions || {},
      rationale: rationale.trim(),
    });
  }

  const actionColor =
    action === 'deny'
      ? 'border-red-300 bg-red-50'
      : action === 'require_approval'
        ? 'border-amber-300 bg-amber-50'
        : 'border-emerald-300 bg-emerald-50';

  return (
    <div className={`border rounded-lg p-4 ${actionColor}`}>
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Rule Name */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Rule Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Block sensitive files"
            className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of the rule"
            className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Scope */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Scope</label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            {SCOPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Action */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Action</label>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Patterns */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Patterns <span className="text-gray-400 font-normal">(comma-separated)</span>
        </label>
        <textarea
          value={patternsText}
          onChange={(e) => setPatternsText(e.target.value)}
          placeholder="e.g., *.env, secrets/*, config/*.key"
          rows={2}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono"
        />
      </div>

      {/* Rationale */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-1">Rationale</label>
        <textarea
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          placeholder="Why does this rule exist?"
          rows={2}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <X size={14} />
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!name.trim()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save size={14} />
          Save Rule
        </button>
      </div>
    </div>
  );
}
