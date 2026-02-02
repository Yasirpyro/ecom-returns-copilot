import { useState, useEffect, useRef } from "react";
import { useTypingAnimation } from "@/hooks/useTypingAnimation";
import { startChat, sendMessage, ChatResponse, getCasePublic, CasePublicStatus } from "@/lib/api";
import { ChatBubble } from "@/components/chat/ChatBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { PhotoUpload } from "@/components/chat/PhotoUpload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, MessageCircle } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

const SESSION_KEY = 'copilot_session_id';
const getActiveCaseKey = (sessionId: string) => `activeCaseId:${sessionId}`;
const getFinalAppendedKey = (sessionId: string) => `finalAppended:${sessionId}`;

// Normalize order ID to ORD-xxxxx format
function normalizeOrderId(orderId: string): string {
  const raw = (orderId || "").trim().toUpperCase().replace(/\s/g, "");
  if (!raw) return orderId;
  if (raw.startsWith("ORD-")) return raw;
  if (raw.startsWith("ORD") && /^\d+$/.test(raw.slice(3))) return `ORD-${raw.slice(3)}`;
  if (/^\d+$/.test(raw)) return `ORD-${raw}`;
  return orderId;
}

function WelcomeText() {
  const { displayedText, isComplete } = useTypingAnimation("Hey, I'm EcomBot", 70, 300);
  
  return (
    <div className="text-center space-y-2">
      <h2 className="font-display text-xl sm:text-2xl md:text-3xl text-foreground">
        {displayedText.includes("EcomBot") ? (
          <>
            {displayedText.replace("EcomBot", "")}
            <span className="text-primary font-semibold">EcomBot</span>
          </>
        ) : (
          <>
            {displayedText}
            <span className="inline-block w-0.5 h-6 sm:h-7 md:h-8 bg-primary animate-pulse ml-0.5 align-middle" />
          </>
        )}
      </h2>
      {isComplete && (
        <p className="text-sm sm:text-base text-muted-foreground max-w-md animate-fade-in">
          Your friendly returns & warranty assistant. How can I help you today?
        </p>
      )}
    </div>
  );
}

