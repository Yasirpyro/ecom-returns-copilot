import { useEffect, useState, useCallback } from "react";
import { getCase, Case } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { OrderFacts } from "./OrderFacts";
import { PhotoGallery } from "./PhotoGallery";
import { AIRecommendation } from "./AIRecommendation";
import { DecisionControls } from "./DecisionControls";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageSquare, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";

interface CaseDetailProps {
  caseId: string;
  onBack?: () => void;
  onCaseClosed?: () => void;
}

export function CaseDetail({ caseId, onBack, onCaseClosed }: CaseDetailProps) {
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCase = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getCase(caseId);
      setCaseData(data);
    } catch (error) {
      toast({
        title: "Failed to load case",
        description: "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
  }, [fetchCase]);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Failed to load case details
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          {onBack && (
            <Button variant="ghost" size="icon" onClick={onBack} className="md:hidden">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h2 className="text-lg font-semibold">Case: {caseData.order_id}</h2>
            <p className="text-sm text-muted-foreground">
              {caseData.reason} • Created {new Date(caseData.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Order facts */}
        {caseData.order_facts_json && (
          <OrderFacts orderFacts={caseData.order_facts_json} />
        )}

        {/* Customer message */}
        {caseData.customer_message && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Customer Message
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm bg-muted p-3 rounded-lg">{caseData.customer_message}</p>
            </CardContent>
          </Card>
        )}

        {/* Photos */}
        <PhotoGallery photos={caseData.photo_urls_json || []} />

        {/* AI Recommendation */}
        {caseData.ai_decision_json && (
          <AIRecommendation 
            aiDecision={caseData.ai_decision_json} 
            policyCitations={caseData.policy_citations_json || []}
          />
        )}

        {/* Human decision */}
        <DecisionControls
          caseId={caseData.case_id}
          currentDecision={caseData.human_decision}
          currentNotes={caseData.human_notes}
          onDecisionSubmitted={fetchCase}
          onCaseClosed={onCaseClosed}
        />
      </div>
    </ScrollArea>
  );
}
