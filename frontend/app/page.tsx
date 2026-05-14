'use client';

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  type: 'user' | 'pipeline' | 'chart' | 'streaming' | 'final';
  content: string;
  imageUrl?: string;
  sender?: 'user' | 'agent';
}

export default function Home() {
  // Session management
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [datasetSource, setDatasetSource] = useState<string | null>(null);
  const [datasetName, setDatasetName] = useState<string>('');
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [summaryText, setSummaryText] = useState('');
  const [availableDatasets, setAvailableDatasets] = useState<any[]>([]);
  const [datasetPickerExpanded, setDatasetPickerExpanded] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [expandedMemory, setExpandedMemory] = useState(false);
  const [expandedAccordions, setExpandedAccordions] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingContentRef = useRef('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isFetchingDrive, setIsFetchingDrive] = useState(false);
  const [driveStatus, setDriveStatus] = useState<string>('Connect your Drive');
  const [uploadedQuestions, setUploadedQuestions] = useState<string[]>([]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload-csv', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (data.filename) {
        setDatasetName(data.filename);
        setDatasetSource('upload');
        if (data.questions) {
          setUploadedQuestions(data.questions);
        }
      }
    } catch (error) {
      console.error('Failed to upload file:', error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDriveFetch = async () => {
    setIsFetchingDrive(true);
    setDriveStatus('Fetching from Drive...');
    try {
      const response = await fetch('http://localhost:8000/drive-fetch', {
        method: 'POST',
      });
      const data = await response.json();
      if (data.filename) {
        setDatasetName(data.filename);
        setDatasetSource('drive');
        setDriveStatus(`✅ Fetched: ${data.filename.split('/').pop()}`);
      } else {
        setDriveStatus('❌ Drive fetch failed');
      }
    } catch (error) {
      console.error('Failed to fetch from Drive:', error);
      setDriveStatus('❌ Drive fetch failed');
    } finally {
      setIsFetchingDrive(false);
    }
  };

  const appendPipelineMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        type: 'pipeline',
        content: text,
      },
    ]);
  };

  const appendStreamingMessage = (chunk: string) => {
    const trimmed = chunk.trim();
    if (trimmed === '•' || trimmed === '·' || trimmed === '.') return;

    streamingContentRef.current += chunk;

    setMessages((prev) => {
      const withoutStreaming = prev.filter((m) => m.type !== 'streaming');
      return [
        ...withoutStreaming,
        {
          id: 'streaming',
          type: 'streaming',
          content: streamingContentRef.current,
        },
      ];
    });
  };

  const finalizeStreamingMessage = (content: string) => {
    streamingContentRef.current = '';
    setMessages((prev) => {
      const withoutStreaming = prev.filter((m) => m.type !== 'streaming');
      return [
        ...withoutStreaming,
        { id: `${Date.now()}-final`, type: 'final', content },
      ];
    });
  };

  const suggestionsByDataset: Record<string, string[]> = {
    'sales_data.csv': [
      'Which product had highest sales?',
      'Show me sales by region as pie chart',
      'What is the monthly sales trend for 2023?',
      'Which age group spends the most?'
    ],
    'inventory_data.csv': [
      'Which product has the lowest stock level?',
      'Show me warehouse cost by region as pie chart',
      'Which products are below reorder point?',
      'What is the stock trend over time?'
    ],
    'customer_data.csv': [
      'Which region has the most loyal customers?',
      'Show me total spending by age group',
      'What is the average loyalty score by region?',
      'Which category do customers prefer the most?'
    ]
  };

  const suggestions = datasetSource === 'upload' && uploadedQuestions.length > 0
    ? uploadedQuestions
    : (suggestionsByDataset[datasetName] || suggestionsByDataset['sales_data.csv']);

  const handleStartSession = async () => {
    if (!datasetSource) return;

    try {
      const response = await fetch('http://localhost:8000/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_source: datasetSource,
          dataset_name: datasetName || 'sales_data.csv',
        }),
      });
      const data = await response.json();
      if (data.session_id) {
        setSessionId(data.session_id);
        setDatasetName(data.dataset_name);
      }
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch('http://localhost:8000/session/end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await response.json();
      setSummaryText(data.summary || 'Session ended.');
      setShowSummaryModal(true);

      setTimeout(() => {
        setShowSummaryModal(false);
        resetToDatasetPicker();
      }, 5000);
    } catch (error) {
      console.error('Failed to end session:', error);
    }
  };

  const resetToDatasetPicker = () => {
    setSessionId(null);
    setDatasetSource(null);
    setDatasetName('');
    setMessages([]);
    setInputValue('');
    setIsLoading(false);
    if (ws) ws.close();
    setWs(null);
    streamingContentRef.current = '';
  };

  // WebSocket connection - only after session starts
  useEffect(() => {
    if (!sessionId) return;

    const websocket = new WebSocket(`ws://localhost:8000/ws?session_id=${sessionId}`);

    websocket.onopen = () => {
      console.log('Connected!');
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        const rawType = String(data.type ?? '').toUpperCase();
        const messageText = typeof data.message === 'string' ? data.message : '';
        const isFinalAnswer = rawType === 'FINAL_ANSWER' || rawType === 'ANSWER';

        if (rawType === 'DONE') {
          setIsLoading(false);
          return;
        }

        if (isFinalAnswer) {
          setIsLoading(false);
          if (messageText.includes('===') || messageText.includes('---')) {
            return;
          }

          finalizeStreamingMessage(messageText);
        } else if (rawType === 'UPDATE' || rawType === 'CHUNK') {
          if (messageText.includes('===') || messageText.includes('---')) {
            return;
          }

          if (messageText.includes('Drive Agent: uploading')) {
            appendPipelineMessage(messageText);
            return;
          }

          if (messageText.includes('Chart link:')) {
            appendPipelineMessage(messageText);
            return;
          }

          if (messageText.includes('Chart saved: charts/')) {
            const match = messageText.match(/charts\/([\w]+\.png)/);
            if (match) {
              const imageUrl = `http://localhost:8000/charts/${match[1]}`;
              setMessages((prev) => [
                ...prev,
                {
                  id: `${Date.now()}`,
                  type: 'pipeline',
                  content: messageText,
                },
                {
                  id: `${Date.now() + 1}`,
                  type: 'chart',
                  content: '',
                  imageUrl,
                },
              ]);
              return;
            }
          }

          const isStreamingToken = messageText.trim().length > 0 && messageText.trim().length <= 6;
          if (isStreamingToken) {
            appendStreamingMessage(messageText);
          } else {
            appendPipelineMessage(messageText);
          }
        }
      } catch (e) {
        console.error('Error parsing message:', e);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      setWs(null);
    };

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (question: string) => {
    if (!question.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

    setMessages(prev => [...prev, {
      id: `${Date.now()}-user`,
      type: 'user',
      content: question
    }]);

    setInputValue('');
    setIsLoading(true);
    ws.send(question);
  };

  const handleSuggestedQuestion = (question: string) => {
    handleSend(question);
  };

  const toggleAccordion = (groupId: string) => {
    const newExpanded = new Set(expandedAccordions);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedAccordions(newExpanded);
  };

  // Group consecutive pipeline messages into an accordion group
  const getMessageGroups = () => {
    const nonStreamingMessages = messages.filter((m) => m.type !== 'streaming');
    const groups: any[] = [];
    let pipelineGroup: any[] = [];

    for (const msg of nonStreamingMessages) {
      if (msg.type === 'pipeline') {
        pipelineGroup.push(msg);
      } else {
        if (pipelineGroup.length > 0) {
          groups.push({ type: 'accordion', messages: pipelineGroup, id: pipelineGroup[0].id });
          pipelineGroup = [];
        }
        groups.push({ type: 'single', message: msg });
      }
    }
    if (pipelineGroup.length > 0) {
      groups.push({ type: 'accordion', messages: pipelineGroup, id: pipelineGroup[0].id });
    }
    return groups;
  };

  const getPipelineStyle = (content: string) => {
    if (content.includes('Orchestrator')) {
      return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '🎯' };
    } else if (content.includes('Memory')) {
      return { bg: 'bg-slate-600', text: 'text-slate-50 font-medium', icon: '🧠', isMemory: true };
    } else if (content.includes('Clarifier')) {
      return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '🔀' };
    } else if (content.includes('Analysis')) {
      return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '🤖' };
    } else if (content.includes('Using tool')) {
      return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '🛠️', mono: true };
    } else if (content.includes('Chart saved')) {
      return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '✅' };
    }
    return { bg: 'bg-slate-700', text: 'text-slate-50 font-medium', icon: '•' };
  };

  const renderMessage = (msg: any) => {
    if (msg.type === 'user') {
      return (
        <div key={msg.id} className="flex justify-end mb-6">
          <div className="max-w-xs lg:max-w-md bg-indigo-600 text-white px-6 py-4 rounded-2xl shadow-lg">
            <p className="text-sm leading-relaxed">{msg.content}</p>
          </div>
        </div>
      );
    }

    if (msg.type === 'pipeline') {
      const style = getPipelineStyle(msg.content);

      if (msg.content.includes('drive.google.com')) {
        const urlMatch = msg.content.match(/https:\/\/drive\.google\.com\/\S+/);
        const driveUrl = urlMatch ? urlMatch[0] : null;

        return (
          <div key={msg.id} className="flex justify-start mb-3">
            <div className={`text-xs px-4 py-2 rounded-full ${style.bg} ${style.text} shadow-sm font-mono flex items-center gap-2`}>
              <span>{style.icon}</span>
              <span>{msg.content.replace(driveUrl, '').trim()}</span>
              {driveUrl && (
                <a href={driveUrl} target="_blank" rel="noopener noreferrer" className="text-blue-300 hover:text-blue-200 underline ml-1">
                  Link
                </a>
              )}
            </div>
          </div>
        );
      }

      if (style.isMemory && !expandedMemory) {
        const firstLine = msg.content.split('\n')[0];
        return (
          <div key={msg.id} className="flex justify-start mb-3">
            <button
              onClick={() => setExpandedMemory(true)}
              className={`text-xs px-4 py-2 rounded-full ${style.bg} ${style.text} shadow-sm font-mono hover:opacity-80 transition`}
            >
              {style.icon} {firstLine}... <span className="text-slate-400 text-xs ml-2 px-2 py-0.5 rounded-full bg-white/5 hover:bg-white/10 hover:underline transition cursor-pointer">Show context</span>
            </button>
          </div>
        );
      }

      if (style.isMemory && expandedMemory) {
        return (
          <div key={msg.id} className="flex justify-start mb-3">
            <div className={`text-xs px-4 py-3 rounded-lg ${style.bg} ${style.text} shadow-sm font-mono max-w-md`}>
              <div className="whitespace-pre-wrap text-slate-200">{msg.content}</div>
              <button
                onClick={() => setExpandedMemory(false)}
                className="text-xs text-slate-400 hover:text-slate-300 mt-2 underline px-2 py-0.5 rounded-full bg-white/5 hover:bg-white/10 transition"
              >
                Hide context
              </button>
            </div>
          </div>
        );
      }

      return (
        <div key={msg.id} className="flex justify-start mb-3">
          <div className={`text-xs px-4 py-2 rounded-full ${style.bg} ${style.text} shadow-sm font-mono flex items-center gap-2`}>
            <span>{style.icon}</span>
            <span>{msg.content}</span>
          </div>
        </div>
      );
    }

    if (msg.type === 'streaming') {
      return (
        <div key={msg.id} className="flex justify-start mb-6">
          <div className="max-w-md lg:max-w-2xl bg-slate-800 text-slate-100 px-6 py-4 rounded-2xl border border-slate-700 shadow-lg">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
          </div>
        </div>
      );
    }

    if (msg.type === 'chart') {
      return (
        <div key={msg.id} className="flex justify-start mb-6">
          <img
            src={msg.imageUrl}
            alt="Generated chart"
            className="rounded-2xl max-w-2xl w-full border border-slate-700 shadow-lg"
          />
        </div>
      );
    }

    if (msg.type === 'final') {
      const cleanedContent = msg.content
        .replace(/!\[.*?\]\(.*?\)/g, '')
        .replace(/\(sandbox:[^)]+\)/g, '')
        .trim();

      return (
        <div key={msg.id} className="flex justify-start mb-8">
          <div className="max-w-md lg:max-w-2xl bg-slate-800 text-slate-100 px-6 py-5 rounded-2xl border-l-4 border-teal-500 shadow-lg">
            <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-3 text-slate-200">{children}</p>,
                  li: ({ children }) => <li className="ml-4 list-disc text-slate-200">{children}</li>,
                  ul: ({ children }) => <ul className="mb-3">{children}</ul>,
                  code: ({ children }) => (
                    <code className="bg-slate-900 px-2 py-1 rounded text-slate-100 font-mono text-xs">
                      {children}
                    </code>
                  ),
                  a: ({ children, href }) => {
                    let finalHref = href;
                    if (href && href.startsWith('sandbox:/')) {
                      finalHref = href.replace(/^sandbox:\//, 'http://localhost:8000/');
                    }
                    return (
                      <a href={finalHref} target="_blank" rel="noopener noreferrer" className="text-teal-400 hover:text-teal-300 underline">
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {cleanedContent}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      );
    }

    return null;
  };

  // Empty state - Home Screen
  if (!sessionId) {
    return (
      <div className="min-h-screen bg-linear-to-br from-gray-950 via-slate-900 to-gray-950 flex flex-col items-center justify-center px-6 py-12" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        <div className="w-full max-w-2xl">
          {/* Title with radial gradient glow effect */}
          <div className="text-center mb-16 relative">
            <div className="absolute inset-0 bg-gradient-radial from-indigo-500/20 via-transparent to-transparent blur-3xl opacity-60 -z-10" style={{ width: '500px', left: '50%', transform: 'translateX(-50%)', top: '-100px' }}></div>
            
            {/* SVG Bar Chart Icon */}
            <div className="flex justify-center mb-6">
              <svg className="w-16 h-16 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="3" y="13" width="3" height="8" fill="currentColor" />
                <rect x="10.5" y="8" width="3" height="13" fill="currentColor" />
                <rect x="18" y="4" width="3" height="17" fill="currentColor" />
              </svg>
            </div>

            <h1 className="text-5xl font-bold text-gray-50 mb-3 tracking-tight">
              Choose your dataset
            </h1>
            <p className="text-base text-slate-400">
              Select a data source to begin your analysis session
            </p>
          </div>

          {/* Dataset Options - Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {/* Local Dataset */}
            <button
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:8000/datasets');
                  const datasets = await response.json();
                  setAvailableDatasets(datasets);
                  setDatasetPickerExpanded(true);
                } catch (error) {
                  console.error('Failed to fetch datasets:', error);
                }
              }}
              className={`p-6 text-left rounded-2xl border transition ${
                datasetName && datasetSource === 'local'
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-slate-700 bg-slate-800/30 hover:bg-slate-700/50 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-2xl">📁</span>
                <span className={`text-xs px-3 py-1 rounded-full ${datasetName && datasetSource === 'local' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-700/50 text-slate-400'}`}>
                  {datasetName && datasetSource === 'local' ? '✓ Selected' : 'Available'}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-slate-100 mb-1">Use existing dataset</h3>
              <p className="text-sm text-slate-400">
                {datasetName && datasetSource === 'local' ? datasetName : 'Browse available datasets'}
              </p>
            </button>

            {/* Upload CSV */}
            <div>
              <input
                type="file"
                accept=".csv"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className={`p-6 text-left rounded-2xl border transition w-full h-full ${
                  datasetSource === 'upload'
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-slate-700 bg-slate-800/30 hover:bg-slate-700/50 hover:border-slate-600'
                } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="text-2xl">⬆️</span>
                  <span className={`text-xs px-3 py-1 rounded-full ${datasetSource === 'upload' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-700/50 text-slate-400'}`}>
                    {datasetSource === 'upload' ? '✓ Selected' : 'Available'}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-slate-100 mb-1">Upload a CSV file</h3>
                <p className="text-sm text-slate-400">
                  {isUploading ? 'Uploading...' : datasetSource === 'upload' && datasetName ? `Selected: ${datasetName.split('/').pop()}` : 'Upload from your computer'}
                </p>
              </button>
            </div>

            {/* Google Drive */}
            <button
              onClick={handleDriveFetch}
              disabled={isFetchingDrive}
              className={`p-6 text-left rounded-2xl border transition ${
                datasetSource === 'drive'
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-slate-700 bg-slate-800/30 hover:bg-slate-700/50 hover:border-slate-600'
              } ${isFetchingDrive ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-2xl">☁️</span>
                <span className={`text-xs px-3 py-1 rounded-full ${datasetSource === 'drive' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-700/50 text-slate-400'}`}>
                  {datasetSource === 'drive' ? '✓ Selected' : 'Available'}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-slate-100 mb-1">Fetch from Google Drive</h3>
              <p className="text-sm text-slate-400">{driveStatus}</p>
            </button>
          </div>

          {/* Expanded Dataset Picker */}
          {datasetPickerExpanded && (
            <div className="mb-8 p-6 rounded-2xl border border-slate-700 bg-slate-800/50">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-100">Available Datasets</h2>
                <button
                  onClick={() => {
                    setDatasetPickerExpanded(false);
                  }}
                  className="text-sm text-slate-400 hover:text-slate-300 px-3 py-1 rounded-lg hover:bg-slate-700/50 transition"
                >
                  ✕
                </button>
              </div>

              {availableDatasets.length > 0 ? (
                <div className="space-y-3">
                  {availableDatasets.map((dataset) => (
                    <div
                      key={dataset.filename}
                      className="p-4 rounded-xl border border-slate-600 bg-slate-700/30 hover:bg-slate-700/50 transition"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-slate-100">{dataset.name}</h3>
                          <p className="text-sm text-slate-400">{dataset.description}</p>
                          <div className="flex flex-wrap gap-2 mt-3">
                            {dataset.columns && dataset.columns.length > 0 ? (
                              dataset.columns.map((col: string) => (
                                <span
                                  key={col}
                                  className="text-xs px-2 py-1 rounded-full bg-slate-600/50 text-slate-300"
                                >
                                  {col}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-500">No columns info</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setDatasetSource('local');
                          setDatasetName(dataset.filename);
                          setDatasetPickerExpanded(false);
                        }}
                        className="mt-3 w-full py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition font-medium"
                      >
                        Select
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">Loading datasets...</p>
              )}
            </div>
          )}
          <button
            onClick={handleStartSession}
            disabled={!datasetName}
            className="w-full py-4 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 transition font-semibold text-lg mb-4"
          >
            Start Session
          </button>

          <p className="text-xs text-slate-500 text-center">
            Powered by GPT-4o-mini • Multi-agent system
          </p>
        </div>
      </div>
    );
  }

  // Empty state - Home Screen
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="min-h-screen bg-linear-to-br from-gray-950 via-slate-900 to-gray-950 flex flex-col items-center justify-center px-6 py-12" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        <div className="w-full max-w-2xl">
          {/* Title with radial gradient glow effect */}
          <div className="text-center mb-16 relative">
            <div className="absolute inset-0 bg-gradient-radial from-indigo-500/20 via-transparent to-transparent blur-3xl opacity-60 -z-10" style={{ width: '500px', left: '50%', transform: 'translateX(-50%)', top: '-100px' }}></div>
            
            {/* SVG Bar Chart Icon */}
            <div className="flex justify-center mb-6">
              <svg className="w-16 h-16 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="3" y="13" width="3" height="8" fill="currentColor" />
                <rect x="10.5" y="8" width="3" height="13" fill="currentColor" />
                <rect x="18" y="4" width="3" height="17" fill="currentColor" />
              </svg>
            </div>

            <h1 className="text-6xl font-bold text-gray-50 mb-4 tracking-tight">
              Data Analysis Agent
            </h1>
            <p className="text-base text-slate-400">
              Intelligent multi-agent system for data insights and visualization
            </p>
          </div>

          {/* Input Box */}
          <div className="mb-10">
            <div className="flex gap-3">
              <div className="flex-1 relative group">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend(inputValue)}
                  placeholder="Ask about your sales data..."
                  className="w-full px-6 py-4 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 focus:shadow-[0_0_16px_rgba(99,102,241,0.4)] transition-all"
                />
                <div className="absolute inset-0 rounded-xl bg-linear-to-r from-indigo-500/0 via-indigo-500/0 to-indigo-500/0 group-focus-within:from-indigo-500/10 group-focus-within:via-indigo-500/5 group-focus-within:to-indigo-500/10 pointer-events-none" />
              </div>
              <button
                onClick={() => handleSend(inputValue)}
                disabled={!inputValue.trim()}
                className="px-8 py-4 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed transition font-semibold text-lg"
              >
                →
              </button>
            </div>
            <p className="text-xs text-slate-500 text-center mt-4">
              Powered by GPT-4o-mini • Multi-agent system
            </p>
          </div>

          {/* Suggested Questions - As Chips */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suggestions.map((text, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestedQuestion(text)}
                className="group p-4 text-left rounded-2xl border border-slate-700 bg-slate-800/30 hover:bg-slate-700/50 hover:border-slate-600 transition text-slate-300 text-sm font-medium hover:shadow-lg hover:shadow-indigo-500/10"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">💡</span>
                  <span className="group-hover:text-slate-100 transition">{text}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Chat state
  return (
    <div className="min-h-screen bg-linear-to-br from-gray-950 via-slate-900 to-gray-950 flex flex-col" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header - Proper Navbar */}
      <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-700/50 px-8 py-5 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="3" y="13" width="2" height="8" fill="currentColor" />
              <rect x="10" y="8" width="2" height="13" fill="currentColor" />
              <rect x="17" y="4" width="2" height="17" fill="currentColor" />
            </svg>
            <div>
              <h1 className="text-lg font-semibold text-slate-50">Data Analysis Agent</h1>
              <p className="text-xs text-slate-500">Multi-agent sales analysis system</p>
            </div>
          </div>
          <button
            onClick={handleEndSession}
            className="text-sm px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-slate-100 transition font-medium"
          >
            End Session
          </button>
        </div>
      </div>

      {/* Summary Modal */}
      {showSummaryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-slate-800 rounded-2xl p-8 max-w-md border border-slate-700 shadow-2xl">
            <h2 className="text-xl font-semibold text-slate-100 mb-4">Session Summary</h2>
            <div className="text-sm text-slate-300 whitespace-pre-wrap mb-6 max-h-48 overflow-y-auto font-mono">
              {summaryText}
            </div>
            <p className="text-xs text-slate-500 text-center">Redirecting to dataset picker...</p>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-4">
          {getMessageGroups().map((group) => {
            if (group.type === 'accordion') {
              const isExpanded = expandedAccordions.has(group.id);
              return (
                <div key={group.id} className="flex justify-start mb-4">
                  <div className="w-full">
                    <button
                      onClick={() => toggleAccordion(group.id)}
                      className="mb-2 text-sm px-4 py-2 rounded-lg bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-slate-100 transition font-medium flex items-center gap-2"
                    >
                      <span>{isExpanded ? '⚙️ Hide agent reasoning' : '⚙️ View agent reasoning'}</span>
                    </button>
                    {isExpanded && (
                      <div className="space-y-1">
                        {group.messages.map((msg: any) => renderMessage(msg))}
                      </div>
                    )}
                  </div>
                </div>
              );
            } else {
              return renderMessage(group.message);
            }
          })}
          {isLoading && (
            <div className="flex justify-start mt-6">
              <div className="text-slate-400 text-sm px-6 py-4 bg-slate-800 rounded-2xl flex items-center gap-3 shadow-lg">
                <span className="flex gap-2">
                  <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-bounce" />
                  <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </span>
                <span>Analyzing...</span>
              </div>
            </div>
          )}
          {messages.filter(m => m.type === 'streaming').map((msg) => (
            <div key={msg.id} className="flex justify-start mb-6">
              <div className="max-w-md lg:max-w-2xl bg-slate-800 text-slate-100 px-6 py-4 rounded-2xl border border-slate-700 shadow-lg">
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area - Fixed at bottom, matches home screen */}
      <div className="bg-slate-900/50 backdrop-blur-sm border-t border-slate-700/50 px-8 py-6 shadow-xl">
        <div className="max-w-4xl mx-auto flex gap-3">
          <div className="flex-1 relative group">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend(inputValue)}
              placeholder="Ask about your sales data..."
              disabled={isLoading}
              className="w-full px-6 py-4 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-100 placeholder-slate-500 disabled:opacity-50 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 transition-all"
            />
            <div className="absolute inset-0 rounded-xl bg-linear-to-r from-indigo-500/0 via-indigo-500/0 to-indigo-500/0 group-focus-within:from-indigo-500/10 group-focus-within:via-indigo-500/5 group-focus-within:to-indigo-500/10 pointer-events-none" />
          </div>
          <button
            onClick={() => handleSend(inputValue)}
            disabled={!inputValue.trim() || isLoading}
            className="px-8 py-4 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed transition font-semibold text-lg"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
