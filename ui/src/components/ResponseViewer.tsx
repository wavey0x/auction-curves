import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Copy, Check } from 'lucide-react';
import CodeBlock from './CodeBlock';

interface ResponseViewerProps {
  data: any;
  title?: string;
  status?: number;
  headers?: Record<string, string>;
  loading?: boolean;
  error?: string;
}

const ResponseViewer: React.FC<ResponseViewerProps> = ({
  data,
  title = "Response",
  status,
  headers,
  loading = false,
  error,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [showHeaders, setShowHeaders] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const jsonString = JSON.stringify(data, null, 2);
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy response:', err);
    }
  };

  const getStatusColor = (status?: number) => {
    if (!status) return 'text-gray-400';
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-yellow-400';
    if (status >= 400) return 'text-red-400';
    return 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-400"></div>
          <span className="text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-red-800 rounded-lg p-4">
        <div className="flex items-center space-x-2 text-red-400">
          <span className="font-medium">Error:</span>
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <span className="text-gray-500">No response data</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center space-x-1 text-gray-300 hover:text-white"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <span className="font-medium">{title}</span>
          </button>
          
          {status && (
            <span className={`text-sm font-mono font-bold ${getStatusColor(status)}`}>
              {status}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {headers && (
            <button
              onClick={() => setShowHeaders(!showHeaders)}
              className="text-xs text-gray-400 hover:text-gray-300 px-2 py-1 bg-gray-800 rounded"
            >
              Headers
            </button>
          )}
          
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div>
          {/* Headers */}
          {showHeaders && headers && (
            <div className="p-4 border-b border-gray-800 bg-gray-950">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Response Headers</h4>
              <div className="space-y-1">
                {Object.entries(headers).map(([key, value]) => (
                  <div key={key} className="flex text-xs font-mono">
                    <span className="text-gray-400 w-32 flex-shrink-0">{key}:</span>
                    <span className="text-gray-300">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Response Body */}
          <div className="p-0">
            <CodeBlock
              code={JSON.stringify(data, null, 2)}
              language="json"
              maxHeight="max-h-96"
              showCopyButton={false}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseViewer;