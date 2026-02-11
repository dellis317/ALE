import { useState } from 'react';
import { X } from 'lucide-react';

const WEBHOOK_EVENTS = [
  'library.published',
  'library.deleted',
  'conformance.passed',
  'conformance.failed',
  'policy.violated',
  'approval.requested',
  'approval.decided',
];

interface WebhookFormProps {
  initialName?: string;
  initialUrl?: string;
  initialEvents?: string[];
  initialSecret?: string;
  onSave: (data: { name: string; url: string; events: string[]; secret: string }) => void;
  onCancel: () => void;
  isEdit?: boolean;
}

export default function WebhookForm({
  initialName = '',
  initialUrl = '',
  initialEvents = [],
  initialSecret = '',
  onSave,
  onCancel,
  isEdit = false,
}: WebhookFormProps) {
  const [name, setName] = useState(initialName);
  const [url, setUrl] = useState(initialUrl);
  const [secret, setSecret] = useState(initialSecret);
  const [events, setEvents] = useState<string[]>(initialEvents);
  const [showSecret, setShowSecret] = useState(false);

  const toggleEvent = (event: string) => {
    setEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    onSave({ name: name.trim(), url: url.trim(), events, secret });
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {isEdit ? 'Edit Webhook' : 'Add Webhook'}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          <X size={20} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div>
          <label
            htmlFor="webhook-name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Name
          </label>
          <input
            id="webhook-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Webhook"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
            required
          />
        </div>

        {/* URL */}
        <div>
          <label
            htmlFor="webhook-url"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            URL
          </label>
          <input
            id="webhook-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/webhook"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
            required
          />
        </div>

        {/* Secret */}
        <div>
          <label
            htmlFor="webhook-secret"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Secret{' '}
            <span className="text-gray-400 font-normal">(optional, for HMAC signing)</span>
          </label>
          <div className="relative">
            <input
              id="webhook-secret"
              type={showSecret ? 'text' : 'password'}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="webhook_secret_key"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500 pr-16"
            />
            <button
              type="button"
              onClick={() => setShowSecret(!showSecret)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-indigo-600 hover:text-indigo-800"
            >
              {showSecret ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>

        {/* Events */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Events
          </label>
          <div className="grid grid-cols-2 gap-2">
            {WEBHOOK_EVENTS.map((event) => (
              <label
                key={event}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={events.includes(event)}
                  onChange={() => toggleEvent(event)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">{event}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || !url.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isEdit ? 'Update Webhook' : 'Create Webhook'}
          </button>
        </div>
      </form>
    </div>
  );
}
