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
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingContentRef = useRef('');

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

  // Streaming behavior uses a ref to accumulate chunks and prevent async state issues
  const appendStreamingMessage = (chunk: string) => {
    // filter out dot-only chunks
    const trimmed = chunk.trim();
    if (trimmed === '•' || trimmed === '·' || trimmed === '.') return;

    // Immediately accumulate to ref (synchronous)
    streamingContentRef.current += chunk;

    // Update state with complete accumulated content
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
    // finalize: clear ref, remove streaming bubble, append final answer
    streamingContentRef.current = '';
    setMessages((prev) => {
      const withoutStreaming = prev.filter((m) => m.type !== 'streaming');
      return [
        ...withoutStreaming,
        { id: `${Date.now()}-final`, type: 'final', content },
      ];
    });
  };

  const suggestedQuestions = [
    'Which product had highest sales?',
    'Show me sales by region as pie chart',
    'What is the monthly sales trend?',
    'Which age group spends the most?'
  ];

  // Connect to WebSocket
  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/ws');

    websocket.onopen = () => {
      console.log('Connected!');
      console.log('✅ Connected to backend on ws://localhost:8000/ws');
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received message:', data);

        const rawType = String(data.type ?? '').toUpperCase();
        const messageText = typeof data.message === 'string' ? data.message : '';
        const isFinalAnswer = rawType === 'FINAL_ANSWER' || rawType === 'ANSWER';

        if (rawType === 'DONE') {
          setIsLoading(false);
          return;
        }

        if (isFinalAnswer) {
          if (messageText.includes('===') || messageText.includes('---')) {
            return;
          }

          // append final answer as its own message
          finalizeStreamingMessage(messageText);
        } else if (rawType === 'UPDATE' || rawType === 'CHUNK') {
          // decide whether this is a streaming chunk (small token) or a pipeline update
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
      console.log('Error:', error);
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('Disconnected from backend');
      setWs(null);
    };

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (question: string) => {
    console.log("handleSend called with:", question);
    if (!question.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

    console.log('Sending:', question);
    // Add user message - NEVER clear, only append
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

  // Determine color and style for pipeline messages based on content
  const getPipelineStyle = (content: string) => {
    if (content.includes('Orchestrator')) {
      return { bg: 'bg-gray-700', text: 'text-gray-200', icon: '🎯' };
    } else if (content.includes('Memory')) {
      return { bg: 'bg-purple-900', text: 'text-purple-100', icon: '🧠', italic: true };
    } else if (content.includes('Clarifier')) {
      return { bg: 'bg-indigo-900', text: 'text-indigo-100', icon: '🔀' };
    } else if (content.includes('Analysis')) {
      return { bg: 'bg-blue-900', text: 'text-blue-100', icon: '🤖' };
    } else if (content.includes('Using tool')) {
      return { bg: 'bg-green-900', text: 'text-green-100', icon: '🛠️', mono: true };
    } else if (content.includes('Chart saved')) {
      return { bg: 'bg-teal-900', text: 'text-teal-100', icon: '✅' };
    }
    return { bg: 'bg-gray-700', text: 'text-gray-200', icon: '•' };
  };

  // Render message based on type
  const renderMessage = (msg: any) => {
    if (msg.type === 'user') {
      return (
        <div key={msg.id} className="flex justify-end mb-4">
          <div className="max-w-xs lg:max-w-md bg-blue-500 text-white px-4 py-3 rounded-xl shadow-lg wrap-break-word">
            {msg.content}
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
          <div key={msg.id} className="flex justify-start mb-1.5">
            <div className={`text-xs px-3 py-1.5 rounded-lg ${style.bg} ${style.text} shadow-sm ${style.italic ? 'italic' : ''} ${style.mono ? 'font-mono' : ''}`}>
              <span className="mr-1">{style.icon}</span>
              {driveUrl ? (
                <>
                  {msg.content.replace(driveUrl, '')}
                  <a href={driveUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">
                    {driveUrl}
                  </a>
                </>
              ) : (
                msg.content
              )}
            </div>
          </div>
        );
      }
      
      // Regular pipeline message
      return (
        <div key={msg.id} className="flex justify-start mb-1.5">
          <div className={`text-xs px-3 py-1.5 rounded-lg ${style.bg} ${style.text} shadow-sm ${style.italic ? 'italic' : ''} ${style.mono ? 'font-mono' : ''}`}>
            <span className="mr-1">{style.icon}</span>
            {msg.content}
          </div>
        </div>
      );
    }

    if (msg.type === 'streaming') {
      return (
        <div key={msg.id} className="flex justify-start mb-4">
          <div className="max-w-md lg:max-w-2xl bg-gray-800 text-gray-100 px-5 py-3 rounded-xl border border-gray-700 shadow-lg">
            <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
              {msg.content}
            </p>
          </div>
        </div>
      );
    }

    if (msg.type === 'chart') {
      return (
        <div key={msg.id} className="flex justify-start mb-4">
          <img
            src={msg.imageUrl}
            alt="Generated chart"
            className="rounded-xl max-w-2xl w-full mt-2 border border-gray-700"
          />
        </div>
      );
    }

    if (msg.type === 'final') {
      const cleanedContent = msg.content
        .replace(/!\[.*?\]\(.*?\)/g, '')
        .replace(/\(sandbox:[^)]+\)/g, '')
        .trim();

      // Final answer with markdown rendering
      return (
        <div key={msg.id} className="flex justify-start mb-6 mt-6">
          <div className="max-w-md lg:max-w-2xl bg-gray-800 text-gray-100 px-5 py-4 rounded-xl border-2 border-gray-700 shadow-lg">
            <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-2">{children}</p>,
                  li: ({ children }) => <li className="ml-4 list-disc">{children}</li>,
                  ul: ({ children }) => <ul className="mb-2">{children}</ul>,
                  code: ({ children }) => (
                    <code className="bg-gray-900 px-1.5 py-0.5 rounded text-gray-100 font-mono text-xs">
                      {children}
                    </code>
                  ),
                  a: ({ children, href }) => {
                    // Convert sandbox:/ URLs to localhost:8000
                    let finalHref = href;
                    if (href && href.startsWith('sandbox:/')) {
                      finalHref = href.replace(/^sandbox:\//, 'http://localhost:8000/');
                    }
                    return (
                      <a href={finalHref} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">
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

  // Empty state
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="min-h-screen bg-linear-to-b from-gray-900 to-black flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-2xl">
          {/* Title and Subtitle */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-100 mb-2">
              📊 Data Analysis Agent
            </h1>
            <p className="text-xl text-gray-400">
              Ask anything about your sales data
            </p>
          </div>

          {/* Input Box */}
          <div className="mb-8">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend(inputValue)}
                placeholder="Ask about sales data..."
                className="flex-1 px-4 py-3 rounded-xl border border-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500 bg-gray-800 text-gray-100 placeholder-gray-500"
              />
              <button
                onClick={() => handleSend(inputValue)}
                disabled={!inputValue.trim()}
                className="px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed transition font-semibold"
              >
                ➜
              </button>
            </div>
          </div>

          {/* Suggested Questions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {suggestedQuestions.map((question, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestedQuestion(question)}
                className="p-4 text-left rounded-xl border border-gray-700 hover:bg-gray-800 hover:border-gray-600 transition text-gray-300 text-sm font-medium hover:shadow-lg"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Chat state
  return (
    <div className="min-h-screen bg-linear-to-b from-gray-900 to-black flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4 shadow-lg sticky top-0">
        <h1 className="text-2xl font-bold text-gray-100">📊 Data Analysis Agent</h1>
        <p className="text-sm text-gray-400">Multi-agent sales analysis system</p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto space-y-2">
          {messages.filter(m => m.type !== 'streaming').map((msg) => renderMessage(msg))}
          {isLoading && (
            <div className="flex justify-start mt-4">
              <div className="text-gray-400 text-sm px-4 py-3 bg-gray-800 rounded-xl flex items-center gap-2 shadow-lg">
                <span className="flex gap-1.5">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </span>
                <span>Analyzing...</span>
              </div>
            </div>
          )}
          {/* Typing area for streaming bubble (growing text) */}
          {messages.filter(m => m.type === 'streaming').map((msg) => (
            <div key={msg.id} className="flex justify-start mb-4">
              <div className="max-w-md lg:max-w-2xl bg-gray-800 text-gray-100 px-5 py-3 rounded-xl border border-gray-700 shadow-lg">
                <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area (Fixed at bottom) */}
      <div className="bg-gray-900 border-t border-gray-800 px-6 py-4 shadow-xl">
        <div className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend(inputValue)}
            placeholder="Ask about your sales data..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 rounded-xl border border-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:bg-gray-800 disabled:text-gray-500 bg-gray-800 text-gray-100 placeholder-gray-500"
          />
          <button
            onClick={() => handleSend(inputValue)}
            disabled={!inputValue.trim() || isLoading}
            className="px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed transition font-semibold"
          >
            ➜
          </button>
        </div>
      </div>
    </div>
  );
}
