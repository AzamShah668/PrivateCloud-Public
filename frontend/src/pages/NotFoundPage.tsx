import { Link } from "react-router-dom";
import Button from "@/components/ui/Button";
import { ArrowLeft } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center bg-deepest px-4 text-center">
      <p
        className="text-8xl font-bold text-accent-blue/20 mb-4"
        style={{ fontFamily: "var(--font-display)" }}
      >
        404
      </p>
      <h1
        className="text-2xl font-semibold text-primary mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Page not found
      </h1>
      <p className="text-secondary mb-8 max-w-md">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link to="/">
        <Button variant="secondary">
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
}
