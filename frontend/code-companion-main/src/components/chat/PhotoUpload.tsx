import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, Camera, Loader2, CheckCircle, X } from "lucide-react";
import { uploadPhoto } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface PhotoUploadProps {
  caseId: string;
  onUploadSuccess?: (photoUrl: string) => void;
}

export function PhotoUpload({ caseId, onUploadSuccess }: PhotoUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedPhotos, setUploadedPhotos] = useState<string[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a JPG, PNG, or WebP image",
        variant: "destructive",
      });
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target?.result as string);
    reader.readAsDataURL(file);

    // Upload
    setIsUploading(true);
    try {
      const response = await uploadPhoto(caseId, file);
      setUploadedPhotos((prev) => [...prev, response.photo_url]);
      onUploadSuccess?.(response.photo_url);
      toast({
        title: "Photo uploaded",
        description: "Your photo has been sent for review",
      });
    } catch (error) {
      toast({
        title: "Upload failed",
        description: "Please try again",
        variant: "destructive",
      });
      setPreviewUrl(null);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const clearPreview = () => {
    setPreviewUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Camera className="h-5 w-5 text-amber-600" />
          Upload Photo Evidence
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Please upload photos of the issue to help us process your warranty claim.
        </p>

        {/* Preview area */}
        {previewUrl && (
          <div className="relative inline-block">
            <img
              src={previewUrl}
              alt="Preview"
              className="max-h-32 rounded-lg border"
            />
            {!isUploading && (
              <button
                onClick={clearPreview}
                className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1"
              >
                <X className="h-3 w-3" />
              </button>
            )}
            {isUploading && (
              <div className="absolute inset-0 bg-background/80 rounded-lg flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            )}
          </div>
        )}

        {/* Uploaded photos */}
        {uploadedPhotos.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-green-600 flex items-center gap-1">
              <CheckCircle className="h-4 w-4" />
              {uploadedPhotos.length} photo(s) uploaded
            </p>
            <div className="flex gap-2 flex-wrap">
              {uploadedPhotos.map((url, i) => (
                <img
                  key={i}
                  src={url}
                  alt={`Uploaded ${i + 1}`}
                  className="h-16 w-16 object-cover rounded border"
                />
              ))}
            </div>
          </div>
        )}

        {/* Upload button */}
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileSelect}
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            Choose Photo
          </Button>
        </div>

        {uploadedPhotos.length > 0 && (
          <div className="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              ✓ Sent for review — Waiting for human review
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
