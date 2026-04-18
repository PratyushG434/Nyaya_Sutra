import { useState, useCallback } from 'react';
import { Message, Mode, UploadedFile, CitizenChatResponse, LawyerChatResponse } from '../types';

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
        let data: CitizenChatResponse | LawyerChatResponse;

        if (currentMode === 'citizen') {
          // Citizen mode: Send JSON to /api/chat
          const history = [...modeMessages[currentMode], userMessage].map(((m) => ({
            role: m.role,
            content: m.content,
          })));

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

          data = await response.json();
        } else {
          // Lawyer mode: Send FormData to /api/lawyer-chat
          const formData = new FormData();
          formData.append('message', content);
          formData.append('mode', 'advocate');

          // If there are attachments, add the first file to the form
          if (attachments && attachments.length > 0) {
            // Note: The file was already uploaded via /api/upload
            // We need to fetch it and add it to FormData
            // For now, we'll just send the filename
            // TODO: Improve file handling if backend needs actual file bytes
            const firstFile = attachments[0];
            if (firstFile.url) {
              // Fetch the file and add to FormData
              try {
                const fileResponse = await fetch(firstFile.url);
                const fileBlob = await fileResponse.blob();
                formData.append('file', fileBlob, firstFile.name);
              } catch (err) {
                console.error('Error fetching file for lawyer chat:', err);
              }
            }
          }

          const response = await fetch(`${API_BASE_URL}/lawyer-chat`, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it with boundary
          });

          if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
          }

          data = await response.json();
        }

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
          type: data.type,
          agents: 'agents' in data ? data.agents : undefined,
          route: 'route' in data ? data.route : undefined,
          used_file: 'used_file' in data ? data.used_file : undefined,
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
    [modeMessages, currentMode]
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
