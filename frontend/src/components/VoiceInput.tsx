import { useState, useEffect, useCallback } from 'react';
import { Mic } from 'lucide-react';

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  isListening?: boolean;
}

export function VoiceInput({ onTranscript }: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recog = new SpeechRecognition();
    recog.continuous = false;
    recog.interimResults = false;
    recog.lang = 'en-IN'; // Default to English (India) given the context, or just 'en-US'

    recog.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onTranscript(transcript);
      setIsRecording(false);
    };

    recog.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
    };

    recog.onend = () => {
      setIsRecording(false);
    };

    setRecognition(recog);
  }, [onTranscript]);

  const toggleRecording = useCallback(() => {
    if (!recognition) return;

    if (isRecording) {
      recognition.stop();
    } else {
      recognition.start();
      setIsRecording(true);
    }
  }, [recognition, isRecording]);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={toggleRecording}
      className={`flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-300 ${
        isRecording 
          ? 'bg-red-50 text-red-600 animate-pulse shadow-sm shadow-red-100' 
          : 'text-paper-700 hover:text-paper-900 hover:bg-paper-100'
      }`}
      title={isRecording ? 'Stop recording' : 'Voice input'}
    >
      {isRecording ? <Mic size={18} /> : <Mic size={18} />}
    </button>
  );
}
