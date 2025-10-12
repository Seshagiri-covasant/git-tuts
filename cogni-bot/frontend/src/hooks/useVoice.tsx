import { useState, useEffect, useCallback } from 'react';

interface UseVoiceProps {
  enabled: boolean;
}

interface UseVoiceReturn {
  isRecording: boolean;
  startRecording: () => void;
  stopRecording: () => void;
  transcript: string;
  isSupported: boolean;
  speak: (text: string) => void;
  isSpeaking: boolean;
  stopSpeaking: () => void;
}

export const useVoice = ({ enabled }: UseVoiceProps): UseVoiceReturn => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    // Check if browser supports speech recognition
    const speechSupported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
    setIsSupported(speechSupported);
    
    if (speechSupported && enabled) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      
      recognition.onresult = (event:any) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        setTranscript(finalTranscript || interimTranscript);
      };
      
      recognition.onerror = (event:any) => {
        setIsRecording(false);
      };
      
      recognition.onend = () => {
        setIsRecording(false);
      };
      
      setRecognition(recognition);
    }
    
    return () => {
      if (recognition) {
        recognition.onresult = null;
        recognition.onend = null;
        recognition.onerror = null;
        if (isRecording) {
          recognition.stop();
        }
      }
    };
  }, [enabled]);

  const startRecording = useCallback(() => {
    if (recognition && enabled) {
      setTranscript('');
      setIsRecording(true);
      recognition.start();
    }
  }, [recognition, enabled]);

  const stopRecording = useCallback(() => {
    if (recognition && isRecording) {
      recognition.stop();
      setIsRecording(false);
    }
  }, [recognition, isRecording]);

  const speak = useCallback((text: string) => {
    if ('speechSynthesis' in window && enabled) {
      window.speechSynthesis.cancel(); // Cancel any ongoing speech
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  }, [enabled]);

  const stopSpeaking = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  // Clean up speech synthesis on unmount
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    transcript,
    isSupported,
    speak,
    isSpeaking,
    stopSpeaking,
  };
};