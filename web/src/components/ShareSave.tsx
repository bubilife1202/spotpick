"use client";

import { useState } from "react";
import { Share2, Bookmark, BookmarkCheck, Link2, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ShareSaveProps {
  districtName: string;
  districtData: unknown;
}

export function ShareSave({ districtName, districtData }: ShareSaveProps) {
  void districtData;
  const [isSaved, setIsSaved] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = localStorage.getItem("saved_districts");
    if (!saved) return false;
    const list = JSON.parse(saved) as string[];
    return list.includes(districtName);
  });
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSave = () => {
    const saved = localStorage.getItem("saved_districts");
    let list: string[] = saved ? JSON.parse(saved) : [];
    
    if (isSaved) {
      list = list.filter((d) => d !== districtName);
    } else {
      list.push(districtName);
    }
    
    localStorage.setItem("saved_districts", JSON.stringify(list));
    setIsSaved(!isSaved);
  };

  const handleCopyLink = async () => {
    const url = `${window.location.origin}?district=${encodeURIComponent(districtName)}`;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = async (platform: "kakao" | "twitter") => {
    const text = `${districtName} 상권 분석 결과 - Builder Curation`;
    const url = `${window.location.origin}?district=${encodeURIComponent(districtName)}`;

    if (platform === "twitter") {
      window.open(
        `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
        "_blank"
      );
    } else if (platform === "kakao") {
      if (typeof window !== "undefined" && (window as unknown as { Kakao?: { Share?: { sendDefault: (config: unknown) => void } } }).Kakao?.Share) {
        (window as unknown as { Kakao: { Share: { sendDefault: (config: unknown) => void } } }).Kakao.Share.sendDefault({
          objectType: "feed",
          content: {
            title: `${districtName} 상권 분석`,
            description: "AI 기반 창업 상권 분석 결과",
            imageUrl: `${window.location.origin}/og-image.png`,
            link: { mobileWebUrl: url, webUrl: url },
          },
          buttons: [
            { title: "분석 보기", link: { mobileWebUrl: url, webUrl: url } },
          ],
        });
      } else {
        handleCopyLink();
      }
    }
    
    setShowShareMenu(false);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleSave}
        className={cn(
          "p-2 rounded-lg transition-all",
          isSaved
            ? "bg-amber-50 text-amber-600"
            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
        )}
        title={isSaved ? "저장됨" : "저장하기"}
      >
        {isSaved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
      </button>

      <div className="relative">
        <button
          onClick={() => setShowShareMenu(!showShareMenu)}
          className="p-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all"
          title="공유하기"
        >
          <Share2 size={18} />
        </button>

        {showShareMenu && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setShowShareMenu(false)}
            />
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border z-50 overflow-hidden">
              <div className="p-2">
                <button
                  onClick={handleCopyLink}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg"
                >
                  {copied ? <Check size={16} className="text-green-500" /> : <Link2 size={16} />}
                  {copied ? "복사됨!" : "링크 복사"}
                </button>
                <button
                  onClick={() => handleShare("kakao")}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg"
                >
                  <span className="w-4 h-4 bg-yellow-400 rounded-sm" />
                  카카오톡 공유
                </button>
                <button
                  onClick={() => handleShare("twitter")}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg"
                >
                  <span className="w-4 h-4 bg-blue-400 rounded-sm" />
                  X (트위터) 공유
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function SavedDistrictsList() {
  const [savedList, setSavedList] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    const saved = localStorage.getItem("saved_districts");
    return saved ? JSON.parse(saved) : [];
  });

  const handleRemove = (name: string) => {
    const newList = savedList.filter((d) => d !== name);
    localStorage.setItem("saved_districts", JSON.stringify(newList));
    setSavedList(newList);
  };

  if (savedList.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Bookmark size={32} className="mx-auto mb-2 opacity-50" />
        <p className="text-sm">저장된 상권이 없습니다</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {savedList.map((name) => (
        <div
          key={name}
          className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg"
        >
          <span className="font-medium text-gray-900">{name}</span>
          <button
            onClick={() => handleRemove(name)}
            className="p-1 text-gray-400 hover:text-red-500"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
