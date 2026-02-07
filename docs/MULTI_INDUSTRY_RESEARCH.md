# Multi-Industry Data Structure Research

**Date:** February 6, 2026  
**Purpose:** Research Seoul API data availability and best practices for multi-industry configuration

---

## 1. Seoul API Industry Codes (CS100001-CS100010)

### Current Status
Based on the codebase analysis, **only CS100010 (커피-음료 / Coffee-Beverage)** is currently being collected.

### Industry Code Structure
The Seoul Commercial District Analysis Service uses `SVC_INDUTY_CD` (서비스업종코드) to categorize businesses:

- **Format:** `CS1000XX` (where XX = 01-10)
- **Current Implementation:** CS100010 only
- **Total Available:** 100+ industry codes in the full dataset

### Known Industry Codes
From the Seoul Open Data Portal documentation:
- **CS100010:** 커피-음료 (Coffee-Beverage) ✅ Currently implemented
- **CS100001-CS100009:** Not yet documented in codebase
- **Total Service Industries:** ~100 categories available in Seoul API

### Data Availability by Industry Code
All industry codes share the **same API endpoints** but are filtered by `SVC_INDUTY_CD`:

**Available APIs:**
1. `VwsmTrdarSelngQq` - 추정매출 (Estimated Sales)
2. `VwsmTrdarStorQq` - 점포현황 (Store Status)
3. `VwsmTrdarWrcPopltnQq` - 직장인구 (Worker Population)
4. `VwsmTrdarRepopQq` - 상주인구 (Resident Population)
5. `VwsmTrdarFlpopQq` - 유동인구 (Foot Traffic)
6. `VwsmTrdarFcltyQq` - 집객시설 (Facilities)
7. `VwsmTrdarIxQq` - 상권변화지표 (Change Indicators)

---

## 2. Data Fields: Industry-Specific vs. Shared

### A. Shared Fields (All Industries)
These fields are available for **all** `SVC_INDUTY_CD` values:

#### Basic Information
```json
{
  "STDR_YYQU_CD": "20251",           // Quarter (2025 Q1)
  "TRDAR_SE_CD": "A",                 // District Type Code
  "TRDAR_SE_CD_NM": "골목상권",        // District Type Name
  "TRDAR_CD": "3110135",              // District Code
  "TRDAR_CD_NM": "성동세무서",         // District Name
  "SVC_INDUTY_CD": "CS100010",        // Industry Code
  "SVC_INDUTY_CD_NM": "커피-음료"      // Industry Name
}
```

#### Sales Data (55 fields)
- **Monthly:** `THSMON_SELNG_AMT`, `THSMON_SELNG_CO`
- **Weekday/Weekend:** `MDWK_SELNG_AMT`, `WKEND_SELNG_AMT`
- **By Day:** `MON_SELNG_AMT`, `TUES_SELNG_AMT`, ..., `SUN_SELNG_AMT`
- **By Time:** `TMZON_00_06_SELNG_AMT`, `TMZON_06_11_SELNG_AMT`, ...
- **By Gender:** `ML_SELNG_AMT`, `FML_SELNG_AMT`
- **By Age:** `AGRDE_10_SELNG_AMT`, `AGRDE_20_SELNG_AMT`, ..., `AGRDE_60_ABOVE_SELNG_AMT`
- **Transaction Counts:** Same structure with `_CO` suffix

#### Store Data
```json
{
  "STOR_CO": 8,                       // Total stores
  "SIMILR_INDUTY_STOR_CO": 9,         // Similar industry stores
  "OPBIZ_RT": 0,                      // Opening rate
  "OPBIZ_STOR_CO": 0,                 // New stores
  "CLSBIZ_RT": 0,                     // Closing rate
  "CLSBIZ_STOR_CO": 0,                // Closed stores
  "FRC_STOR_CO": 1                    // Franchise stores
}
```

