import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string, orderId: string, wantsStoreCredit: boolean) => void;
  isLoading: boolean;
  isDisabled?: boolean;
  orderId: string;
  onOrderIdChange: (orderId: string) => void;
}

// Normalize order ID to ORD-xxxxx format on blur
function normalizeOrderId(orderId: string): string {
  const raw = (orderId || "").trim().toUpperCase().replace(/\s/g, "");
  if (!raw) return orderId;
  if (raw.startsWith("ORD-")) return raw;
  if (raw.startsWith("ORD") && /^\d+$/.test(raw.slice(3))) return `ORD-${raw.slice(3)}`;
  if (/^\d+$/.test(raw)) return `ORD-${raw}`;
  return orderId;
}

export function ChatInput({ onSend, isLoading, isDisabled = false, orderId, onOrderIdChange }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [wantsStoreCredit, setWantsStoreCredit] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isDisabled) return;
    if (!message.trim()) return;
    onSend(message.trim(), orderId, wantsStoreCredit);
    setMessage("");
  };

  return (
    <form onSubmit={handleSubmit} className="border-t bg-background p-3 sm:p-4 space-y-3">
      <div className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe your return or warranty issue..."
            className="min-h-[50px] sm:min-h-[60px] resize-none text-sm sm:text-base"
            disabled={isLoading || isDisabled}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
        </div>
        <Button type="submit" disabled={isLoading || isDisabled || !message.trim()} size="sm" className="h-auto px-3 sm:hidden">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
      
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="order-id" className="text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
              Order ID:
            </Label>
            <Input
              id="order-id"
              value={orderId}
              onChange={(e) => onOrderIdChange(e.target.value)}
              onBlur={(e) => {
                const normalized = normalizeOrderId(e.target.value);
                if (normalized !== e.target.value) {
                  onOrderIdChange(normalized);
                }
              }}
              placeholder="ORD-10003"
              className="w-24 sm:w-32 h-8 text-xs sm:text-sm"
              disabled={isLoading || isDisabled}
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Switch
              id="store-credit"
              checked={wantsStoreCredit}
              onCheckedChange={setWantsStoreCredit}
              disabled={isLoading || isDisabled}
            />
            <Label htmlFor="store-credit" className="text-xs sm:text-sm text-muted-foreground cursor-pointer">
              Store credit
            </Label>
          </div>
        </div>
        
        <Button type="submit" disabled={isLoading || isDisabled || !message.trim()} size="sm" className="hidden sm:flex">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="ml-2">Send</span>
        </Button>
      </div>
      
      {!orderId && (
        <p className="text-xs text-amber-600">
          💡 Tip: Providing your Order ID helps us assist you faster
        </p>
      )}
    </form>
  );
}
