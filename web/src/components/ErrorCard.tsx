"use client";

import { AlertTriangle } from "lucide-react";

export function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center py-12 text-center">
      <AlertTriangle className="h-8 w-8 text-slate-300" />
      <p className="mt-2 text-sm text-slate-500">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 text-sm text-blue-600 underline">
          다시 시도
        </button>
      )}
    </div>
  );
}
