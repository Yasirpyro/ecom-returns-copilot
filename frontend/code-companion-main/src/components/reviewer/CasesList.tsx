import { useEffect, useState, useCallback } from "react";
import { getCases, Case } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Inbox, Loader2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface CasesListProps {
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
}

export function CasesList({ selectedCaseId, onSelectCase }: CasesListProps) {
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchCases = useCallback(async () => {
    try {
      const response = await getCases('ready_for_human_review');
      setCases(response.data || []);
      setLastRefresh(new Date());
    } catch (error) {
      toast({
        title: "Failed to fetch cases",
        description: "Please try refreshing",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
    
    // Auto-refresh every 15 seconds
    const interval = setInterval(fetchCases, 15000);
    return () => clearInterval(interval);
  }, [fetchCases]);

  const handleRefresh = () => {
    setIsLoading(true);
    fetchCases();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + 
           ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Inbox className="h-5 w-5" />
            Review Inbox
            {cases.length > 0 && (
              <Badge variant="secondary" className="ml-2">
                {cases.length}
              </Badge>
            )}
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Last updated: {lastRefresh.toLocaleTimeString()}
        </p>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        {isLoading && cases.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : cases.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
            <Inbox className="h-10 w-10 mb-2 opacity-50" />
            <p className="text-sm">No cases pending review</p>
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className="space-y-1 p-3 pt-0">
              {cases.map((caseItem) => (
                <button
                  key={caseItem.case_id}
                  onClick={() => onSelectCase(caseItem.case_id)}
                  className={cn(
                    "w-full text-left p-3 rounded-lg border transition-colors",
                    selectedCaseId === caseItem.case_id
                      ? "bg-primary/10 border-primary"
                      : "hover:bg-muted border-transparent"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-sm truncate">
                        {caseItem.order_id}
                      </p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {caseItem.reason || 'No reason specified'}
                      </p>
                    </div>
                    {caseItem.photos_required && (
                      <Badge variant="outline" className="text-xs flex-shrink-0">
                        📷
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatDate(caseItem.created_at)}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
