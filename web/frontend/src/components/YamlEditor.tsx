import { useRef, useEffect, useCallback } from 'react';

interface YamlEditorProps {
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  placeholder?: string;
}

export default function YamlEditor({
  value,
  onChange,
  readOnly = false,
  placeholder = '# Enter YAML content here...',
}: YamlEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  const lines = value ? value.split('\n') : [''];
  const lineCount = lines.length;

  const syncScroll = useCallback(() => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Auto-resize textarea to content
    textarea.style.height = 'auto';
    const minHeight = 400;
    textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      if (readOnly || !onChange) return;

      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;

      // Insert 2 spaces at cursor position
      const newValue = value.substring(0, start) + '  ' + value.substring(end);
      onChange(newValue);

      // Restore cursor position after React re-render
      requestAnimationFrame(() => {
        textarea.selectionStart = start + 2;
        textarea.selectionEnd = start + 2;
      });
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (onChange && !readOnly) {
      onChange(e.target.value);
    }
  };

  return (
    <div className="relative flex border border-gray-300 rounded-lg overflow-hidden bg-gray-950 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent">
      {/* Line numbers gutter */}
      <div
        ref={lineNumbersRef}
        className="flex-shrink-0 bg-gray-900 text-gray-500 text-xs font-mono py-3 select-none overflow-hidden"
        style={{ width: '3.5rem' }}
        aria-hidden="true"
      >
        {Array.from({ length: lineCount }, (_, i) => (
          <div
            key={i + 1}
            className="px-2 text-right leading-[1.625rem]"
          >
            {i + 1}
          </div>
        ))}
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onScroll={syncScroll}
        readOnly={readOnly}
        placeholder={placeholder}
        spellCheck={false}
        className={`flex-1 bg-gray-950 text-gray-100 font-mono text-sm py-3 px-4 resize-none outline-none leading-[1.625rem] placeholder-gray-600 ${
          readOnly ? 'cursor-default' : ''
        }`}
        style={{ minHeight: '400px', tabSize: 2 }}
      />
    </div>
  );
}
