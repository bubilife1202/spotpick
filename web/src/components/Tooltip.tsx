"use client";

import { useState, useRef, useEffect } from "react";
import { Info } from "lucide-react";
import { GLOSSARY } from "@/lib/chat-api";

interface TooltipProps {
  term: string;
  children: React.ReactNode;
}

export function Tooltip({ term, children }: TooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLSpanElement>(null);

  const definition = GLOSSARY[term];

  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 8,
        left: Math.max(16, rect.left - 100),
      });
    }
  }, [isOpen]);

  if (!definition) return <>{children}</>;

  return (
    <span className="relative inline">
      <span
        ref={triggerRef}
        className="border-b border-dashed border-blue-400 cursor-help text-blue-600"
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onClick={() => setIsOpen(!isOpen)}
      >
        {children}
      </span>
      
      {isOpen && (
        <div
          className="fixed z-50 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl"
          style={{ top: position.top, left: position.left }}
        >
          <div className="flex items-start gap-2">
            <Info size={14} className="text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold mb-1">{term}</p>
              <p className="text-gray-300 leading-relaxed">{definition}</p>
            </div>
          </div>
          <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-gray-900" />
        </div>
      )}
    </span>
  );
}

export function GlossaryBadge({ term }: { term: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const definition = GLOSSARY[term];

  if (!definition) return null;

  return (
    <span className="relative inline-flex items-center">
      <button
        className="ml-1 w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-xs flex items-center justify-center hover:bg-blue-200"
        onClick={() => setIsOpen(!isOpen)}
        onBlur={() => setIsOpen(false)}
      >
        ?
      </button>
      
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl z-50">
          <p className="font-semibold mb-1">{term}</p>
          <p className="text-gray-300">{definition}</p>
        </div>
      )}
    </span>
  );
}
