"use client";

import { useEffect, useState } from "react";
import { MapPin, TrendingUp, Building2, Coffee, BarChart3, Users, Clock, Plus, Check, MessageCircle } from "lucide-react";
import { SearchForm } from "@/components/SearchForm";
import { RecommendationCard } from "@/components/RecommendationCard";
import { useRecommendations } from "@/hooks/useRecommendations";
import { LocationRecommendation } from "@/lib/api";
import { CompareDistricts, CompareButton, District } from "@/components/CompareDistricts";
import { ShareSave } from "@/components/ShareSave";
import dynamic from "next/dynamic";

const MapView = dynamic(() => import("@/components/MapView"), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl">
      <div className="text-center text-gray-500">
        <MapPin size={48} className="mx-auto mb-2 opacity-50 animate-pulse" />
        <p className="text-sm">지도 로딩 중...</p>
      </div>
    </div>
  )
});

interface SearchModeProps {
  onSwitchToChat: () => void;
  initialSearchParams?: {
    budgetMin: number;
    budgetMax: number;
    district?: string;
  };
}

export default function SearchMode({ onSwitchToChat, initialSearchParams }: SearchModeProps) {
  const [searchParams, setSearchParams] = useState<{
    budgetMin: number;
    budgetMax: number;
    district?: string;
  } | null>(initialSearchParams ?? null);

  const [selectedLocation, setSelectedLocation] = useState<LocationRecommendation | null>(null);
  const [compareList, setCompareList] = useState<District[]>([]);
  const [showCompare, setShowCompare] = useState(false);

  const { data, isLoading, error } = useRecommendations({
    budget_min: searchParams?.budgetMin || 0,
    budget_max: searchParams?.budgetMax || 0,
    preferred_district: searchParams?.district,
    enabled: searchParams !== null,
  });

  useEffect(() => {
    if (!initialSearchParams) return;
    if (searchParams !== null) return;
    setSearchParams(initialSearchParams);
  }, [initialSearchParams, searchParams]);

  const handleSearch = (params: {
    budgetMin: number;
    budgetMax: number;
    district?: string;
  }) => {
    setSearchParams(params);
    setSelectedLocation(null);
  };

  const convertToDistrict = (rec: LocationRecommendation): District => ({
    name: rec.area_name,
    type: rec.area_type,
    monthly_sales: Math.round(rec.success_probability * 50000000),
    estimated_rent: rec.estimated_monthly_rent,
    survival_rate: rec.area_stats.survival_rate_3y,
    store_count: rec.area_stats.competitor_count,
    peak_time: "12:00 - 14:00",
    main_age_group: "20-30대",
    female_ratio: 0.6,
  });

  const toggleCompare = (rec: LocationRecommendation, e: React.MouseEvent) => {
    e.stopPropagation();
    const district = convertToDistrict(rec);
    setCompareList(prev => {
      const exists = prev.find(d => d.name === district.name);
      if (exists) {
        return prev.filter(d => d.name !== district.name);
      }
      if (prev.length >= 3) {
        alert("최대 3개까지 비교할 수 있습니다.");
        return prev;
      }
      return [...prev, district];
    });
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
              <Coffee className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">Builder Curation</h1>
              <p className="text-xs text-gray-500 hidden sm:block">AI 창업 컨설턴트</p>
            </div>
          </div>
          <nav className="flex items-center gap-4">
            <button
              onClick={onSwitchToChat}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <MessageCircle size={16} />
              <span className="hidden sm:inline">대화 모드</span>
            </button>
          </nav>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {!searchParams && (
          <section className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm font-medium mb-4">
              <BarChart3 size={14} />
              1,077개 상권 · 64개 분석 지표
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              창업, 어디서 해야<br className="sm:hidden" /> 성공할까?
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto text-sm sm:text-base">
              서울시 6년간 데이터를 AI가 분석했습니다.<br />
              <strong className="text-blue-600">시간대별 · 요일별 · 연령대별</strong> 맞춤 상권을 추천받으세요.
            </p>
          </section>
        )}

        <SearchForm onSearch={handleSearch} isLoading={isLoading} />

        {error && (
          <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
            오류가 발생했습니다. 다시 시도해주세요.
          </div>
        )}

        {data && data.recommendations.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900">
                추천 위치 TOP {data.recommendations.length}
              </h3>
              <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {data.total_candidates}개 후보 중 분석
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollbar-thin">
                {data.recommendations.map((rec) => {
                  const isCompared = compareList.some(d => d.name === rec.area_name);
                  return (
                    <div key={rec.rank} className="relative group">
                      <RecommendationCard
                        recommendation={rec}
                        isSelected={selectedLocation?.rank === rec.rank}
                        onClick={() => setSelectedLocation(rec)}
                      />
                      <button
                        onClick={(e) => toggleCompare(rec, e)}
                        className={`absolute top-4 right-4 p-2 rounded-full shadow-md transition-all z-10 ${
                          isCompared 
                            ? "bg-indigo-600 text-white hover:bg-indigo-700" 
                            : "bg-white text-gray-400 hover:text-indigo-600 hover:bg-gray-50 opacity-0 group-hover:opacity-100"
                        }`}
                        title={isCompared ? "비교 목록에서 제거" : "비교 목록에 추가"}
                      >
                        {isCompared ? <Check size={16} /> : <Plus size={16} />}
                      </button>
                    </div>
                  );
                })}
              </div>

              <div className="bg-white rounded-2xl shadow-lg p-4 h-[600px] border">
                {selectedLocation ? (
                  <div className="h-full flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-lg font-bold flex items-center gap-2">
                        <MapPin className="text-blue-600" size={20} />
                        {selectedLocation.area_name} 상세 분석
                      </h4>
                      <ShareSave 
                        districtName={selectedLocation.area_name} 
                        districtData={selectedLocation} 
                      />
                    </div>
                    
                    <div className="flex-1 rounded-xl overflow-hidden mb-4">
                      {data && (
                        <MapView
                          locations={data.recommendations.map(rec => ({
                            lat: rec.lat,
                            lng: rec.lng,
                            name: rec.area_name,
                            rank: rec.rank
                          }))}
                          selectedLocation={selectedLocation ? { lat: selectedLocation.lat, lng: selectedLocation.lng } : null}
                          onLocationSelect={(loc) => {
                            const found = data.recommendations.find(
                              r => Math.abs(r.lat - loc.lat) < 0.0001 && Math.abs(r.lng - loc.lng) < 0.0001
                            );
                            if (found) setSelectedLocation(found);
                          }}
                        />
                      )}
                    </div>

                    <div className="space-y-4">
                      <div>
                        <h5 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                          <TrendingUp size={14} className="text-green-600" />
                          인근 성공 매장
                        </h5>
                        {selectedLocation.nearby_successful_stores.length > 0 ? (
                          <div className="space-y-1">
                            {selectedLocation.nearby_successful_stores.map((store, i) => (
                              <div key={i} className="flex justify-between text-sm bg-gray-50 px-3 py-2 rounded-lg">
                                <span className="text-gray-700">{store.name}</span>
                                <span className="text-green-600 font-semibold">
                                  {(store.score * 100).toFixed(0)}점
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">
                            (베타) 인근 성공 매장 데이터는 준비 중입니다.
                          </p>
                        )}
                      </div>

                      <div>
                        <h5 className="text-sm font-semibold text-gray-700 mb-2">추천 전략</h5>
                        <ul className="text-sm text-gray-600 space-y-1">
                          {selectedLocation.recommendations.slice(0, 3).map((rec, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-blue-500 mt-0.5">•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <MapPin size={48} className="mx-auto mb-3 opacity-40" />
                      <p className="font-medium">왼쪽에서 위치를 선택하면</p>
                      <p className="text-sm">상세 분석을 볼 수 있습니다</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {data && data.recommendations.length === 0 && (
          <div className="mt-8 text-center py-12 bg-white rounded-2xl shadow-lg border">
            <Building2 size={48} className="mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              조건에 맞는 추천 위치가 없습니다
            </h3>
            <p className="text-gray-500 text-sm">
              예산 범위를 조정하거나 다른 지역을 선택해보세요
            </p>
          </div>
        )}

        {!searchParams && (
          <>
            <section className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
              <FeatureCard
                icon={<Clock className="text-blue-600" />}
                title="시간대별 분석"
                description="새벽부터 심야까지 6개 시간대별 매출 패턴 분석"
              />
              <FeatureCard
                icon={<Users className="text-purple-600" />}
                title="고객층 분석"
                description="10대~60대+ 연령별, 성별 고객 비율 파악"
              />
              <FeatureCard
                icon={<TrendingUp className="text-green-600" />}
                title="6년 트렌드"
                description="2019~2025년 분기별 매출 추이 및 생존율 변화"
              />
            </section>

            <section className="mt-12 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 text-white text-center">
              <h3 className="text-2xl font-bold mb-3">AI와 대화하며 상권 분석하기</h3>
              <p className="text-blue-100 mb-6 max-w-lg mx-auto">
                &quot;홍대에서 20대 여성 타겟 상권 추천해줘&quot; 처럼<br />
                자연어로 질문하면 맞춤 분석을 제공합니다.
              </p>
              <button
                onClick={onSwitchToChat}
                className="px-8 py-3 bg-white text-blue-600 font-semibold rounded-xl hover:bg-blue-50 transition-colors"
              >
                AI 대화 시작하기
              </button>
            </section>
          </>
        )}
      </div>
      
      <CompareButton onClick={() => setShowCompare(true)} count={compareList.length} />
      <CompareDistricts 
        isOpen={showCompare} 
        onClose={() => setShowCompare(false)} 
        districts={compareList} 
      />
    </main>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-lg border p-6 hover:shadow-xl transition-shadow">
      <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
    </div>
  );
}