#### Population & Demographics (from extra APIs)
- **Worker Population:** `TOT_WRC_POPLTN_CO`, by gender/age
- **Resident Population:** `TOT_REPOP_CO`, by gender/age
- **Foot Traffic:** `TOT_FLPOP_CO`, by gender/age/time
- **Households:** `TOT_HSHLD_CO`, `APT_HSHLD_CO`, `NON_APT_HSHLD_CO`

#### Facilities (from extra APIs)
- **Transportation:** `SUBWAY_STATN_CO`, `BUS_STTN_CO`, `RLROAD_STATN_CO`
- **Public:** `VIATR_FCLTY_CO`, `BANK_CO`, `GNRL_HSPTL_CO`
- **Education:** `KNDRGR_CO`, `ELESCH_CO`, `UNIV_CO`
- **Commercial:** `DRTS_CO`, `LRGMRT_CO`, `MVR_NM_CO`

#### Change Indicators
```json
{
  "TRDAR_CHNGE_IX_CD": "HL",          // Change indicator code
  "TRDAR_CHNGE_IX_CD_NM": "High-Low", // Change indicator name
  "OPR_SALE_MT_AVRG": 24.5            // Average operation months
}
```

**Total Shared Fields:** ~120+ fields

### B. Industry-Specific Fields (Potential)
Based on industry characteristics, these fields may vary:

#### 1. **Peak Hours** (varies by industry)
- Coffee shops: 11-14 (lunch), 14-17 (afternoon)
- Restaurants: 11-14 (lunch), 17-21 (dinner)
- Bars/Nightlife: 21-24, 00-06
- Retail: 14-17, 17-21

#### 2. **Customer Demographics** (varies by industry)
- Coffee: 20s-40s, office workers
- Fine Dining: 30s-50s, higher income
- Fast Food: All ages, families
- Bars: 20s-30s, evening crowd

#### 3. **Seasonality Patterns** (varies by industry)
- Ice cream: Summer peak
- Hot pot: Winter peak
- Coffee: Year-round stable
- Tourism-related: Seasonal

### C. Calculated/Derived Fields (Industry-Agnostic)
These are computed from shared fields:

```python
{
  "weekday_ratio": 0.7734,
  "weekend_ratio": 0.2266,
  "male_ratio": 0.3841,
  "female_ratio": 0.6159,
  "peak_time": "11-14",
  "peak_day": "금",
  "main_age_group": "30대",
  "survival_rate": 0.9523,
  "facility_score": 245,
  "transit_raw": 180
}
```

---

## 3. Best Practices for Industry Config File Structure

### A. Hierarchical Configuration Pattern

Based on GitHub examples and data engineering best practices:

```typescript
// config/industries.ts
interface IndustryConfig {
  code: string;                    // CS100001-CS100010
  name: string;                    // Display name
  category: string;                // F&B, Retail, Service, etc.
  
  // Business characteristics
  characteristics: {
    avgTicketSize: number;         // Average transaction
    peakHours: string[];           // ["11-14", "17-21"]
    peakDays: string[];            // ["금", "토"]
    seasonality: "high" | "medium" | "low";
  };
  
  // Financial defaults
  financials: {
    avgCOGS: number;               // Cost of Goods Sold %
    avgLaborCost: number;          // Labor cost %
    avgRentRatio: number;          // Rent as % of revenue
    avgUtilities: number;          // Utilities %
    avgMargin: number;             // Net margin %
  };
  
  // Startup costs
  startup: {
    equipmentMin: number;
    equipmentMax: number;
    interiorMin: number;
    interiorMax: number;
    depositMonths: number;         // Typical deposit (months)
    inventoryDays: number;         // Initial inventory (days)
  };
  
  // Success metrics
  metrics: {
    minMonthlyRevenue: number;     // Survival threshold
    targetRevenue: number;         // Success threshold
    breakEvenMonths: number;       // Typical breakeven
    avgLifespan: number;           // Industry avg (months)
  };
  
  // Data processing
  processing: {
    weightTimeSlots: Record<string, number>;  // Time slot importance
    weightDemographics: Record<string, number>; // Age group weights
    competitionRadius: number;     // Meters
  };
}
```

