import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Play, Code, FileText, ExternalLink } from 'lucide-react';
import CodeBlock from './CodeBlock';
import ApiTester from './ApiTester';

interface Parameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'integer';
  required?: boolean;
  description?: string;
  example?: string | number | boolean;
  enum?: string[];
}

interface ResponseExample {
  status: number;
  description: string;
  example: any;
}

interface ApiEndpointProps {
  title: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  endpoint: string;
  description: string;
  parameters?: Parameter[];
  pathParams?: Parameter[];
  responses: ResponseExample[];
  codeExamples?: {
    curl?: string;
    javascript?: string;
    python?: string;
  };
  tags?: string[];
}

const ApiEndpoint: React.FC<ApiEndpointProps> = ({
  title,
  method,
  endpoint,
  description,
  parameters = [],
  pathParams = [],
  responses,
  codeExamples,
  tags = [],
}) => {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'try' | 'examples' | 'responses'>('try');

  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'bg-blue-500';
      case 'POST': return 'bg-green-500';
      case 'PUT': return 'bg-yellow-500';
      case 'PATCH': return 'bg-orange-500';
      case 'DELETE': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const tabs = [
    { id: 'try' as const, label: 'Try It Out', icon: Play },
    { id: 'examples' as const, label: 'Code Examples', icon: Code },
    { id: 'responses' as const, label: 'Responses', icon: FileText },
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div 
        className="p-3 cursor-pointer hover:bg-gray-850 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="flex items-center space-x-2">
              {expanded ? (
                <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
              )}
              
              <span className={`text-xs font-bold text-white px-1.5 py-0.5 rounded ${getMethodColor(method)}`}>
                {method}
              </span>
            </div>
            
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-100">{title}</h3>
              <p className="text-xs text-gray-400 font-mono">{endpoint}</p>
            </div>
          </div>

          <div className="flex items-center space-x-1.5">
            {tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
        
        {!expanded && (
          <p className="text-xs text-gray-400 mt-2 line-clamp-2">{description}</p>
        )}
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-800">
          {/* Description */}
          <div className="p-3 bg-gray-950 border-b border-gray-800">
            <p className="text-sm text-gray-300">{description}</p>
          </div>

          {/* Parameters Documentation */}
          {(pathParams.length > 0 || parameters.length > 0) && (
            <div className="p-3 bg-gray-950 border-b border-gray-800">
              <h4 className="text-xs font-semibold text-gray-200 mb-2">Parameters</h4>
              
              {/* Path Parameters */}
              {pathParams.length > 0 && (
                <div className="mb-3">
                  <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                    Path Parameters
                  </h5>
                  <div className="space-y-1.5">
                    {pathParams.map((param) => (
                      <div key={param.name} className="flex items-start space-x-2 text-xs">
                        <div className="flex items-center space-x-1.5 w-28 flex-shrink-0">
                          <span className="font-mono text-gray-300">{param.name}</span>
                          {param.required && <span className="text-red-400">*</span>}
                        </div>
                        <span className="text-xs bg-gray-800 text-gray-400 px-1 rounded font-mono">
                          {param.type}
                        </span>
                        <span className="text-gray-400 flex-1">{param.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Query Parameters */}
              {parameters.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                    Query Parameters
                  </h5>
                  <div className="space-y-1.5">
                    {parameters.map((param) => (
                      <div key={param.name} className="flex items-start space-x-2 text-xs">
                        <div className="flex items-center space-x-1.5 w-28 flex-shrink-0">
                          <span className="font-mono text-gray-300">{param.name}</span>
                          {param.required && <span className="text-red-400">*</span>}
                        </div>
                        <span className="text-xs bg-gray-800 text-gray-400 px-1 rounded font-mono">
                          {param.type}
                        </span>
                        <span className="text-gray-400 flex-1">{param.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tabs */}
          <div className="border-b border-gray-800">
            <div className="flex space-x-0">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-primary-500 text-primary-400 bg-gray-850'
                        : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-850'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-3">
            {activeTab === 'try' && (
              <ApiTester
                endpoint={endpoint}
                method={method}
                parameters={parameters}
                pathParams={pathParams}
              />
            )}

            {activeTab === 'examples' && codeExamples && (
              <div className="space-y-4">
                {codeExamples.curl && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-2">cURL</h5>
                    <CodeBlock code={codeExamples.curl} language="bash" />
                  </div>
                )}
                
                {codeExamples.javascript && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-2">JavaScript</h5>
                    <CodeBlock code={codeExamples.javascript} language="javascript" />
                  </div>
                )}
                
                {codeExamples.python && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-2">Python</h5>
                    <CodeBlock code={codeExamples.python} language="python" />
                  </div>
                )}
              </div>
            )}

            {activeTab === 'responses' && (
              <div className="space-y-4">
                {responses.map((response, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <span className={`text-sm font-mono font-bold ${
                        response.status >= 200 && response.status < 300 ? 'text-green-400' :
                        response.status >= 400 ? 'text-red-400' : 'text-yellow-400'
                      }`}>
                        {response.status}
                      </span>
                      <span className="text-sm text-gray-400">{response.description}</span>
                    </div>
                    <CodeBlock
                      code={JSON.stringify(response.example, null, 2)}
                      language="json"
                      maxHeight="max-h-64"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiEndpoint;