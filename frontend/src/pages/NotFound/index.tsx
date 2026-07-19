import { useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { Button } from "@/components/ui/button";
import { FileQuestion, Home } from "lucide-react";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <PageContainer>
      <div className="flex min-h-[500px] flex-col items-center justify-center gap-6">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-muted">
          <FileQuestion size={48} className="text-muted-foreground" />
        </div>
        <h1 className="text-4xl font-bold text-foreground">404</h1>
        <p className="text-lg text-muted-foreground">Page not found</p>
        <p className="max-w-sm text-center text-sm text-muted-foreground">
          The page you are looking for does not exist or has been moved.
        </p>
        <Button size="lg" onClick={() => navigate("/")}>
          <Home size={16} />
          Back to Dashboard
        </Button>
      </div>
    </PageContainer>
  );
}