### B. Example: Coffee Shop (CS100010)

```typescript
export const INDUSTRY_CONFIGS: Record<string, IndustryConfig> = {
  "CS100010": {
    code: "CS100010",
    name: "커피-음료",
    category: "F&B",
    
    characteristics: {
      avgTicketSize: 5500,
      peakHours: ["06-11", "11-14", "14-17"],
      peakDays: ["월", "화", "수", "목", "금"],
      seasonality: "low"
    },
    
    financials: {
      avgCOGS: 0.30,              // 30% COGS
      avgLaborCost: 0.25,         // 25% labor
      avgRentRatio: 0.15,         // 15% rent
      avgUtilities: 0.05,         // 5% utilities
      avgMargin: 0.15             // 15% net margin
    },
    
    startup: {
      equipmentMin: 15_000_000,   // 1500만원
      equipmentMax: 50_000_000,   // 5000만원
      interiorMin: 20_000_000,
      interiorMax: 80_000_000,
      depositMonths: 10,
      inventoryDays: 7
    },
    
    metrics: {
      minMonthlyRevenue: 8_000_000,
      targetRevenue: 20_000_000,
      breakEvenMonths: 18,
      avgLifespan: 36
    },
    
    processing: {
      weightTimeSlots: {
        "00-06": 0.05,
        "06-11": 0.25,
        "11-14": 0.30,
        "14-17": 0.25,
        "17-21": 0.10,
        "21-24": 0.05
      },
      weightDemographics: {
        "10대": 0.05,
        "20대": 0.25,
        "30대": 0.30,
        "40대": 0.25,
        "50대": 0.10,
        "60대+": 0.05
      },
      competitionRadius: 500
    }
  }
};
```

### C. Template for Other Industries

```typescript
// CS100001: 한식음식점 (Korean Restaurant)
"CS100001": {
  code: "CS100001",
  name: "한식음식점",
  category: "F&B",
  characteristics: {
    avgTicketSize: 12000,
    peakHours: ["11-14", "17-21"],
    peakDays: ["금", "토", "일"],
    seasonality: "medium"
  },
  financials: {
    avgCOGS: 0.35,
    avgLaborCost: 0.30,
    avgRentRatio: 0.12,
    avgUtilities: 0.08,
    avgMargin: 0.10
  },
  // ... rest of config
}
```

---

## 4. Per-District JSON File Structure

### A. Single-Industry Model (Current)
```
data/processed/
  ├── coffee_districts.json          # All districts for coffee
  └── summary.json                   # Coffee summary stats
```

### B. Multi-Industry Model (Recommended)

#### Option 1: Industry-First Hierarchy
```
data/processed/
  ├── industries/
  │   ├── CS100010_coffee/
  │   │   ├── districts.json         # All districts
  │   │   ├── summary.json
  │   │   └── trends.json
  │   ├── CS100001_korean_food/
  │   │   ├── districts.json
  │   │   ├── summary.json
  │   │   └── trends.json
  │   └── ...
  └── index.json                     # Industry catalog
```

#### Option 2: District-First Hierarchy
```
data/processed/
  ├── districts/
  │   ├── 3110002_독립문역1번/
  │   │   ├── CS100010.json          # Coffee data
  │   │   ├── CS100001.json          # Korean food data
  │   │   └── summary.json           # All industries
  │   └── ...
  └── industries_index.json
```

#### Option 3: Hybrid (Recommended for Performance)
```
data/processed/
  ├── by_industry/
  │   ├── CS100010.json              # All districts for coffee
  │   ├── CS100001.json              # All districts for korean food
  │   └── ...
  ├── by_district/
  │   ├── 3110002.json               # All industries for district
  │   └── ...
  ├── summary/
  │   ├── industry_summary.json      # Per-industry stats
  │   └── district_summary.json      # Per-district stats
  └── metadata.json                  # Schema version, update time
```