export default function CustomerChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [orderId, setOrderId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [caseStatus, setCaseStatus] = useState<string | null>(null);
  const [pendingStatusText, setPendingStatusText] = useState("Working on it...");
  const [finalMessageAppended, setFinalMessageAppended] = useState(false);
  const appendedContentRef = useRef<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      const existingSessionId = localStorage.getItem(SESSION_KEY);
      
      if (existingSessionId) {
        setSessionId(existingSessionId);
        setIsInitializing(false);
        const storedCaseId = localStorage.getItem(getActiveCaseKey(existingSessionId));
        if (storedCaseId) {
          setCaseId(storedCaseId);
        }
        // Add welcome back message
        setMessages([{
          id: 'welcome',
          content: "Welcome back! How can I help you with your return or warranty request today?",
          isUser: false,
          timestamp: new Date(),
        }]);
      } else {
        try {
          const response = await startChat();
          localStorage.setItem(SESSION_KEY, response.session_id);
          setSessionId(response.session_id);
          // Add initial welcome message
          setMessages([{
            id: 'welcome',
            content: "Hello! I'm your Returns & Warranty Assistant. I can help you with returns, exchanges, and warranty claims. How can I assist you today?",
            isUser: false,
            timestamp: new Date(),
          }]);
        } catch (error) {
          toast({
            title: "Connection failed",
            description: "Unable to start chat session. Please refresh the page.",
            variant: "destructive",
          });
        }
        setIsInitializing(false);
      }
    };

    initSession();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    setFinalMessageAppended(false);
  }, [caseId]);

  // Pending status text when sending
  useEffect(() => {
    if (!isLoading) return;
    setPendingStatusText("Working on it...");
    const timer = setTimeout(() => {
      setPendingStatusText("Still working—thanks for your patience.");
    }, 2500);
    return () => clearTimeout(timer);
  }, [isLoading]);

  const { data: caseStatusData } = useQuery<CasePublicStatus>({
    queryKey: ["case-status", sessionId, caseId],
    queryFn: () => getCasePublic(caseId as string),
    enabled: !!caseId,
    refetchInterval: (query) => {
      const data = query.state.data as CasePublicStatus | undefined;
      if (!data) return 3000;
      if (data.status === "closed" || data.final_customer_reply) return false;
      return 3000;
    },
  });

  useEffect(() => {
    if (!caseStatusData) return;

    if (caseStatusData.status) {
      setCaseStatus(caseStatusData.status);
    }

    if (caseStatusData.final_customer_reply && !finalMessageAppended) {
      const content = caseStatusData.final_customer_reply;
      
      // Strong deduplication: check if this content was already appended
      if (appendedContentRef.current.has(content)) {
        return;
      }

      const finalMessage: Message = {
        id: `final-${caseId}-${Date.now()}`,
        content,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => {
        // Additional check: ensure we don't duplicate by content
        const alreadyExists = prev.some(m => !m.isUser && m.content === content);
        if (alreadyExists) {
          return prev;
        }
        return [...prev, finalMessage];
      });

      appendedContentRef.current.add(content);

      setFinalMessageAppended(true);
      if (sessionId) {
        localStorage.removeItem(getActiveCaseKey(sessionId));
      }
      setCaseId(null);
      setCaseStatus("closed");
      return;
    }

    if (caseStatusData.status === "closed" && !caseStatusData.final_customer_reply) {
      if (sessionId) {
        localStorage.removeItem(getActiveCaseKey(sessionId));
      }
      setCaseId(null);
      setCaseStatus("closed");
    }
  }, [caseStatusData, finalMessageAppended, sessionId]);

  const handleSend = async (message: string, orderIdValue: string, wantsStoreCredit: boolean) => {
    if (!sessionId) return;
    const hasActiveCase = !!caseId && caseStatus !== 'closed';
    if (hasActiveCase) return;

    // Normalize order ID before sending
    const normalizedOrderId = orderIdValue ? normalizeOrderId(orderIdValue) : undefined;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendMessage(sessionId, {
        message,
        order_id: normalizedOrderId,
        wants_store_credit: wantsStoreCredit,
      });

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.assistant_message,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Update case info
      if (response.case_id) {
        setCaseId(response.case_id);
        localStorage.setItem(getActiveCaseKey(sessionId), response.case_id);
        setFinalMessageAppended(false);
      }
      if (response.status) {
        setCaseStatus(response.status);
      }
    } catch (error) {
      toast({
        title: "We couldn’t generate a response. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePhotoUpload = () => {
    // Refresh status after photo upload
    setCaseStatus('ready_for_human_review');
  };

  const startNewSession = async () => {
    localStorage.removeItem(SESSION_KEY);
    if (sessionId) {
      localStorage.removeItem(getActiveCaseKey(sessionId));
    }
    setMessages([]);
    setCaseId(null);
    setCaseStatus(null);
    setFinalMessageAppended(false);
    appendedContentRef.current.clear();
    setIsInitializing(true);
    
    try {
      const response = await startChat();
      localStorage.setItem(SESSION_KEY, response.session_id);
      setSessionId(response.session_id);
      setMessages([{
        id: 'welcome',
        content: "Hello! I'm your Returns & Warranty Assistant. I can help you with returns, exchanges, and warranty claims. How can I assist you today?",
        isUser: false,
        timestamp: new Date(),
      }]);
    } catch (error) {
      toast({
        title: "Connection failed",
        description: "Unable to start new session",
        variant: "destructive",
      });
    }
    setIsInitializing(false);
  };

  if (isInitializing) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="mt-2 text-muted-foreground">Starting chat session...</p>
        </div>
      </div>
    );
  }

  const isCaseActive = !!caseId && caseStatus !== 'closed';
  const bannerText = caseStatus === 'needs_customer_photos'
    ? "Please upload photos to continue."
    : "Your case is under review. You’ll receive an update here.";

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card px-3 sm:px-4 py-3 flex items-center justify-between flex-shrink-0 gap-2">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <MessageCircle className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="font-semibold text-sm sm:text-base truncate">Returns & Warranty</h1>
            <p className="text-xs text-muted-foreground hidden sm:block">We're here to help</p>
          </div>
        </div>
        <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
          <Button variant="ghost" size="sm" onClick={startNewSession} className="text-xs sm:text-sm px-2 sm:px-3">
            New
          </Button>
        </div>
      </header>

      {/* Chatbot illustration - fixed, no scroll */}
      {messages.length <= 1 && (
        <div className="flex-1 flex flex-col justify-center items-center px-4 overflow-hidden gap-4">
          <svg
            viewBox="0 0 120 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-48 h-48 sm:w-56 sm:h-56 md:w-64 md:h-64 lg:w-72 lg:h-72 text-primary"
          >
            {/* Robot head */}
            <rect x="25" y="30" width="70" height="55" rx="12" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="3"/>
            {/* Antenna */}
            <line x1="60" y1="30" x2="60" y2="18" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            <circle cx="60" cy="14" r="5" fill="currentColor"/>
            {/* Eyes */}
            <circle cx="42" cy="52" r="8" fill="currentColor"/>
            <circle cx="78" cy="52" r="8" fill="currentColor"/>
            <circle cx="44" cy="50" r="3" fill="white"/>
            <circle cx="80" cy="50" r="3" fill="white"/>
            {/* Mouth */}
            <rect x="40" y="68" width="40" height="8" rx="4" fill="currentColor" fillOpacity="0.3"/>
            <rect x="44" y="70" width="6" height="4" rx="1" fill="currentColor"/>
            <rect x="54" y="70" width="6" height="4" rx="1" fill="currentColor"/>
            <rect x="64" y="70" width="6" height="4" rx="1" fill="currentColor"/>
            <rect x="74" y="70" width="6" height="4" rx="1" fill="currentColor"/>
            {/* Body */}
            <rect x="35" y="88" width="50" height="20" rx="6" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="2"/>
            {/* Chat bubbles */}
            <circle cx="18" cy="45" r="6" fill="currentColor" fillOpacity="0.4"/>
            <circle cx="10" cy="55" r="4" fill="currentColor" fillOpacity="0.3"/>
            <circle cx="102" cy="45" r="6" fill="currentColor" fillOpacity="0.4"/>
            <circle cx="110" cy="55" r="4" fill="currentColor" fillOpacity="0.3"/>
          </svg>
          <WelcomeText />
        </div>
      )}

      {/* Chat area - only shows when there are messages */}
      {messages.length > 1 && (
        <div className="flex-1 overflow-y-auto p-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((message) => (
            <div key={message.id}>
              <ChatBubble
                message={message.content}
                isUser={message.isUser}
                timestamp={message.timestamp}
              />
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">{pendingStatusText}</span>
                </div>
              </div>
            </div>
          )}

          {/* Photo upload card */}
          {caseStatus === 'needs_customer_photos' && caseId && (
            <PhotoUpload 
              caseId={caseId} 
              onUploadSuccess={handlePhotoUpload}
            />
          )}

          {/* Case status */}
          {caseId && (
            <Card className="p-3 bg-muted/50">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Case ID: {caseId.slice(0, 8)}...</span>
                {caseStatus && (
                  <Badge variant={
                    caseStatus === 'closed' ? 'default' :
                    caseStatus === 'ready_for_human_review' ? 'secondary' :
                    'outline'
                  }>
                    {caseStatus.replace(/_/g, ' ')}
                  </Badge>
                )}
              </div>
            </Card>
          )}

          <div ref={scrollRef} />
          </div>
        </div>
      )}

      {/* Input */}
      <div className="max-w-2xl mx-auto w-full">
        {isCaseActive && (
          <div className="px-3 sm:px-4 pt-3">
            <div className="rounded-md bg-muted/60 text-muted-foreground text-xs sm:text-sm px-3 py-2">
              {bannerText}
            </div>
          </div>
        )}
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          isDisabled={isCaseActive}
          orderId={orderId}
          onOrderIdChange={setOrderId}
        />
      </div>
    </div>
  );
}
