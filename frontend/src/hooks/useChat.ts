import { useState, useCallback, useEffect } from 'react';
import { Message, Mode, UploadedFile } from '../types';

const FLASK_BASE_URL = 'http://localhost:5000';

export function useChat(mode: Mode) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const storageKey = `nyaya_saathi_chat_${mode}`;

  // Initialize messages from localStorage on mount or when mode changes
  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Convert string timestamps back to Date objects
        const hydrated = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(hydrated);
      } catch (e) {
        console.error('Failed to parse chat history from localStorage', e);
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  }, [mode, storageKey]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(storageKey, JSON.stringify(messages));
    }
  }, [messages, storageKey]);

  const sendMessage = useCallback(
    async (content: string, attachments?: UploadedFile[]) => {
      if (!content.trim() && (!attachments || attachments.length === 0)) return;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: new Date(),
        attachments,
      };

      setMessages((prev) => {
        const updated = [...prev, userMessage];
        localStorage.setItem(storageKey, JSON.stringify(updated));
        return updated;
      });
      
      setIsLoading(true);
      setError(null);

      try {
        // Use the most up-to-date messages for history
        const history = [...messages, userMessage].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await fetch(`${FLASK_BASE_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: content,
            mode,
            history,
            files: attachments?.map((f) => f.name),
          }),
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
        };

        setMessages((prev) => {
          const updated = [...prev, assistantMessage];
          localStorage.setItem(storageKey, JSON.stringify(updated));
          return updated;
        });
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to connect to server.'
        );
        // We keep the user message so it shows in history even if the response failed
      } finally {
        setIsLoading(false);
      }
    },
    [messages, mode, storageKey]
  );

  const uploadFile = useCallback(async (file: File): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${FLASK_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('File upload failed');
    }

    const data = await response.json();

    return {
      name: file.name,
      size: file.size,
      type: file.type,
      url: data.url,
    };
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(storageKey);
    setError(null);
  }, [storageKey]);

  return { messages, isLoading, error, sendMessage, uploadFile, clearChat };
}
