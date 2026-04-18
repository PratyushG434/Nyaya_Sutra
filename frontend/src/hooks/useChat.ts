import { useState, useCallback } from 'react';
import { Message, Mode, UploadedFile, ChatResponse } from '../types';

const API_BASE_URL = '/api';

export function useChat(currentMode: Mode) {
  // Store messages for both modes in memory (clears on refresh)
  const [modeMessages, setModeMessages] = useState<Record<Mode, Message[]>>({
    citizen: [],
    lawyer: [],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active messages for the current mode
  const messages = modeMessages[currentMode];

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

      // Add user message to the current mode's history
      setModeMessages((prev) => ({
        ...prev,
        [currentMode]: [...prev[currentMode], userMessage],
      }));
      
      setIsLoading(true);
      setError(null);

      try {
        const history = [...messages, userMessage].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await fetch(`${API_BASE_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: content,
            mode: currentMode,
            history,
            files: attachments?.map((f) => f.name),
          }),
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        const data: ChatResponse = await response.json();

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
          timeline: data.timeline,
          audit_results: data.audit_results,
        };

        setModeMessages((prev) => ({
          ...prev,
          [currentMode]: [...prev[currentMode], assistantMessage],
        }));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to connect to server.'
        );
      } finally {
        setIsLoading(false);
      }
    },
    [messages, currentMode]
  );

  const uploadFile = useCallback(async (file: File): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
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
    setModeMessages((prev) => ({
      ...prev,
      [currentMode]: [],
    }));
    setError(null);
  }, [currentMode]);

  return { messages, isLoading, error, sendMessage, uploadFile, clearChat };
}
