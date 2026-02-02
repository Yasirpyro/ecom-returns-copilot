import { useState } from "react";
import { CasesList } from "@/components/reviewer/CasesList";
import { CaseDetail } from "@/components/reviewer/CaseDetail";
import { Button } from "@/components/ui/button";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setReviewerAuth, clearReviewerAuth } from "@/lib/api";

export default function ReviewerDashboard() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAuthed, setIsAuthed] = useState(
    () => !!sessionStorage.getItem("reviewer_basic_auth")
  );

  const handleLogin = () => {
    if (!username || !password) return;
    setReviewerAuth(username, password);
    setIsAuthed(true);
  };

  const handleLogout = () => {
    clearReviewerAuth();
    setIsAuthed(false);
    setUsername("");
    setPassword("");
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="font-semibold">Reviewer Dashboard</h1>
            <p className="text-xs text-muted-foreground">Review and approve warranty claims</p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Cases list - left panel */}
        <div className={cn(
          "w-full md:w-80 lg:w-96 border-r flex-shrink-0 overflow-hidden",
          selectedCaseId && "hidden md:block"
        )}>
          {!isAuthed ? (
            <div className="p-4">
              <div className="border rounded-lg p-4 space-y-3 bg-card">
                <div>
                  <h2 className="font-semibold text-sm">Reviewer Login</h2>
                  <p className="text-xs text-muted-foreground">Enter credentials to access cases</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reviewer-username">Username</Label>
                  <Input
                    id="reviewer-username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="reviewer"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reviewer-password">Password</Label>
                  <Input
                    id="reviewer-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
                <Button onClick={handleLogin} className="w-full">
                  Sign in
                </Button>
              </div>
            </div>
          ) : (
            <CasesList
              selectedCaseId={selectedCaseId}
              onSelectCase={setSelectedCaseId}
            />
          )}
        </div>

        {/* Case detail - right panel */}
        <div className={cn(
          "flex-1 overflow-hidden",
          !selectedCaseId && "hidden md:flex items-center justify-center"
        )}>
          {selectedCaseId && isAuthed ? (
            <CaseDetail
              caseId={selectedCaseId}
              onBack={() => setSelectedCaseId(null)}
              onCaseClosed={() => setSelectedCaseId(null)}
            />
          ) : (
            <div className="text-center text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>{isAuthed ? "Select a case to review" : "Sign in to review cases"}</p>
            </div>
          )}
        </div>
      </div>

      {isAuthed && (
        <div className="border-t bg-card px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
          <span>Reviewer authenticated</span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </div>
      )}
    </div>
  );
}
