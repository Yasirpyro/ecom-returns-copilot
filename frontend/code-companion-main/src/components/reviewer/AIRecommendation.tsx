import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { Brain, ChevronDown, FileText } from "lucide-react";
import { PolicyCitation } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AIRecommendationProps {
  aiDecision: Record<string, unknown>;
  policyCitations: PolicyCitation[];
}

export function AIRecommendation({ aiDecision, policyCitations }: AIRecommendationProps) {
  const [expandedCitations, setExpandedCitations] = useState<Set<number>>(new Set());

  const toggleCitation = (index: number) => {
    setExpandedCitations(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  // Extract key decision fields for display
  const decision = aiDecision.decision || aiDecision.recommendation || 'N/A';
  const confidence = aiDecision.confidence;
  const reasoning = aiDecision.reasoning || aiDecision.explanation;

  return (
    <Card className="border-purple-200 dark:border-purple-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-600" />
          AI Recommendation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Decision summary */}
        <div className="p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">Decision:</span>
            <Badge 
              variant={
                String(decision).toLowerCase().includes('approv') ? 'default' :
                String(decision).toLowerCase().includes('deny') || String(decision).toLowerCase().includes('denied') ? 'destructive' :
                'secondary'
              }
            >
              {String(decision)}
            </Badge>
            {confidence && (
              <Badge variant="outline" className="text-xs">
                {typeof confidence === 'number' ? `${(confidence * 100).toFixed(0)}%` : String(confidence)} confidence
              </Badge>
            )}
          </div>
          {reasoning && (
            <p className="text-sm text-muted-foreground">{String(reasoning)}</p>
          )}
        </div>

        {/* Full JSON viewer */}
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
            <ChevronDown className="h-4 w-4" />
            View full AI response
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="mt-2 p-3 bg-muted rounded-lg text-xs overflow-x-auto">
              {JSON.stringify(aiDecision, null, 2)}
            </pre>
          </CollapsibleContent>
        </Collapsible>

        {/* Policy citations */}
        {policyCitations && policyCitations.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Policy Citations ({policyCitations.length})
            </h4>
            <div className="space-y-2">
              {policyCitations.map((citation, index) => (
                <Collapsible 
                  key={index}
                  open={expandedCitations.has(index)}
                  onOpenChange={() => toggleCitation(index)}
                >
                  <CollapsibleTrigger className="w-full">
                    <div className={cn(
                      "flex items-center justify-between p-2 rounded border text-left text-sm hover:bg-muted/50 transition-colors",
                      expandedCitations.has(index) && "bg-muted/50"
                    )}>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs font-mono">
                          {citation.policy_id}
                        </Badge>
                        <span className="text-muted-foreground">{citation.source}</span>
                      </div>
                      <ChevronDown className={cn(
                        "h-4 w-4 transition-transform",
                        expandedCitations.has(index) && "rotate-180"
                      )} />
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="mt-1 p-3 bg-muted/30 rounded-b border-x border-b text-sm">
                      <p className="italic text-muted-foreground">"{citation.excerpt}"</p>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
