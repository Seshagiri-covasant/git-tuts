import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAppContext } from "../../context/AppContext";
import { getAllInteractions, createInteraction, getQuery, getConversationStatus, rateInteraction, getInteractionRating, getConversationInteractionCount, getBAInsights, getVisualization, getInteractionResultPage, handleHumanApproval } from "../../services/api";
import { InteractionResultMeta } from "../../types";
import { Send, Mic, MicOff, Bug, X, Lightbulb, BarChart3, Download, Paperclip, FileText, FileIcon, AlertTriangle, MessageSquare, Database } from "lucide-react";
import { DebugPanel } from "../DebugPanel";
import VoiceControls from "./VoiceControls";
import ProcessingStatusIndicator from "../ProcessingStatusIndicator";
import BAInsightsModal from '../../Modals/BAInsightsModal';
import VisualizationModal from '../../Modals/VisualizationModal';
import HumanApprovalDialog from '../HumanApprovalDialog';
// import ApprovalRequestCard from '../ApprovalRequestCard';
import { exportToCSV, generateCSVFilename } from '../../utils/csvUtils';

import { createMessagePoller, createStatusPoller } from '../../utils/smartPolling';
import { getErrorMessage } from '../../utils/errorHandler';

const ChatInterface: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    // conversations,
    selectedConversationId,
    isVoiceEnabled,
    toggleVoice,
    setIsSpeaking,
    selectedConversationName,
    chatbots,
    selectedChatbotId,
  } = useAppContext();
  
  // console.log('ChatInterface rendering with:', { selectedConversationId, selectedChatbotId });
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [page, setPage] = useState(0);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [debugSteps, setDebugSteps] = useState<any[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevScrollHeight = useRef(0);
  const [debugData, setDebugData] = useState<any>(null);
  const [interaction, setInteraction] = useState<any[]>([]);
  const [isLast, setIsLast] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [pollingForPending, setPollingForPending] = useState(false);
  // const pollingRef = useRef<number | null>(null);
  
  // Add conversation switching loading state
  const [conversationLoading, setConversationLoading] = useState(false);
  
  // Smart polling refs
  const messagePollerRef = useRef<any>(null);
  const statusPollerRef = useRef<any>(null);
  
  // Interaction limit state
  const [interactionCount, setInteractionCount] = useState(0);
  const [maxInteractions] = useState(10);
  const [interactionLimitReached, setInteractionLimitReached] = useState(false);
  
  // Add processing status state
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [showProcessingStatus, setShowProcessingStatus] = useState(false);
  const [, setPollingError] = useState<string | null>(null);
  const [, setPollingFailureCount] = useState(0);

  // Enhanced clarification state for human-in-the-loop
  const [clarificationSuggestions, setClarificationSuggestions] = useState<string[]>([]);
  const [showClarificationBar, setShowClarificationBar] = useState<boolean>(true);
  const [clarificationContext, setClarificationContext] = useState<{
    priority: string;
    question: string;
    step: number;
    totalSteps: number;
  } | null>(null);
  const [isInClarificationMode, setIsInClarificationMode] = useState<boolean>(false);

  const [baModalOpen, setBaModalOpen] = useState(false);
  const [baModalSummary, setBaModalSummary] = useState<string | null>(null);
  const [baLoading, setBaLoading] = useState(false);
  const [baUserQuery, setBaUserQuery] = useState<string>("");
  
  // Visualization modal states
  const [visualizationModalOpen, setVisualizationModalOpen] = useState(false);
  const [chartConfig, setChartConfig] = useState<any>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartUserQuery, setChartUserQuery] = useState<string>("");
  
  // Store visualization parameters for regeneration
  const [visualizationParams, setVisualizationParams] = useState<{
    table: any[];
    prompt: string;
    chatbotId: string;
  } | null>(null);
  
  // Rating states
  const [ratings, setRatings] = useState<{ [key: string]: number }>({});
  const [ratingLoading, setRatingLoading] = useState<{ [key: string]: boolean }>({});
  
  // Human Approval State
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalRequest, setApprovalRequest] = useState<any>(null);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<any>(null);

  // Paged table result state (keyed by interactionId)
  const [resultMeta, setResultMeta] = useState<{[key: string]: InteractionResultMeta | null}>({});
  const resultMetaRef = useRef<{[key: string]: InteractionResultMeta | null}>({});
  
  // Keep ref in sync with state
  useEffect(() => {
    resultMetaRef.current = resultMeta;
  }, [resultMeta]);
  const [currentPageByIx, setCurrentPageByIx] = useState<{[key: string]: number}>({});
  const [rowsByIxPage, setRowsByIxPage] = useState<{[key: string]: {[page: number]: any[]}}>({});
  const rowsByIxPageRef = useRef<{[key: string]: {[page: number]: any[]}}>({});
  const [pagedInit, setPagedInit] = useState<{[key: string]: boolean}>({});
  const pagedInitRef = useRef<{[key: string]: boolean}>({});
  const [pageInputByIx, setPageInputByIx] = useState<{[key: string]: string}>({});
  const [pageSizeUiByIx, setPageSizeUiByIx] = useState<{[key: string]: number}>({});
  const [currentUiPageByIx, setCurrentUiPageByIx] = useState<{[key: string]: number}>({});
  
  // Keep refs in sync with state
  useEffect(() => {
    rowsByIxPageRef.current = rowsByIxPage;
  }, [rowsByIxPage]);
  
  useEffect(() => {
    pagedInitRef.current = pagedInit;
  }, [pagedInit]);

  // Removed unused ensureMeta function // Remove resultMeta dependency to prevent infinite loops

  const loadPage = useCallback(async (interactionId: string, pageIndex: number) => {
    if (!interactionId) return;
    const container = containerRef.current;
    const prevTop = container?.scrollTop ?? 0;
    const prevHeight = container?.scrollHeight ?? 0;

    setCurrentPageByIx(prev => ({ ...prev, [interactionId]: pageIndex }));
    try {
      const page = await getInteractionResultPage(interactionId, pageIndex);
      setRowsByIxPage(prev => ({
        ...prev,
        [interactionId]: { ...(prev[interactionId] || {}), [pageIndex]: page.rows }
      }));
    } catch (e) {
      // swallow for UI; meta may exist but page not ready yet
    } finally {
      // Restore scroll position relative to content height change without smooth behavior to avoid flicker
      requestAnimationFrame(() => {
        const c = containerRef.current;
        if (c) {
          const prevBehavior = c.style.scrollBehavior;
          c.style.scrollBehavior = 'auto';
          const newHeight = c.scrollHeight;
          const delta = newHeight - prevHeight;
          c.scrollTop = prevTop + delta;
          // Restore original behavior on next frame
          requestAnimationFrame(() => {
            c.style.scrollBehavior = prevBehavior;
          });
        }
      });
    }
  }, []);

  const ensureStoredPage = useCallback(async (interactionId: string, storedIndex: number) => {
    const cache = rowsByIxPageRef.current[interactionId] || {};
    if (cache[storedIndex]) return;
    
    await loadPage(interactionId, storedIndex);
  }, [loadPage]);

  // Auto-initialize pagination for assistant messages once they appear
  // Temporarily disabled to fix infinite loop
  // useEffect(() => {
  //   // displayedInteractions is derived lower; fallback to interaction state
  //   const msgs = interaction as any[];
  //   msgs
  //     .filter(m => m.role === 'assistant' && m.interactionId)
  //     .forEach(async (m) => {
  //       if (pagedInitRef.current[m.interactionId]) {
  //         return;
  //       }
  //       const meta = await ensureMeta(m.interactionId);
  //       if (meta) {
  //         setPagedInit(prev => ({ ...prev, [m.interactionId]: true }));
  //         loadPage(m.interactionId, 0);
  //       } else {
  //         // Mark as initialized even if no meta to prevent retries
  //         setPagedInit(prev => ({ ...prev, [m.interactionId]: true }));
  //       }
  //     });
  // }, [interaction, ensureMeta, loadPage]);
  
  // Document upload states
  const [uploadedDocuments, setUploadedDocuments] = useState<File[]>([]);
  const [showDocuments, setShowDocuments] = useState(false);
  
  const currentChatbot = chatbots.find(c => c.chatbot_id === selectedChatbotId);
  const llmName = currentChatbot?.current_llm_name;

  // Function to fetch interaction count from backend
  const fetchInteractionCount = useCallback(async () => {
    if (!selectedConversationId || !selectedChatbotId) return;
    
    try {
      const response = await getConversationInteractionCount(selectedConversationId, selectedChatbotId);
      if (response.status === 200) {
        const count = response.data.interaction_count;
        setInteractionCount(count);
        setInteractionLimitReached(count >= maxInteractions);
      }
    } catch (error) {
      console.error('Error fetching interaction count:', error);
    }
  }, [selectedConversationId, selectedChatbotId]);

  // Initial load
  useEffect(() => {
    // Clear previous interactions when switching conversations
    setInteraction([]);
    setPage(0);
    setIsLast(false);
    setPollingForPending(false);
    setShowProcessingStatus(false);
    setProcessingStatus(null);
    setPollingError(null);
    setConversationLoading(true);
    
    // Reset interaction limit state
    setInteractionCount(0);
    setInteractionLimitReached(false);
    
    // Reset pagination state
    setResultMeta({});
    setRowsByIxPage({});
    setCurrentPageByIx({});
    setPagedInit({});
    setPageInputByIx({});
    setPageSizeUiByIx({});
    setCurrentUiPageByIx({});
    
    // Stop any existing polling
    if (messagePollerRef.current) {
      messagePollerRef.current.stop();
    }
    if (statusPollerRef.current) {
      statusPollerRef.current.stop();
    }
    
    // Load new conversation interactions
    if (selectedConversationId && selectedChatbotId) {
      getAllInteraction(0, false);
      fetchInteractionCount(); // Fetch interaction count
    }
  }, [selectedConversationId, selectedChatbotId]);

  // Scroll to bottom after initial load
  useEffect(() => {
    if (page === 0 && containerRef.current && interaction.length > 0) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [interaction, page]);

  // Enhanced clarification parsing for human-in-the-loop
  const parseClarificationSuggestions = (content: string): { suggestions: string[], context?: any } => {
    try {
      const marker = 'CLARIFICATION_NEEDED:';
      let text = content;
      if (content.startsWith(marker)) {
        text = content.slice(marker.length).trim();
      }
      
      // Try to extract JSON array first
      const jsonMatch = text.match(/\[(.|\n|\r)*\]/);
      if (jsonMatch) {
        const arr = JSON.parse(jsonMatch[0]);
        if (Array.isArray(arr)) {
          return { suggestions: arr.map((s) => String(s)).slice(0, 3) };
        }
      }
      
      // Fallback: capture lines like "1. suggestion" up to 3 items
      const lines = text.split(/\r?\n/).map((l) => l.trim());
      const numbered = lines
        .map((l) => {
          const m = l.match(/^\d+\.\s*(.+)$/);
          return m ? m[1].trim() : null;
        })
        .filter((s): s is string => Boolean(s));
      
      if (numbered.length >= 1) {
        return { suggestions: numbered.slice(0, 3) };
      }
      
      // Check for targeted questions (new format)
      if (text.includes("I need a bit more information") || text.includes("Which of these tables")) {
        return { 
          suggestions: [text], 
          context: { isTargetedQuestion: true }
        };
      }
    } catch {}
    return { suggestions: [] };
  };

  const getAllInteraction = useCallback(async (pageNo: number, appendToTop: boolean) => {
    try {
      const container = containerRef.current;
      const prevHeight = container?.scrollHeight ?? 0;

      if (pageNo === 0) {
        setLoading(true);
        setLoadingProgress(0);
        
        // Simulate progress
        const progressInterval = setInterval(() => {
          setLoadingProgress(prev => {
            if (prev >= 80) {
              clearInterval(progressInterval);
              return prev;
            }
            return prev + 10;
          });
        }, 200);
      }

      if (!selectedConversationId || !selectedChatbotId) {
        console.log('Missing required IDs, skipping API call');
        return;
      }

      console.log('Fetching interactions:', { selectedConversationId, selectedChatbotId, pageNo });
      const response = await getAllInteractions(selectedConversationId, 5, pageNo, selectedChatbotId);
      console.log('API Response:', response);

      if (response.status === 200) {
        setIsLast(response.data?.last);
        console.log('Response data:', response.data);

        const flatMessages = response.data?.interactions.flatMap((msg: any) => {
          const userMessage = {
            id: `${msg?.interactionId}_user`,
            role: "user",
            content: msg.request,
            interactionId: msg.interactionId,
            conversationId: msg?.conversationId,
            timestamp: msg?.startTime
          };

          const assistantMessage = {
            id: `${msg?.interactionId}_assistant`,
            role: "assistant",
            content: msg?.final_result || "",
            timestamp: msg?.startTime,
            interactionId: msg.interactionId,
            conversationId: msg?.conversationId,
            request: false,
          };

          return [userMessage, assistantMessage];
        });
        console.log('Flat messages:', flatMessages);

        // For initial load (pageNo === 0), we want to show the latest messages first
        // For pagination (appendToTop === true), we want to prepend older messages
        if (pageNo === 0) {
          // Initial load: replace all messages with the latest ones
          setInteraction(flatMessages);
          // If we have any assistant messages, ensure processing indicator is off
          const hasAssistant = flatMessages.some((m: any) => m.role === 'assistant');
          if (hasAssistant) {
            setShowProcessingStatus(false);
            setProcessingStatus(null);
          }
          
          // Scroll to bottom to show latest messages
          setTimeout(() => {
            if (container) {
              container.scrollTop = container.scrollHeight;
            }
          }, 100);
        } else {
          // Pagination: prepend older messages to the top
          setInteraction((prev) => [...flatMessages, ...prev]);
          
          // Maintain scroll position when prepending older messages
          setTimeout(() => {
            if (appendToTop && container) {
              const newHeight = container.scrollHeight;
              container.scrollTop = newHeight - prevHeight;
            }
          }, 0);
        }
      } else {
        console.error('Failed to load interactions');
      }
    } catch (error) {
      console.error('Error loading interactions:', error);
    } finally {
      setTimeout(() => {
        setLoading(false);
        setLoadingProgress(0);
        setConversationLoading(false);
      }, 500);
    }
  }, [selectedConversationId, selectedChatbotId]);

  const handleScroll = () => {
    const container = containerRef.current;
    if (!container || loading || isLast) return; // 👈 check loading

    if (container.scrollTop <= 30) {
      prevScrollHeight.current = container.scrollHeight;

      setPage((prev) => prev + 5); // 👈 this will now only trigger once loading is false
    }
  };

  useEffect(() => {
    if (page === 0) return; 
    getAllInteraction(page, true);
  }, [page, getAllInteraction]);

  // (moved below displayedInteractions definition)

  // Filter out any duplicate messages and temporary assistant messages that have been replaced
   const displayedInteractions = useMemo(() => {
    return interaction.filter((msg, index, self) => {
      if (msg.id.startsWith('temp_assistant_')) {
        return false;
      }
      // For temporary messages, only keep the most recent one
      if (msg.id.startsWith('temp_')) {
        const lastIndex = self.map(m => m.id).lastIndexOf(msg.id);
        return index === lastIndex;
      }
      // For regular messages, remove duplicates by interactionId and role
      return index === self.findIndex((m: any) => 
        m.interactionId === msg.interactionId && 
        m.role === msg.role &&
        !m.id.startsWith('temp_')
      );
    }).sort((a, b) => {
      // Sort by timestamp to ensure chronological order (oldest to newest)
      const timeA = new Date(a.timestamp || a.startTime || 0).getTime();
      const timeB = new Date(b.timestamp || b.startTime || 0).getTime();
      return timeA - timeB;
    });
  }, [interaction]);

  // Enhanced clarification detection for human-in-the-loop
  useEffect(() => {
    if (!displayedInteractions || displayedInteractions.length === 0) return;
    const lastAssistant = [...displayedInteractions]
      .reverse()
      .find((m: any) => m.role === 'assistant' && typeof m.content === 'string');
    if (!lastAssistant) return;

    const content: string = lastAssistant.content || '';
    if (typeof content === 'string' && content.includes('CLARIFICATION_NEEDED:')) {
      const parsed = parseClarificationSuggestions(content);
      if (parsed.suggestions.length) {
        setClarificationSuggestions(parsed.suggestions);
        setShowClarificationBar(true);
        setIsInClarificationMode(true);
        
        // Extract context if available
        if (parsed.context?.isTargetedQuestion) {
          setClarificationContext({
            priority: 'general',
            question: parsed.suggestions[0],
            step: 1,
            totalSteps: 5
          });
        }
      }
    } else {
      // Clear on normal assistant responses
      setClarificationSuggestions([]);
      setShowClarificationBar(false);
      setIsInClarificationMode(false);
      setClarificationContext(null);
    }
  }, [displayedInteractions]);



  // Smart polling for new messages
  useEffect(() => {
    if (pollingForPending && selectedConversationId) {
      // Stop any existing poller
      if (messagePollerRef.current) {
        messagePollerRef.current.stop();
      }

      // Create new smart poller
      messagePollerRef.current = createMessagePoller();
      
      messagePollerRef.current.start(
        async () => {
          if (!selectedConversationId || !selectedChatbotId) {
            console.log('Missing required IDs, skipping API call');
            return;
          }
          
          const response = await getAllInteractions(selectedConversationId, 5, 0, selectedChatbotId);
          if (response.status === 200) {
            // Get the latest interaction from the response
            const latestInteraction = response.data?.interactions[0];
            
            // Debug: Log the interaction data
            console.log('🔍 DEBUG: Latest interaction:', latestInteraction);
            console.log('🔍 DEBUG: Interaction type:', latestInteraction?.interaction_type);
            console.log('🔍 DEBUG: Interaction keys:', Object.keys(latestInteraction || {}));
            console.log('🔍 DEBUG: Approval request:', latestInteraction?.approval_request);
            console.log('🔍 DEBUG: Clarification questions:', latestInteraction?.clarification_questions);
            
            // Check for human approval request
            if (latestInteraction?.interaction_type === 'human_approval') {
              // Handle human approval request
              console.log('Human approval detected:', latestInteraction);
              
              // Extract approval request data
              const approvalData = {
                message: latestInteraction.approval_request?.message || "I need to confirm some details before proceeding.",
                intent_summary: latestInteraction.approval_request?.intent_summary || {},
                clarification_questions: latestInteraction.clarification_questions || [],
                similar_columns: latestInteraction.similar_columns || [],
                requires_human_input: true,
                approval_type: latestInteraction.approval_request?.approval_type || 'intent_confirmation'
              };
              
              setApprovalRequest(approvalData);
              setPendingApproval(latestInteraction);
              setShowApprovalDialog(true);
              
              // Stop polling as we're waiting for human input
              if (messagePollerRef.current) {
                messagePollerRef.current.stop();
              }
              setPollingForPending(false);
              return;
            }
            
            // Check for clarification request
            if (latestInteraction?.interaction_type === 'clarification') {
              // Handle clarification request
              const clarificationMessage = {
                id: `clarification_${Date.now()}`,
                role: "assistant" as const,
                content: latestInteraction.question || "I need more information to help you.",
                timestamp: new Date().toISOString(),
                interactionId: `clarification_${Date.now()}`,
                conversationId: selectedConversationId,
                isClarification: true
              };
              
              setInteraction(prev => [...prev, clarificationMessage]);
              
              // Stop polling as we're waiting for human input
              if (messagePollerRef.current) {
                messagePollerRef.current.stop();
              }
              setPollingForPending(false);
              return;
            }
            
            // Only process if we have a valid latest interaction with a response
            if (latestInteraction?.final_result) {
              // Create the final messages array
              const finalMessages = response.data.interactions.flatMap((msg: any) => [
                {
                  id: `${msg.interactionId}_user`,
                  role: "user" as const,
                  content: msg.request,
                  interactionId: msg.interactionId,
                  conversationId: msg.conversationId,
                  timestamp: msg.startTime,
                  request: true,
                },
                {
                  id: `${msg.interactionId}_assistant`,
                  role: "assistant" as const,
                  content: msg.final_result || "",
                  timestamp: msg.startTime,
                  interactionId: msg.interactionId,
                  conversationId: msg.conversationId,
                  request: false,
                },
              ]);

              // Update the messages, removing any temporary ones
              setInteraction(prev => {
                // Keep only the messages that are not temporary
                const nonTempMessages = prev.filter(msg => !msg.id.startsWith('temp_'));
                // Merge with new messages from backend
                const updatedMessages = [...nonTempMessages, ...finalMessages];
                
                // Scroll to bottom to show the latest messages
                setTimeout(() => {
                  const container = containerRef.current;
                  if (container) {
                    container.scrollTop = container.scrollHeight;
                  }
                }, 100);
                
                return updatedMessages;
              });

              // Refresh interaction count after new interaction is completed
              fetchInteractionCount();

              // Keep processing indicator on until UI renders new assistant message
              setTimeout(() => {
                setPollingForPending(false);
                // Let the status poller control visibility to avoid flicker
              }, 300);
              setPollingError(null);
              setPollingFailureCount(0);
              
              return response; // Success - stop polling
            }
          }
          throw new Error('No final result yet'); // Continue polling
        },
        2000 // Poll every 2 seconds
      ).catch((error: any) => {
        console.error('Message polling failed:', error);
        // Do not surface timeout/connection warnings in UI; keep polling quietly
        setPollingFailureCount(prev => prev + 1);
        setPollingError(null);
      });
    }

    return () => {
      if (messagePollerRef.current) {
        messagePollerRef.current.stop();
      }
    };
  }, [pollingForPending, selectedConversationId, selectedChatbotId]);

  // Smart polling for processing status
  useEffect(() => {
    // Keep status polling active while processing is ongoing, even if the UI flag toggles
    if ((showProcessingStatus || pollingForPending) && selectedConversationId) {
      // Stop any existing status poller
      if (statusPollerRef.current) {
        statusPollerRef.current.stop();
      }

      // Create new smart status poller
      statusPollerRef.current = createStatusPoller();
      
      statusPollerRef.current.start(
        async () => {
          const response = await getConversationStatus(selectedConversationId);
          if (response.status === 200) {
            setProcessingStatus(response.data);
            
            // Hide status indicator if processing is completed or errored
            if (response.data.current_step === 'completed' || response.data.current_step === 'error') {
              setTimeout(() => {
                setShowProcessingStatus(false);
                setProcessingStatus(null);
              }, 2000); // Show completion for 2 seconds
              return response; // Success - stop polling
            }
          }
          throw new Error('Processing not complete yet'); // Continue polling
        },
        1000 // Poll every second
      ).catch((error: any) => {
        console.error('Status polling failed:', error);
        // Do not surface status polling failures in UI; keep existing state
      });
    }

    return () => {
      if (statusPollerRef.current) {
        statusPollerRef.current.stop();
      }
    };
  }, [showProcessingStatus, pollingForPending, selectedConversationId]);

  const handleSendMessage = async (customMessage?: string) => {
    const message = customMessage?.trim() || inputMessage.trim();
    if (!message) return;

    // Check interaction limit before sending
    if (interactionLimitReached) {
      console.log('Interaction limit reached');
      return;
    }

    const userMessageId = Date.now().toString();
    const tempUserMessage = {
      id: `temp_${userMessageId}`,
      role: "user" as const,
      content: message,
      timestamp: new Date().toISOString(),
      request: true,
      interactionId: userMessageId,
      conversationId: selectedConversationId,
    };

    // Show user message immediately
    setInteraction(prev => [...prev, tempUserMessage]);
    setInputMessage("");
    setIsTyping(true);

    // TODO: Future RAG integration - process uploadedDocuments here
    // const documentsForRAG = uploadedDocuments.map(doc => ({
    //   name: doc.name,
    //   size: doc.size,
    //   type: doc.type
    // }));

    // Show loading message for assistant
    const tempAssistantMessage = {
      id: `temp_assistant_${userMessageId}`,
      role: "assistant" as const,
      content: "",
      timestamp: new Date().toISOString(),
      interactionId: userMessageId,
      conversationId: selectedConversationId,
      isLoading: true
    };
    setInteraction(prev => [...prev, tempAssistantMessage]);

    // Show processing status indicator
    setShowProcessingStatus(true);
    setProcessingStatus({
      current_step: "initializing",
      progress: 0,
      message: "Starting AI processing..."
    });

    // Scroll to bottom
    setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);

    try {
      // Send to backend and capture immediate debug info
      const resp = await createInteraction(selectedConversationId, message, llmName);
      // If backend returned debug steps, show them immediately
      try {
        const steps = resp?.debug?.steps;
        if (Array.isArray(steps) && steps.length > 0) {
          setDebugSteps(steps);
          setShowDebugPanel(true);
        }
      } catch {}

      // Start polling for the actual response
      setPollingForPending(true);
      setPollingError(null); // Clear any previous errors
      
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = getErrorMessage(err);
      
      // Update the loading message to show specific error
      setInteraction(prev => prev.map(msg => 
        msg.id === `temp_assistant_${userMessageId}` 
          ? { 
              ...msg, 
              content: errorMessage, 
              isLoading: false,
              error: true
            }
          : msg
      ));
      
      // Hide processing status on error
      setShowProcessingStatus(false);
      setProcessingStatus(null);
      setPollingError(errorMessage);
    } finally {
      setIsTyping(false);
      setIsSpeaking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handlePickSuggestion = (s: string) => {
    setInputMessage(s);
    // Keep the suggestions visible so user can refine; they can dismiss
  };

  const handleDebugClick = async (conversationId: string, interactionId: string) => {
    // Find the assistant message in displayedInteractions
    const msg = displayedInteractions.find(
      (m) => m.interactionId === interactionId && m.role === "assistant"
    );
    
    if (msg) {
      try {
        const parsed = JSON.parse(msg.content);
        if (parsed && typeof parsed === 'object' && parsed.debug?.steps) {
          setDebugSteps(parsed.debug.steps);
          setShowDebugPanel(true);
          return;
        }
      } catch (e) {
        console.error('Error parsing debug information:', e);
      }
    }

    // Fallback: fetch from backend
    try {
      const response = await getQuery(conversationId, interactionId);
      if (response.data?.debug?.steps) {
        setDebugSteps(response.data.debug.steps);
        setShowDebugPanel(true);
      }
      setDebugData(response.data);
    } catch (error) {
      console.error('Error fetching debug info:', error);
      setDebugData(null);
    }
  };

  // Parse JSON content for table rendering
  const parseJsonContent = (content: string) => {
    try {
      // First try to parse the content directly
      const parsed = JSON.parse(content);
      return parsed;
    } catch {
      try {
        // If that fails, try to extract JSON from a string that might contain JSON
        const jsonMatch = content.match(/\{.*\}|\[.*\]/);
        if (jsonMatch) {
          return JSON.parse(jsonMatch[0]);
        }
      } catch {
        return null;
      }
      return null;
    }
  };

  // Safely render a value in table cell
  const renderCellValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "-";
    }
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  // Render table for JSON data with row count
  const renderTable = (jsonData: any[], rowCount?: number) => {
    // Safety check: ensure jsonData is a valid array
    if (!Array.isArray(jsonData) || jsonData.length === 0) {
      return <div className="mt-2 p-4 text-gray-500">No data to display</div>;
    }

    try {
      const allKeys = Array.from(
        new Set(jsonData.flatMap((item: any) => {
          if (item && typeof item === 'object') {
            return Object.keys(item);
          }
          return [];
        }))
      );

      if (allKeys.length === 0) {
        return <div className="mt-2 p-4 text-gray-500">No valid data columns found</div>;
      }

      return (
        <div className="mt-2">
          <div className="overflow-auto max-h-[400px]">
            <table className="min-w-full divide-y divide-gray-200 border rounded-lg shadow-md">
              <thead className="bg-gray-100 sticky top-0 z-10">
                <tr>
                  {allKeys.map((key) => (
                    <th
                      key={key}
                      className="px-4 py-2 text-left text-sm font-semibold text-gray-700"
                    >
                      {String(key).replace(/["\\]/g, "")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200 text-sm">
                {jsonData.map((row: any, idx: number) => (
                  <tr key={idx}>
                    {allKeys.map((key) => (
                      <td
                        key={key}
                        className="px-4 py-2 whitespace-nowrap"
                      >
                        {renderCellValue(row[key])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Row count display at bottom */}
          <div className="mt-2 px-2 py-1 text-sm text-gray-600 bg-gray-50 rounded-b-lg border-t">
            Fetched {rowCount || jsonData.length} rows
          </div>
        </div>
      );
    } catch (error) {
      console.error('Error rendering table:', error);
      return <div className="mt-2 p-4 text-red-500">Error displaying table data</div>;
    }
  };

  // Removed unused copyToClipboard function

  // State to hold BA context for regeneration
  const [baInteractionId, setBaInteractionId] = useState<string | undefined>(undefined);
  const [baTable, setBaTable] = useState<any[] | undefined>(undefined);

  const handleBAInsights = async (table: any[], prompt: string, interactionId?: string) => {
    if (!selectedChatbotId) {
      setBaModalSummary("Chatbot ID not available. Please select a chatbot first.");
      setBaModalOpen(true);
      return;
    }

    setBaLoading(true);
    setBaModalOpen(true);
    setBaModalSummary(null);
    setBaUserQuery(prompt);
    // Track which interaction this BA summary belongs to for caching/regeneration
    const effectiveInteractionId = interactionId || (debugData?.interactionId || undefined);
    setBaInteractionId(effectiveInteractionId);
    setBaTable(table);
    try {
      const res = await getBAInsights(table, prompt, selectedChatbotId, effectiveInteractionId, false);
      setBaModalSummary(res.data.summary);
    } catch (err) {
      setBaModalSummary("Failed to generate BA insights.");
    }
    setBaLoading(false);
  };

  const handleRegenerateBAInsights = async () => {
    if (!selectedChatbotId) return;
    setBaLoading(true);
    try {
      const res = await getBAInsights(baTable || [], baUserQuery || "", selectedChatbotId, baInteractionId || (debugData?.interactionId || undefined), true);
      setBaModalSummary(res.data.summary);
    } catch (err) {
      // keep prior summary if regenerate fails
    }
    setBaLoading(false);
  };

  const handleVisualize = async (table: any[], prompt: string) => {
    if (!selectedChatbotId) {
      setChartConfig({ error: "Chatbot ID not available. Please select a chatbot first." });
      setVisualizationModalOpen(true);
      return;
    }

    // Store parameters for regeneration
    setVisualizationParams({ table, prompt, chatbotId: selectedChatbotId });

    setChartLoading(true);
    setVisualizationModalOpen(true);
    setChartConfig(null);
    setChartUserQuery(prompt);
    try {
      const res = await getVisualization(table, prompt, "", selectedChatbotId);
      setChartConfig(res.data.chart_config);
    } catch (err) {
      setChartConfig({ error: "Failed to generate visualization." });
    }
    setChartLoading(false);
  };

  const handleRegenerateVisualization = async () => {
    if (!visualizationParams) {
      console.error('No visualization parameters available for regeneration');
      return;
    }

    setChartLoading(true);
    setChartConfig(null);
    try {
      const res = await getVisualization(
        visualizationParams.table, 
        visualizationParams.prompt, 
        "", 
        visualizationParams.chatbotId
      );
      setChartConfig(res.data.chart_config);
    } catch (err) {
      setChartConfig({ error: "Failed to regenerate visualization." });
    }
    setChartLoading(false);
  };

  // Human Approval Handlers
  const handleHumanApprovalResponse = async (response: any) => {
    if (!selectedConversationId || !pendingApproval) return;
    
    setApprovalLoading(true);
    try {
      const result = await handleHumanApproval(selectedConversationId, response);
      
      if (result.data) {
        // Handle the response from the backend
        if (result.data.interaction_type === 'human_approval') {
          // Still needs more approval
          setApprovalRequest(result.data);
          setPendingApproval(result.data);
        } else {
          // Approval completed, process the final response
          setShowApprovalDialog(false);
          setPendingApproval(null);
          setApprovalRequest(null);
          
          // Add the final response to the conversation
          if (result.data.final_result) {
            const finalMessage = {
              id: `approval_${Date.now()}`,
              role: "assistant" as const,
              content: result.data.final_result,
              timestamp: new Date().toISOString(),
              data: result.data.raw_result_set || [],
              sql: result.data.cleaned_query || '',
              interactionId: `approval_${Date.now()}`,
              conversationId: selectedConversationId,
            };
            setInteraction(prev => [...prev, finalMessage]);
          }
        }
      }
    } catch (error) {
      console.error('Error handling human approval:', error);
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleApprovalReject = () => {
    setShowApprovalDialog(false);
    setPendingApproval(null);
    setApprovalRequest(null);
  };

  const handleRating = async (conversationId: string, interactionId: string, rating: number) => {
    const ratingKey = `${conversationId}_${interactionId}`;
    
    try {
      // Optimistic update - immediately update UI
      setRatings(prev => ({ ...prev, [ratingKey]: rating }));
      setRatingLoading(prev => ({ ...prev, [ratingKey]: true }));
      
      await rateInteraction(conversationId, interactionId, rating);
    } catch (error) {
      console.error('Error rating interaction:', error);
      // Revert optimistic update on error
      setRatings(prev => {
        const newRatings = { ...prev };
        delete newRatings[ratingKey];
        return newRatings;
      });
    } finally {
      setRatingLoading(prev => ({ ...prev, [ratingKey]: false }));
    }
  };

  const handleDownloadCSV = (data: any[], userPrompt: string) => {
    try {
      const filename = generateCSVFilename(`nl2sql_${userPrompt.slice(0, 20).replace(/[^a-zA-Z0-9]/g, '_')}`);
      exportToCSV(data, filename);
    } catch (error) {
      console.error('Error downloading CSV:', error);
    }
  };

  const handleDocumentUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const newFiles = Array.from(files).filter(file => {
        const fileType = file.type;
        const fileName = file.name.toLowerCase();
        return (
          fileType === 'application/pdf' ||
          fileType === 'application/msword' ||
          fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
          fileName.endsWith('.pdf') ||
          fileName.endsWith('.doc') ||
          fileName.endsWith('.docx')
        );
      });
      
      setUploadedDocuments(prev => [...prev, ...newFiles]);
      // Reset the input value to allow re-uploading the same file
      event.target.value = '';
    }
  };

  const removeDocument = (index: number) => {
    setUploadedDocuments(prev => {
      const newDocs = prev.filter((_, i) => i !== index);
      // Close dropdown if no documents left
      if (newDocs.length === 0) {
        setShowDocuments(false);
      }
      return newDocs;
    });
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.toLowerCase().split('.').pop();
    if (extension === 'pdf') {
      return <FileText className="w-4 h-4 text-red-600" />;
    }
    return <FileIcon className="w-4 h-4 text-blue-600" />;
  };

  // Track which ratings we have already fetched to avoid duplicate calls
  const fetchedRatingsRef = useRef<Set<string>>(new Set());

  // Load existing ratings when interactions are loaded (fetch each only once)
  useEffect(() => {
    const keysToFetch: Array<{ conversationId: string; interactionId: string; key: string }> = [];

    for (const msg of interaction) {
      if (msg.role !== 'assistant' || !msg.conversationId || !msg.interactionId) continue;
      const key = `${msg.conversationId}_${msg.interactionId}`;
      if (ratings[key] !== undefined) continue; // already in state
      if (fetchedRatingsRef.current.has(key)) continue; // already fetched this session
      fetchedRatingsRef.current.add(key);
      keysToFetch.push({ conversationId: msg.conversationId, interactionId: msg.interactionId, key });
    }

    if (keysToFetch.length === 0) return;

    (async () => {
      try {
        const responses = await Promise.all(
          keysToFetch.map(({ conversationId, interactionId }) =>
            getInteractionRating(conversationId, interactionId).catch(() => ({ data: { rating: null } }))
          )
        );

        const next: { [k: string]: number } = {} as any;
        responses.forEach((res, idx) => {
          const key = keysToFetch[idx].key;
          if (res && res.data && res.data.rating !== null && res.data.rating !== undefined) {
            next[key] = res.data.rating;
          }
        });
        if (Object.keys(next).length > 0) {
          setRatings(prev => ({ ...prev, ...next }));
        }
      } catch {
        // ignore
      }
    })();
  }, [interaction, ratings]);

  // Close documents dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showDocuments) {
        const target = event.target as Element;
        const dropdown = document.querySelector('[data-documents-dropdown]');
        const button = document.querySelector('[data-documents-button]');
        
        if (dropdown && !dropdown.contains(target) && button && !button.contains(target)) {
          setShowDocuments(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDocuments]);

  return (
    <>
      {loading && (
        <div className="fixed inset-0 bg-white dark:bg-gray-900 flex flex-col items-center justify-center z-50">
          <div className="w-64 mb-4">
            <div className="text-center text-gray-600 dark:text-gray-400 mb-2">
              Loading conversation...
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(loadingProgress + 20, 100)}%` }}
              ></div>
            </div>
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">
              {Math.min(loadingProgress + 20, 100)}%
            </div>
          </div>
        </div>
      )}
      <div className={`flex flex-col h-full min-h-0 bg-white dark:bg-gray-900 transition-all duration-300 ${showDebugPanel ? 'pr-96' : ''}`}>
        {/* Chat header */}
        <div className="pb-3 px-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {selectedConversationName}
            </h2>
            <div className="flex items-center space-x-2">
              {/* EDIT SCHEMA FEATURE: Edit Schema Button in Chat Interface Header */}
              {/* 
                This button provides easy access to the ER diagram editor from within
                the chatbot conversation interface. It allows users to modify the 
                semantic schema without leaving the chat context.
              */}
              {selectedChatbotId && (
                <button
                  onClick={() => {
                    const editSchemaPath = `/chatbot/${selectedChatbotId}/edit-schema`;
                    // Force navigation by adding a timestamp to force re-render
                    if (location.pathname === editSchemaPath) {
                      navigate(editSchemaPath, { replace: true, state: { refresh: Date.now() } });
                    } else {
                      navigate(editSchemaPath);
                    }
                  }}
                  className="flex items-center px-3 py-1.5 text-sm border border-blue-600 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Edit Database Schema"
                >
                  <Database className="w-4 h-4 mr-1" />
                  Edit Schema
                </button>
              )}
              
              {/* Interaction count display */}
              <div className="flex items-center space-x-1 text-sm">
                <MessageSquare className="w-4 h-4 text-gray-500" />
                <span className={`font-medium ${
                  interactionCount >= maxInteractions 
                    ? 'text-red-600' 
                    : interactionCount >= maxInteractions - 2 
                    ? 'text-orange-600' 
                    : 'text-gray-600'
                }`}>
                  {interactionCount}/{maxInteractions}
                </span>
              </div>
            </div>
          </div>
          
          {/* Warning messages */}
          {interactionCount >= maxInteractions && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                <div>
                  <p className="text-sm font-medium text-red-800">
                    Conversation limit reached
                  </p>
                  <p className="text-xs text-red-700">
                    This conversation has reached the maximum of {maxInteractions} interactions. Please start a new conversation to continue.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {interactionCount === maxInteractions - 1 && (
            <div className="mt-2 p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-orange-600" />
                <div>
                  <p className="text-sm font-medium text-orange-800">
                    Last interaction remaining
                  </p>
                  <p className="text-xs text-orange-700">
                    Only 1 interaction left. After this, you'll need to start a new conversation.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {interactionCount === maxInteractions - 2 && (
            <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
                <div>
                  <p className="text-sm font-medium text-yellow-800">
                    Almost at limit
                  </p>
                  <p className="text-xs text-yellow-700">
                    Only 2 interactions remaining in this conversation.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Messages area */}
        <div className={`flex-1 overflow-y-auto flex-col-reverse p-2 space-y-4 mt-2 transition-all duration-300 ${showDebugPanel ? 'mr-96' : ''}`} onScroll={handleScroll} ref={containerRef}>
          {conversationLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-lg font-medium mb-2">
                  Loading conversation...
                </p>
                <p className="max-w-md">
                  Please wait while we load the conversation data.
                </p>
              </div>
            </div>
          ) : displayedInteractions?.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <p className="text-lg font-medium mb-2">
                  Start a new conversation
                </p>
                <p className="max-w-md">
                  Type a message below to begin chatting with the AI assistant.
                </p>
              </div>
            </div>
          ) : (
            <>
              {displayedInteractions.map((msg: any) => {
                if (msg.is_system_message) {
                  // System message rendering
                  return (
                    <div key={msg.id || msg.interactionId || Math.random()} className="flex justify-center my-2">
                      <div className="bg-yellow-100 text-yellow-800 px-4 py-2 rounded text-xs font-semibold shadow">
                        {msg.request || msg.content}
                      </div>
                    </div>
                  );
                }

                // Skip rendering if this is a temporary message that's been replaced
                if (msg.id.startsWith('temp_') && interaction.some(m =>
                  !m.id.startsWith('temp_') &&
                  m.interactionId === msg.interactionId &&
                  m.role === msg.role
                )) {
                  return null;
                }

                // Original logic: parse content and render table if possible
                const parsedContent = parseJsonContent(msg.content);
                // Removed unused isJsonArray variable
                const isJsonObject = parsedContent && typeof parsedContent === 'object' && !Array.isArray(parsedContent);
                const isNewFormat = isJsonObject && parsedContent.data && parsedContent.metadata;
                const metaForIx = resultMeta[msg.interactionId];
                const userMsg = displayedInteractions.find(
                  (m) => m.interactionId === msg.interactionId && m.role === "user"
                );
                const userPrompt = userMsg?.content || "";

                return (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    } message-appear my-2`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        msg.role === "user"
                          ? "bg-[#6658dd] text-white"
                          : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700"
                      }`}
                    >
                      {msg.role === "user" ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        // Assistant message - handle JSON or text
                        <>
                          {(metaForIx && metaForIx.has_tabular_data) || isNewFormat ? (
                            <>
                              {/* Paged table UI */}
                              {(() => {
                                // Handle new format with pagination
                                if (isNewFormat && parsedContent.data) {
                                  const allRows = parsedContent.data;
                                  // Removed unused headers variable
                                  const totalRows = allRows.length;
                                  
                                  // Use UI pagination settings
                                  const uiSize = pageSizeUiByIx[msg.interactionId] ?? 500;
                                  const totalPages = Math.max(1, Math.ceil(totalRows / uiSize));
                                  const uiPageIndex = currentUiPageByIx[msg.interactionId] ?? 0;
                                  
                                  // Calculate which rows to show
                                  const startRow = uiPageIndex * uiSize;
                                  const endRow = Math.min(totalRows, startRow + uiSize);
                                  const rows = allRows.slice(startRow, endRow);
                                  
                                  return (
                                    <div>
                                      {renderTable(rows, totalRows)}
                                      {/* Pagination controls for new format */}
                                      <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
                                        <span className="text-gray-600">Rows per page:</span>
                                        <input
                                          className="w-16 px-1 py-0.5 border border-gray-200 rounded text-center"
                                          type="number"
                                          min={50}
                                          max={2000}
                                          step={50}
                                          value={uiSize}
                                          onChange={(e) => {
                                            const v = Math.max(1, Math.min(20000, parseInt(e.target.value || '1', 10)));
                                            setPageSizeUiByIx(prev => ({ ...prev, [msg.interactionId]: v }));
                                            setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: 0 }));
                                          }}
                                        />
                                        <button className="px-2 py-1 bg-gray-100 rounded disabled:opacity-50" disabled={uiPageIndex<=0} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: uiPageIndex-1 })); }}>Prev</button>
                                        <span>Page</span>
                                        <input
                                          className="w-14 px-1 py-0.5 border border-gray-200 rounded text-center"
                                          type="number"
                                          min={1}
                                          max={totalPages}
                                          value={pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1)}
                                          onChange={(e) => setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: e.target.value }))}
                                          onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                              e.preventDefault(); e.stopPropagation();
                                              const raw = pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1);
                                              let target = parseInt(raw, 10);
                                              if (isNaN(target)) target = uiPageIndex+1;
                                              target = Math.max(1, Math.min(totalPages, target));
                                              setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: String(target) }));
                                              setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: target - 1 }));
                                            }
                                          }}
                                        />
                                        <span>/ {totalPages}</span>
                                        <button className="px-2 py-1 bg-gray-100 rounded" onClick={(e) => {
                                          e.preventDefault(); e.stopPropagation();
                                          const raw = pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1);
                                          let target = parseInt(raw, 10);
                                          if (isNaN(target)) target = uiPageIndex+1;
                                          target = Math.max(1, Math.min(totalPages, target));
                                          setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: String(target) }));
                                          setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: target - 1 }));
                                        }}>Go</button>
                                        <button className="px-2 py-1 bg-gray-100 rounded disabled:opacity-50" disabled={uiPageIndex>=totalPages-1} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: uiPageIndex+1 })); }}>Next</button>
                                      </div>
                                      {/* Footer: rating (left) + actions (right) */}
                                      <div className="flex items-center justify-between mt-2">
                                        {/* Rate this response */}
                                        <div className="flex items-center gap-2 text-xs text-gray-600">
                                          <span className="font-medium">Rate this response:</span>
                                          {(() => {
                                            const ratingKey = `${msg.conversationId}_${msg.interactionId}`;
                                            const currentRating = ratings[ratingKey];
                                            const isLoading = ratingLoading[ratingKey];
                                            return (
                                              <div className="flex items-center gap-1">
                                                <button
                                                  className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 transform ${
                                                    currentRating === 1 
                                                      ? 'bg-green-100 text-green-800 border border-green-300 scale-105' 
                                                      : 'bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-700 hover:border-green-200'
                                                  } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                                                  onClick={() => !isLoading && handleRating(msg.conversationId, msg.interactionId, 1)}
                                                  disabled={isLoading}
                                                >
                                                  👍
                                                </button>
                                                <button
                                                  className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 transform ${
                                                    currentRating === -1 
                                                      ? 'bg-red-100 text-red-800 border border-red-300 scale-105' 
                                                      : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-700 hover:border-red-200'
                                                  } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                                                  onClick={() => !isLoading && handleRating(msg.conversationId, msg.interactionId, -1)}
                                                  disabled={isLoading}
                                                >
                                                  👎
                                                </button>
                                                {isLoading && <span className="text-xs text-gray-500">Saving...</span>}
                                              </div>
                                            );
                                          })()}
                                        </div>
                                        {/* Action buttons on right */}
                                        <div className="flex items-center gap-2">
                                          <button
                                            className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200 text-xs"
                                            title="Download CSV (current page)"
                                            onClick={() => handleDownloadCSV(rows, userPrompt)}
                                          >
                                            <Download size={16} /> Download
                                          </button>
                                          <button
                                            className="flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 text-xs"
                                            title="Show Business Analyst Insights (current page)"
                                            onClick={() => handleBAInsights(rows, userPrompt, msg.interactionId)}
                                          >
                                            <Lightbulb size={16} /> BA Insights
                                          </button>
                                          <button
                                            className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200 text-xs"
                                            title="Visualize Data (current page)"
                                            onClick={() => handleVisualize(rows, userPrompt)}
                                          >
                                            <BarChart3 size={16} /> Visualize
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                }

                                // Handle paginated format (existing logic)
                                const storedPageIndex = currentPageByIx[msg.interactionId] ?? 0; // index used with backend
                                const uiSize = pageSizeUiByIx[msg.interactionId] ?? (metaForIx?.page_size || 500); // user-selected size
                                const backendSize = metaForIx?.page_size || 500; // fixed storage size

                                // Map UI page to backend page using chunking
                                const total = metaForIx?.total_rows || 0;
                                const totalPages = Math.max(1, Math.ceil(total / uiSize));
                                const uiPageIndex = currentUiPageByIx[msg.interactionId] ?? Math.floor((storedPageIndex * backendSize) / uiSize);
                                // Removed unused showingStart and showingEnd variables

                                // Determine which backend pages are needed to assemble the desired UI page
                                const startRow = uiPageIndex * uiSize;
                                const endRow = Math.min(total, startRow + uiSize);
                                const startBackend = Math.floor(startRow / backendSize);
                                const endBackend = Math.floor((endRow - 1) / backendSize);

                                // Ensure required backend pages are loaded
                                for (let p = startBackend; p <= endBackend; p++) {
                                  if (metaForIx) { // Only load pages if we have metadata
                                    void ensureStoredPage(msg.interactionId, p);
                                  }
                                }

                                // Stitch rows from cached backend pages
                                const cache = rowsByIxPageRef.current[msg.interactionId] || {};
                                let stitched: any[] = [];
                                for (let p = startBackend; p <= endBackend; p++) {
                                  const chunk = cache[p];
                                  if (chunk) stitched = stitched.concat(chunk);
                                }
                                const offsetInFirst = startRow - startBackend * backendSize;
                                const rows = stitched.slice(offsetInFirst, offsetInFirst + (endRow - startRow));
                                // Removed unused cols variable
                                return (
                                  <div>
                                    {rows ? (
                                      renderTable(rows, total)
                                    ) : (
                                      <div className="text-xs text-gray-500">Loading page {uiPageIndex + 1}...</div>
                                    )}
                                    <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
                                      <span className="text-gray-600">Rows per page:</span>
                                      <input
                                        className="w-16 px-1 py-0.5 border border-gray-200 rounded text-center"
                                        type="number"
                                        min={50}
                                        max={2000}
                                        step={50}
                                        value={uiSize}
                                        onChange={(e) => {
                                          const v = Math.max(1, Math.min(20000, parseInt(e.target.value || '1', 10)));
                                          setPageSizeUiByIx(prev => ({ ...prev, [msg.interactionId]: v }));
                                          setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: 0 }));
                                        }}
                                      />
                                      <button className="px-2 py-1 bg-gray-100 rounded disabled:opacity-50" disabled={uiPageIndex<=0} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: uiPageIndex-1 })); }}>Prev</button>
                                      <span>Page</span>
                                      <input
                                        className="w-14 px-1 py-0.5 border border-gray-200 rounded text-center"
                                        type="number"
                                        min={1}
                                        max={totalPages}
                                        value={pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1)}
                                        onChange={(e) => setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: e.target.value }))}
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter') {
                                            e.preventDefault(); e.stopPropagation();
                                            const raw = pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1);
                                            let target = parseInt(raw, 10);
                                            if (isNaN(target)) target = uiPageIndex+1;
                                            target = Math.max(1, Math.min(totalPages, target));
                                            setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: String(target) }));
                                            setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: target - 1 }));
                                          }
                                        }}
                                      />
                                      <span>/ {totalPages}</span>
                                      <button className="px-2 py-1 bg-gray-100 rounded" onClick={(e) => {
                                        e.preventDefault(); e.stopPropagation();
                                        const raw = pageInputByIx[msg.interactionId] ?? String(uiPageIndex+1);
                                        let target = parseInt(raw, 10);
                                        if (isNaN(target)) target = uiPageIndex+1;
                                        target = Math.max(1, Math.min(totalPages, target));
                                        setPageInputByIx(prev => ({ ...prev, [msg.interactionId]: String(target) }));
                                        setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: target - 1 }));
                                      }}>Go</button>
                                      <button className="px-2 py-1 bg-gray-100 rounded disabled:opacity-50" disabled={uiPageIndex>=totalPages-1} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setCurrentUiPageByIx(prev => ({ ...prev, [msg.interactionId]: uiPageIndex+1 })); }}>Next</button>
                                    </div>
                                    {/* Footer: rating (left) + actions (right) */}
                                    {rows && rows.length > 0 && (
                                      <div className="flex items-center justify-between mt-2">
                                        {/* Rate this response */}
                                        <div className="flex items-center gap-2 text-xs text-gray-600">
                                          <span className="font-medium">Rate this response:</span>
                                  {(() => {
                                    const ratingKey = `${msg.conversationId}_${msg.interactionId}`;
                                    const currentRating = ratings[ratingKey];
                                    const isLoading = ratingLoading[ratingKey];
                                    return (
                                      <div className="flex items-center gap-1">
                                        <button
                                          className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 transform ${
                                            currentRating === 1 
                                              ? 'bg-green-100 text-green-800 border border-green-300 scale-105' 
                                              : 'bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-700 hover:border-green-200'
                                          } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                                          onClick={() => !isLoading && handleRating(msg.conversationId, msg.interactionId, 1)}
                                          disabled={isLoading}
                                        >
                                          👍
                                        </button>
                                        <button
                                          className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 transform ${
                                                    currentRating === -1 
                                              ? 'bg-red-100 text-red-800 border border-red-300 scale-105' 
                                              : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-700 hover:border-red-200'
                                          } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                                                  onClick={() => !isLoading && handleRating(msg.conversationId, msg.interactionId, -1)}
                                          disabled={isLoading}
                                        >
                                          👎
                                        </button>
                                        {isLoading && <span className="text-xs text-gray-500">Saving...</span>}
                                      </div>
                                    );
                                  })()}
                                </div>
                                        {/* Action buttons on right */}
                                <div className="flex items-center gap-2">
                                  <button
                                    className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200 text-xs"
                                          title="Download CSV (current page)"
                                          onClick={() => handleDownloadCSV(rows, userPrompt)}
                                  >
                                    <Download size={16} /> Download
                                  </button>
                                  <button
                                    className="flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 text-xs"
                                          title="Show Business Analyst Insights (current page)"
                                          onClick={() => handleBAInsights(rows, userPrompt, msg.interactionId)}
                                  >
                                    <Lightbulb size={16} /> BA Insights
                                  </button>
                                  <button
                                    className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200 text-xs"
                                          title="Visualize Data (current page)"
                                          onClick={() => handleVisualize(rows, userPrompt)}
                                  >
                                    <BarChart3 size={16} /> Visualize
                                  </button>
                                </div>
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })()}
                            </>
                          ) : (
                            <>
                              {/* Show text content for non-tabular responses */}
                              <div className="whitespace-pre-wrap break-words text-sm text-gray-700">{msg.content}</div>
                            </>
                          )}
                        </>
                      )}
                    </div>
                    {msg.role === "user" && (
                      <button
                        onClick={() => handleDebugClick(msg?.conversationId, msg.interactionId)}
                        className="text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 ml-2"
                        title="Debug Info"
                      >
                        <Bug size={14} />
                      </button>
                    )}
                  </div>
                );
              })}
            </>
          )}

          {isTyping && interaction.some(msg => msg.isLoading) && (
            <div className="flex justify-start message-appear">
              <div className="bg-white dark:bg-gray-800 rounded-lg px-4 py-2 border border-gray-200 dark:border-gray-700">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Voice controls */}
        {isVoiceEnabled && <VoiceControls
          onFinalVoiceMessage={(msg) => {
            setInputMessage(msg);
            handleSendMessage(msg);
          }}
        />}

        {/* Enhanced clarification bar for human-in-the-loop */}
        {showClarificationBar && clarificationSuggestions.length > 0 && (
          <div className="px-4 pt-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {isInClarificationMode ? "🤖 I need clarification:" : "💡 Quick suggestions:"}
                </div>
                {clarificationContext && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Step {clarificationContext.step} of {clarificationContext.totalSteps}
                  </div>
                )}
              </div>
              <button
                className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => setShowClarificationBar(false)}
                title="Hide suggestions"
              >
                ✕
              </button>
            </div>
            
            {/* Progress indicator for clarification mode */}
            {isInClarificationMode && clarificationContext && (
              <div className="mb-3">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div 
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${(clarificationContext.step / clarificationContext.totalSteps) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
            
            <div className="flex flex-wrap gap-2">
              {clarificationSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handlePickSuggestion(s)}
                  className={`max-w-full truncate px-4 py-2 text-sm rounded-lg border-2 transition-all duration-200 transform hover:scale-105 ${
                    isInClarificationMode 
                      ? 'border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 hover:bg-blue-100 dark:hover:bg-blue-900/40 shadow-md hover:shadow-lg' 
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-400'
                  }`}
                  title={`Click to use: ${s}`}
                >
                  {s}
                </button>
              ))}
            </div>
            
            {/* Additional context for clarification mode */}
            {isInClarificationMode && (
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                💡 Please provide your answer so I can generate the most accurate query for you.
              </div>
            )}
          </div>
        )}

        {/* Input area */}
        <div className="dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
          <div className="relative p-4">
            <div className="flex items-end bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all px-3 py-1">
              {/* Textarea */}
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  conversationLoading 
                    ? "Loading conversation..." 
                    : interactionLimitReached 
                    ? "Conversation limit reached. Start a new conversation to continue."
                    : "Type your message..."
                }
                className="flex-1 border-0 bg-transparent py-3 px-2 focus:outline-none focus:ring-0 dark:text-white resize-none min-h-[48px] max-h-[120px] placeholder:align-middle"
                rows={1}
                style={{ lineHeight: '1.5rem' }}
                disabled={conversationLoading || interactionLimitReached}
              />

              {/* Document Upload Button */}
              <div className="relative flex items-center">
                <input
                  type="file"
                  id="document-upload"
                  className="hidden"
                  accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  multiple
                  onChange={handleDocumentUpload}
                  disabled={interactionLimitReached}
                />
                <label
                  htmlFor="document-upload"
                  className={`cursor-pointer p-3 mx-1 rounded-xl transition-all text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300 flex items-center ${
                    interactionLimitReached ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                  title={interactionLimitReached ? "Upload disabled - conversation limit reached" : "Upload documents (PDF, DOC, DOCX)"}
                >
                  <Paperclip size={20} />
                </label>
                
                {/* Documents Icon */}
                {uploadedDocuments.length > 0 && (
                  <div className="relative">
                    <button
                      onClick={() => setShowDocuments(!showDocuments)}
                      className="p-2 rounded-lg transition-all text-[#6658dd] dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 flex items-center"
                      title={`${uploadedDocuments.length} document${uploadedDocuments.length > 1 ? 's' : ''} attached`}
                      data-documents-button
                    >
                      <FileText size={16} />
                      <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                        {uploadedDocuments.length}
                      </span>
                    </button>
                    
                    {/* Documents Dropdown */}
                    {showDocuments && (
                      <div 
                        className="absolute bottom-full right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 w-64 z-50"
                        data-documents-dropdown
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Attached Documents</h4>
                          <button
                            onClick={() => setShowDocuments(false)}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          >
                            <X size={14} />
                          </button>
                        </div>
                        <div className="space-y-2 max-h-32 overflow-y-auto">
                          {uploadedDocuments.map((doc, index) => (
                            <div key={index} className="flex items-center gap-2 bg-gray-50 dark:bg-gray-700 rounded-md px-2 py-1">
                              {getFileIcon(doc.name)}
                              <span className="text-xs text-gray-700 dark:text-gray-300 truncate flex-1" title={doc.name}>
                                {doc.name}
                              </span>
                              <button
                                onClick={() => removeDocument(index)}
                                className="text-gray-400 hover:text-red-500 transition-colors"
                                title="Remove document"
                              >
                                <X size={12} />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Mic Button */}
              <button
                onClick={toggleVoice}
                type="button"
                disabled={interactionLimitReached}
                className={`p-3 mx-1 rounded-xl transition-all ${
                  interactionLimitReached
                    ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                    : isVoiceEnabled
                    ? 'text-[#6658dd] dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
                title={
                  interactionLimitReached 
                    ? "Voice disabled - conversation limit reached"
                    : isVoiceEnabled 
                    ? "Disable voice" 
                    : "Enable voice"
                }
              >
                {isVoiceEnabled ? <Mic size={20} /> : <MicOff size={20} />}
              </button>

              {/* Send Button */}
              <button
                onClick={() => handleSendMessage()}
                type="button"
                disabled={!inputMessage.trim() || conversationLoading || interactionLimitReached}
                className={`p-3 mb-1 rounded-xl transition-all ${
                  inputMessage.trim() && !conversationLoading && !interactionLimitReached
                    ? 'bg-[#6658dd] text-white shadow-md hover:shadow-lg transform hover:scale-105'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                }`}
                title={
                  conversationLoading 
                    ? "Loading conversation..." 
                    : interactionLimitReached 
                    ? "Conversation limit reached - start a new conversation"
                    : "Send message"
                }
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Debug Panel */}
        <DebugPanel steps={debugSteps} isVisible={showDebugPanel} />
        

        {/* Processing Status Indicator */}
        {(() => {
          const isProcessingActive = pollingForPending || (
            processingStatus && processingStatus.current_step !== 'completed' && processingStatus.current_step !== 'error'
          );
          return (
            <ProcessingStatusIndicator 
              status={processingStatus}
              isVisible={Boolean(isProcessingActive)}
            />
          );
        })()}

        {/* Error Display */}
        {/* Timeout/connection warning hidden per request */}

        {/* BA Summary Modal */}
        <BAInsightsModal
          isOpen={baModalOpen}
          onClose={() => setBaModalOpen(false)}
          summary={baModalSummary}
          isLoading={baLoading}
          userQuery={baUserQuery}
          onRegenerate={handleRegenerateBAInsights}
        />

        {/* Visualization Modal */}
        <VisualizationModal
          isOpen={visualizationModalOpen}
          onClose={() => setVisualizationModalOpen(false)}
          chartConfig={chartConfig}
          isLoading={chartLoading}
          userQuery={chartUserQuery}
          onRegenerate={handleRegenerateVisualization}
        />

        {/* Human Approval Dialog */}
        <HumanApprovalDialog
          isOpen={showApprovalDialog}
          onClose={handleApprovalReject}
          approvalRequest={approvalRequest}
          onApprove={handleHumanApprovalResponse}
          isLoading={approvalLoading}
        />
      </div>
    </>
  );
};

export default ChatInterface;