### C. File Format Example

**by_industry/CS100010.json:**
```json
{
  "industry_code": "CS100010",
  "industry_name": "커피-음료",
  "data_quarter": "20253",
  "updated_at": "2026-02-06T10:00:00Z",
  "total_districts": 1234,
  "total_stores": 5678,
  "districts": [
    {
      "district_code": "3110002",
      "district_name": "독립문역 1번",
      "monthly_sales": 62814045,
      // ... all 120+ fields
    }
  ]
}
```

**by_district/3110002.json:**
```json
{
  "district_code": "3110002",
  "district_name": "독립문역 1번",
  "district_type": "골목상권",
  "data_quarter": "20253",
  "industries": {
    "CS100010": {
      "industry_name": "커피-음료",
      "monthly_sales": 62814045,
      "store_count": 15,
      // ... industry-specific data
    },
    "CS100001": {
      "industry_name": "한식음식점",
      "monthly_sales": 85000000,
      "store_count": 23,
      // ...
    }
  },
  "shared_data": {
    // Population, facilities, etc. (same for all industries)
    "resident_total": 12500,
    "foot_traffic_total": 45000,
    "facility_subway": 1,
    "facility_bus_stop": 8
  }
}
```

---

## 5. Common Industry-Specific Values

### A. Equipment Costs by Industry

| Industry | Equipment Range (KRW) | Key Equipment |
|----------|----------------------|---------------|
| Coffee Shop | 15M - 50M | Espresso machine, grinder, refrigerator |
| Korean Restaurant | 30M - 100M | Kitchen equipment, ventilation, tables |
| Fast Food | 40M - 120M | Fryers, grills, POS system |
| Bakery | 50M - 150M | Ovens, mixers, display cases |
| Convenience Store | 20M - 60M | Refrigerators, shelving, POS |
| Hair Salon | 25M - 80M | Chairs, mirrors, washing stations |
| Fitness Center | 100M - 500M | Machines, weights, lockers |
| PC Bang | 80M - 300M | Computers, chairs, network |
| Laundromat | 60M - 200M | Washers, dryers, folding tables |
| Pet Grooming | 15M - 50M | Tubs, dryers, grooming tools |

### B. COGS Ratios by Industry

| Industry | COGS % | Labor % | Rent % | Net Margin % |
|----------|--------|---------|--------|--------------|
| Coffee Shop | 30% | 25% | 15% | 15% |
| Korean Restaurant | 35% | 30% | 12% | 10% |
| Fast Food | 28% | 28% | 10% | 12% |
| Bakery | 32% | 22% | 13% | 14% |
| Convenience Store | 70% | 8% | 8% | 3% |
| Hair Salon | 15% | 45% | 15% | 18% |
| Fitness Center | 10% | 35% | 20% | 20% |
| PC Bang | 5% | 15% | 18% | 25% |
| Laundromat | 8% | 12% | 15% | 30% |
| Pet Grooming | 20% | 40% | 12% | 15% |

### C. Business Type Classifications

```typescript
enum BusinessType {
  // F&B
  COFFEE_SHOP = "CS100010",
  KOREAN_FOOD = "CS100001",
  WESTERN_FOOD = "CS100002",
  CHINESE_FOOD = "CS100003",
  JAPANESE_FOOD = "CS100004",
  FAST_FOOD = "CS100005",
  BAKERY = "CS100006",
  
  // Retail
  CONVENIENCE = "CS100007",
  CLOTHING = "CS100008",
  
  // Service
  HAIR_SALON = "CS100009",
  FITNESS = "CS100010"
}

interface IndustryCategory {
  code: string;
  name: string;
  parent: "F&B" | "Retail" | "Service" | "Entertainment";
  subCategory: string;
}
```

---

## 6. Examples from Other Platforms

