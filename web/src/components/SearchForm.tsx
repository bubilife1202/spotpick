"use client";

import { useState } from "react";
import { Search } from "lucide-react";

interface Props {
  onSearch: (params: {
    budgetMin: number;
    budgetMax: number;
    district?: string;
  }) => void;
  isLoading?: boolean;
}

const DISTRICTS = [
  "전체",
  "강남",
  "서초",
  "마포",
  "용산",
  "성동",
  "종로",
  "중구",
  "영등포",
  "송파",
  "광진",
];

export function SearchForm({ onSearch, isLoading }: Props) {
  const [budgetMin, setBudgetMin] = useState(2000000);
  const [budgetMax, setBudgetMax] = useState(5000000);
  const [district, setDistrict] = useState("전체");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch({
      budgetMin,
      budgetMax,
      district: district === "전체" ? undefined : district,
    });
  };

  const formatMoney = (value: number) => {
    return `${(value / 10000).toFixed(0)}만원`;
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">창업 조건 입력</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            선호 지역
          </label>
          <select
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            최소 예산 (월 임대료)
          </label>
          <div className="relative">
            <input
              type="range"
              min={1000000}
              max={10000000}
              step={500000}
              value={budgetMin}
              onChange={(e) => setBudgetMin(Number(e.target.value))}
              className="w-full"
            />
            <div className="text-center text-sm font-medium text-gray-900">
              {formatMoney(budgetMin)}
            </div>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            최대 예산 (월 임대료)
          </label>
          <div className="relative">
            <input
              type="range"
              min={1000000}
              max={10000000}
              step={500000}
              value={budgetMax}
              onChange={(e) => setBudgetMax(Number(e.target.value))}
              className="w-full"
            />
            <div className="text-center text-sm font-medium text-gray-900">
              {formatMoney(budgetMax)}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          예산 범위: {formatMoney(budgetMin)} ~ {formatMoney(budgetMax)}
        </div>
        <button
          type="submit"
          disabled={isLoading || budgetMin > budgetMax}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              분석 중...
            </>
          ) : (
            <>
              <Search size={18} />
              추천 받기
            </>
          )}
        </button>
      </div>
    </form>
  );
}
