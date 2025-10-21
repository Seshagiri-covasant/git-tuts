import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';

// Type definitions for Speech Recognition API
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionInterface {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
}

interface VoiceControlsProps {
  onFinalVoiceMessage: (message: string) => void;
}


const VoiceControls: React.FC<VoiceControlsProps> = ({ onFinalVoiceMessage }) => {
  const { isVoiceEnabled } = useAppContext();
  const recognitionRef = useRef<SpeechRecognitionInterface | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [displayTranscript, setDisplayTranscript] = useState('');
  const transcriptRef = useRef(''); // To store the actual transcript

  useEffect(() => {
    if (!isVoiceEnabled) {
      stopRecording();
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true; // Keeps listening until manually stopped
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptChunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcriptChunk;
        } else {
          interim += transcriptChunk;
        }
      }

      const currentTranscript = final || interim;
      transcriptRef.current = final || transcriptRef.current;
      setDisplayTranscript(currentTranscript);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
    };

    recognitionRef.current = recognition;

    return () => stopRecording();
  }, [isVoiceEnabled]);

  const startRecording = () => {
    transcriptRef.current = '';
    setDisplayTranscript('');
    setIsRecording(true);
    recognitionRef.current?.start();
  };

  const stopRecording = () => {
    recognitionRef.current?.stop();
    setIsRecording(false);

    const finalMessage = transcriptRef.current.trim();
    if (finalMessage) {
      onFinalVoiceMessage(finalMessage);
      transcriptRef.current = '';
      setDisplayTranscript('');
    }
  };

  if (!isVoiceEnabled) return null;

  return (
    <div className="p-2 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
      <div className="flex items-center space-x-2">
        {isRecording ? (
          <>
            <button
              onClick={stopRecording}
              className="p-2 rounded-md bg-red-600 text-white hover:bg-red-700 transition-colors"
            >
              <Square size={18} />
            </button>
            <div className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              {displayTranscript || 'Listening...'}
            </div>
            <div className="flex items-center space-x-1">
              <span className="h-2 w-2 bg-red-500 rounded-full animate-pulse"></span>
              <span className="text-xs text-gray-500 dark:text-gray-400">Recording</span>
            </div>
          </>
        ) : (
          <>
            <button
              onClick={startRecording}
              className="p-2 rounded-md bg-[#6658dd] text-white transition-colors"
            >
              <Mic size={18} />
            </button>
            <div className="flex-1 text-sm text-gray-500 dark:text-gray-400">
              Click the mic to speak your message
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default VoiceControls;
