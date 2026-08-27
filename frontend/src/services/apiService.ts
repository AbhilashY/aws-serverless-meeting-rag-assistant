import axios, {
  AxiosInstance
} from 'axios';

import {
  fetchAuthSession
} from 'aws-amplify/auth';

interface RAGSource {
  uri?: string;
  score?: number;
}

interface RAGResponse {
  success: boolean;
  query: string;
  answer: string;
  sources: RAGSource[];
  timestamp: string;
}

function generateConversationId(): string {
  return `conv_${Date.now()}_${Math.random()
    .toString(36)
    .substring(2, 11)}`;
}

class APIService {
  private apiClient: AxiosInstance;

  constructor() {
    const baseURL =
      process.env.REACT_APP_API_GATEWAY_ENDPOINT ||
      '';

    this.apiClient = axios.create({
      baseURL,
      timeout: 70000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.apiClient.interceptors.request.use(
      async (config) => {
        const session =
          await fetchAuthSession();

        const idToken =
          session.tokens?.idToken?.toString();

        if (!idToken) {
          throw new Error(
            'User is not authenticated'
          );
        }

        config.headers.Authorization =
          idToken;

        return config;
      }
    );
  }

  async queryRAG(
    userQuery: string,
    conversationId?: string
  ): Promise<RAGResponse> {
    try {
      const response =
        await this.apiClient.post(
          '/query',
          {
            query: userQuery,
            conversation_id:
              conversationId ||
              generateConversationId()
          }
        );

      return {
        success: true,
        query: userQuery,
        answer:
          response.data.answer ||
          'No answer returned.',
        sources:
          response.data.sources || [],
        timestamp:
          new Date().toISOString()
      };
    } catch (error: any) {
      console.error(
        'Error querying RAG:',
        error
      );

      throw new Error(
        error.response?.data?.error ||
        error.response?.data?.message ||
        error.message ||
        'Unable to query meeting transcripts'
      );
    }
  }
}

const apiService = new APIService();

export default apiService;