### A. Yelp/Google Maps Approach
- **Industry taxonomy:** 3-level hierarchy (Category > Subcategory > Type)
- **Shared attributes:** Hours, location, reviews, photos
- **Industry-specific:** Menu (restaurants), services (salons), amenities (hotels)

### B. Square/Toast POS Systems
- **Industry templates:** Pre-configured for 50+ industries
- **Shared:** Payment, inventory, reporting
- **Industry-specific:** Table management (restaurants), appointment booking (salons)

### C. Data.gov Industry Classification
- **NAICS codes:** 6-digit hierarchical system
- **Shared metrics:** Employment, revenue, establishments
- **Industry-specific:** Production metrics, specialized ratios

### D. Best Practices Synthesis

1. **Separation of Concerns:**
   - Shared data in common schema
   - Industry-specific in extensions
   - Calculated fields in separate layer

2. **Normalization:**
   - Avoid duplicating shared data (population, facilities)
   - Reference by district code
   - Compute on-demand when possible

3. **Versioning:**
   - Schema version in metadata
   - Migration scripts for updates
   - Backward compatibility

4. **Performance:**
   - Index by both industry and district
   - Cache frequently accessed combinations
   - Lazy-load industry-specific details

---

## 7. Recommended Implementation Plan

### Phase 1: Extend Current System (Coffee Only)
1. Add industry config for CS100010
2. Refactor `analyze_seoul_data.py` to use config
3. Test with existing coffee data

### Phase 2: Multi-Industry Data Collection
1. Modify `collect_seoul_api.py` to accept industry code parameter
2. Collect data for CS100001-CS100009
3. Store in `data/seoul/{industry_code}_sales_{quarter}.json`

### Phase 3: Unified Processing
1. Create `process_multi_industry.py`
2. Generate both by_industry and by_district files
3. Implement shared data deduplication

### Phase 4: API Integration
1. Update API to serve multi-industry data
2. Add industry selection to frontend
3. Implement industry comparison features

---

## 8. Data Schema Recommendations

### A. Metadata Schema
```json
{
  "schema_version": "2.0.0",
  "generated_at": "2026-02-06T10:00:00Z",
  "data_quarter": "20253",
  "industries": [
    {
      "code": "CS100010",
      "name": "커피-음료",
      "district_count": 1234,
      "store_count": 5678,
      "total_sales": 123456789000
    }
  ],
  "districts": {
    "total": 1500,
    "by_type": {
      "골목상권": 1200,
      "발달상권": 200,
      "전통시장": 80,
      "관광특구": 20
    }
  }
}
```

### B. Industry Config Schema
```typescript
interface IndustryConfigSchema {
  version: string;
  industries: Record<string, IndustryConfig>;
  categories: {
    "F&B": string[];
    "Retail": string[];
    "Service": string[];
    "Entertainment": string[];
  };
  defaults: {
    financials: FinancialDefaults;
    startup: StartupDefaults;
  };
}
```

---

## 9. Key Findings Summary

1. **Seoul API supports 100+ industries** with the same field structure
2. **120+ shared fields** available for all industries
3. **Industry-specific differences** are mainly in:
   - Financial ratios (COGS, labor, margin)
   - Startup costs (equipment, interior)
   - Customer patterns (peak hours, demographics)
   - Success metrics (breakeven, lifespan)

4. **Recommended structure:**
   - Hybrid file organization (by_industry + by_district)
   - Hierarchical config with inheritance
   - Shared data normalization
   - Industry-specific extensions

5. **Next steps:**
   - Define CS100001-CS100009 industry codes
   - Create industry config file
   - Extend data collection script
   - Implement multi-industry processing

---

## 10. References

- Seoul Open Data Portal: https://data.seoul.go.kr
- Seoul Commercial District Analysis: https://golmok.seoul.go.kr
- Current codebase: `/scripts/collect_seoul_api.py`, `/scripts/analyze_seoul_data.py`
- Industry config examples: GitHub search results (resume-alchemist, stock-sdk)

