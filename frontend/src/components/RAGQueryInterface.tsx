import React, {
  useEffect,
  useRef,
  useState
} from 'react';

import apiService from '../services/apiService';
import './RAGQueryInterface.css';

interface Source {
  uri?: string;
  score?: number;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Source[];
}

const RAGQueryInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConversationId(
      `conv_${Date.now()}_${Math.random()
        .toString(36)
        .substring(2, 11)}`
    );
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth'
    });
  }, [messages]);

  const handleSubmitQuery = async (
    event: React.FormEvent
  ) => {
    event.preventDefault();

    const query = inputQuery.trim();

    if (!query || loading) {
      return;
    }

    const userMessage: Message = {
      id: `msg_${Date.now()}_user`,
      type: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };

    setMessages((previousMessages) => [
      ...previousMessages,
      userMessage
    ]);

    setInputQuery('');
    setLoading(true);

    try {
      const response = await apiService.queryRAG(
        query,
        conversationId
      );

      const assistantMessage: Message = {
        id: `msg_${Date.now()}_assistant`,
        type: 'assistant',
        content: response.answer,
        timestamp:
          response.timestamp ||
          new Date().toISOString(),
        sources: response.sources || []
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        assistantMessage
      ]);
    } catch (error: any) {
      console.error(
        'Error querying RAG API:',
        error
      );

      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        type: 'assistant',
        content:
          error?.message ||
          'Sorry, there was an error processing your query. Please try again.',
        timestamp: new Date().toISOString()
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        errorMessage
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getSourceName = (
    source: Source
  ): string => {
    if (!source.uri) {
      return 'Meeting transcript';
    }

    const parts = source.uri.split('/');

    return (
      parts[parts.length - 1] ||
      'Meeting transcript'
    );
  };

  return (
    <div className="rag-query-container">
      <div className="chat-header">
        <h2>
          🤖 Meeting RAG Assistant
        </h2>

        <p>
          Ask questions about your meeting
          transcripts
        </p>
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>
              Welcome to Meeting RAG Assistant
            </h3>

            <p>
              Ask me anything about your indexed
              meeting transcripts.
            </p>

            <ul className="example-queries">
              <li>
                When is the customer portal
                production deployment scheduled?
              </li>

              <li>
                What could cause the deployment
                to be cancelled?
              </li>

              <li>
                How long will production be
                monitored?
              </li>

              <li>
                What is the rollback plan?
              </li>
            </ul>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`message message-${message.type}`}
          >
            <div className="message-content">
              <p>{message.content}</p>

              {message.sources &&
                message.sources.length > 0 && (
                  <div className="sources">
                    <h4>📚 Sources</h4>

                    <ul>
                      {message.sources.map(
                        (source, index) => (
                          <li key={index}>
                            <strong>
                              {getSourceName(
                                source
                              )}
                            </strong>

                            {source.score !==
                              undefined && (
                              <>
                                <br />

                                <small>
                                  Relevance:{' '}
                                  {source.score.toFixed(
                                    3
                                  )}
                                </small>
                              </>
                            )}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </div>

            <span className="timestamp">
              {new Date(
                message.timestamp
              ).toLocaleTimeString()}
            </span>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant loading">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>

            <small>
              Searching meeting transcripts...
            </small>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSubmitQuery}
        className="query-form"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(event) =>
            setInputQuery(event.target.value)
          }
          placeholder="Ask a question about your meetings..."
          disabled={loading}
          className="query-input"
        />

        <button
          type="submit"
          disabled={
            loading ||
            !inputQuery.trim()
          }
          className="submit-button"
        >
          {loading
            ? '⏳ Processing...'
            : '📤 Send'}
        </button>
      </form>
    </div>
  );
};

export default RAGQueryInterface;
