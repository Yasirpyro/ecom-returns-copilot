import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CheckCircle, XCircle, HelpCircle, Loader2, Copy, Check, Gavel, Send } from "lucide-react";
import { submitDecision, finalizeCase, FinalizeResponse } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface DecisionControlsProps {
  caseId: string;
  currentDecision: string | null;
  currentNotes: string | null;
  onDecisionSubmitted: () => void;
}

export function DecisionControls({ 
  caseId, 
  currentDecision, 
  currentNotes,
  onDecisionSubmitted 
}: DecisionControlsProps) {
  const [notes, setNotes] = useState(currentNotes || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [finalizeResult, setFinalizeResult] = useState<FinalizeResponse | null>(null);
  const [editableReply, setEditableReply] = useState("");
  const [copiedReply, setCopiedReply] = useState(false);
  const [copiedActions, setCopiedActions] = useState(false);

  const handleDecision = async (decision: 'approved' | 'denied' | 'more_info_requested') => {
    setIsSubmitting(true);
    try {
      await submitDecision(caseId, decision, notes || undefined);
      toast({
        title: "Decision submitted",
        description: `Case marked as ${decision.replace('_', ' ')}`,
      });
      onDecisionSubmitted();
    } catch (error) {
      toast({
        title: "Failed to submit decision",
        description: "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinalize = async () => {
    setIsFinalizing(true);
    try {
      const result = await finalizeCase(caseId);
      setFinalizeResult(result);
      setEditableReply(result.customer_reply);
      toast({
        title: "Case finalized",
        description: "Customer reply generated successfully",
      });
      onDecisionSubmitted();
    } catch (error) {
      toast({
        title: "Failed to finalize case",
        description: "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsFinalizing(false);
    }
  };

  const copyToClipboard = async (text: string, type: 'reply' | 'actions') => {
    await navigator.clipboard.writeText(text);
    if (type === 'reply') {
      setCopiedReply(true);
      setTimeout(() => setCopiedReply(false), 2000);
    } else {
      setCopiedActions(true);
      setTimeout(() => setCopiedActions(false), 2000);
    }
    toast({ title: "Copied to clipboard" });
  };

  const hasDecision = !!currentDecision;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Gavel className="h-4 w-4" />
          Human Decision
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Decision buttons */}
        {!hasDecision && (
          <>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any notes about your decision..."
                className="min-h-[80px]"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex gap-2 flex-wrap">
              <Button
                onClick={() => handleDecision('approved')}
                disabled={isSubmitting}
                className="bg-green-600 hover:bg-green-700"
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                Approve
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleDecision('denied')}
                disabled={isSubmitting}
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <XCircle className="h-4 w-4 mr-2" />}
                Deny
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDecision('more_info_requested')}
                disabled={isSubmitting}
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <HelpCircle className="h-4 w-4 mr-2" />}
                Request More Info
              </Button>
            </div>
          </>
        )}

        {/* Current decision display */}
        {hasDecision && !finalizeResult && (
          <div className="space-y-4">
            <div className="p-3 bg-muted rounded-lg">
              <p className="text-sm">
                <span className="font-medium">Decision:</span>{" "}
                <span className={
                  currentDecision === 'approved' ? 'text-green-600' :
                  currentDecision === 'denied' ? 'text-red-600' :
                  'text-amber-600'
                }>
                  {currentDecision?.replace('_', ' ')}
                </span>
              </p>
              {currentNotes && (
                <p className="text-sm text-muted-foreground mt-1">
                  <span className="font-medium">Notes:</span> {currentNotes}
                </p>
              )}
            </div>

            <Button
              onClick={handleFinalize}
              disabled={isFinalizing}
              className="w-full"
            >
              {isFinalizing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Finalize & Generate Customer Message
            </Button>
          </div>
        )}

        {/* Finalize result */}
        {finalizeResult && (
          <div className="space-y-4">
            <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
              <p className="text-sm font-medium text-green-700 dark:text-green-300">
                ✓ Case closed
              </p>
            </div>

            {/* Customer reply */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Customer Reply</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(editableReply, 'reply')}
                >
                  {copiedReply ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  <span className="ml-1">Copy</span>
                </Button>
              </div>
              <Textarea
                value={editableReply}
                onChange={(e) => setEditableReply(e.target.value)}
                className="min-h-[120px]"
              />
            </div>

            {/* Next actions */}
            {finalizeResult.next_actions && finalizeResult.next_actions.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Next Actions</Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(JSON.stringify(finalizeResult.next_actions, null, 2), 'actions')}
                  >
                    {copiedActions ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    <span className="ml-1">Copy JSON</span>
                  </Button>
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Action</TableHead>
                        <TableHead className="text-xs">Details</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {finalizeResult.next_actions.map((action, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium text-sm">{action.action}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {action.details || '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
