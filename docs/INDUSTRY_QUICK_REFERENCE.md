# Industry Configuration Quick Reference

**Last Updated:** February 6, 2026

---

## Seoul API Field Mapping

### Core Fields (All Industries)

| Field Category | Count | Examples |
|----------------|-------|----------|
| Basic Info | 7 | `TRDAR_CD`, `SVC_INDUTY_CD`, `STDR_YYQU_CD` |
| Sales (Amount) | 28 | `THSMON_SELNG_AMT`, `MON_SELNG_AMT`, `TMZON_11_14_SELNG_AMT` |
| Sales (Count) | 28 | `THSMON_SELNG_CO`, `MON_SELNG_CO`, `TMZON_11_14_SELNG_CO` |
| Store Status | 7 | `STOR_CO`, `OPBIZ_STOR_CO`, `CLSBIZ_STOR_CO`, `FRC_STOR_CO` |
| Population | 27 | `TOT_WRC_POPLTN_CO`, `TOT_REPOP_CO`, `TOT_FLPOP_CO` |
| Facilities | 16 | `SUBWAY_STATN_CO`, `BANK_CO`, `UNIV_CO` |
| Households | 4 | `TOT_HSHLD_CO`, `APT_HSHLD_CO` |
| Change Indicators | 3 | `TRDAR_CHNGE_IX_CD`, `OPR_SALE_MT_AVRG` |
| **Total** | **120+** | |

---

## Industry Code Mapping (Hypothetical)

| Code | Korean Name | English Name | Category |
|------|-------------|--------------|----------|
| CS100001 | 한식음식점 | Korean Restaurant | F&B |
| CS100002 | 중식음식점 | Chinese Restaurant | F&B |
| CS100003 | 일식음식점 | Japanese Restaurant | F&B |
| CS100004 | 서양음식점 | Western Restaurant | F&B |
| CS100005 | 패스트푸드 | Fast Food | F&B |
| CS100006 | 치킨전문점 | Chicken Restaurant | F&B |
| CS100007 | 분식전문점 | Snack Bar | F&B |
| CS100008 | 제과점 | Bakery | F&B |
| CS100009 | 호프/간이주점 | Bar/Pub | F&B |
| CS100010 | 커피-음료 | Coffee/Beverage | F&B |

*Note: Codes CS100001-CS100009 are hypothetical. Verify with actual Seoul API documentation.*

---

## Financial Benchmarks by Industry

### F&B Industries

```
Coffee Shop (CS100010)
├─ COGS: 30%
├─ Labor: 25%
├─ Rent: 15%
├─ Utilities: 5%
├─ Other: 10%
└─ Net Margin: 15%

Korean Restaurant (CS100001)
├─ COGS: 35%
├─ Labor: 30%
├─ Rent: 12%
├─ Utilities: 8%
├─ Other: 5%
└─ Net Margin: 10%

Fast Food (CS100005)
├─ COGS: 28%
├─ Labor: 28%
├─ Rent: 10%
├─ Utilities: 6%
├─ Other: 16%
└─ Net Margin: 12%

Bakery (CS100008)
├─ COGS: 32%
├─ Labor: 22%
├─ Rent: 13%
├─ Utilities: 7%
├─ Other: 12%
└─ Net Margin: 14%
```

---

## Startup Cost Ranges (KRW)

| Industry | Equipment | Interior | Deposit | Initial Inventory | Total Range |
|----------|-----------|----------|---------|-------------------|-------------|
| Coffee Shop | 15M - 50M | 20M - 80M | 10-12 months | 2M - 5M | 50M - 150M |
| Korean Restaurant | 30M - 100M | 30M - 120M | 10-12 months | 5M - 15M | 80M - 300M |
| Fast Food | 40M - 120M | 25M - 100M | 6-10 months | 3M - 10M | 80M - 250M |
| Bakery | 50M - 150M | 30M - 100M | 10-12 months | 5M - 12M | 100M - 350M |

---

## Peak Hours by Industry

```
Coffee Shop:     ████████░░░░░░░░░░░░░░░░
                 06   11   14   17   21   24

Korean Restaurant: ░░░░████░░░░░░░░████░░░░
                   06   11   14   17   21   24

Fast Food:       ░░░░████░░░░░░░░████░░░░
                 06   11   14   17   21   24

Bar/Pub:         ░░░░░░░░░░░░░░░░░░░░████
                 06   11   14   17   21   24
```

---

## Customer Demographics by Industry

### Coffee Shop
- **Primary:** 20s-40s (80%)
- **Gender:** Female-leaning (55-60%)
- **Peak Days:** Weekdays
- **Seasonality:** Low

### Korean Restaurant
- **Primary:** 30s-50s (70%)
- **Gender:** Balanced
- **Peak Days:** Weekends
- **Seasonality:** Medium

### Fast Food
- **Primary:** All ages
- **Gender:** Balanced
- **Peak Days:** Weekends
- **Seasonality:** Low

### Bakery
- **Primary:** 20s-50s (75%)
- **Gender:** Female-leaning (60-65%)
- **Peak Days:** Weekends
- **Seasonality:** Medium

---

## Success Metrics by Industry

| Industry | Min Monthly Revenue | Target Revenue | Breakeven (months) | Avg Lifespan (months) |
|----------|---------------------|----------------|--------------------|-----------------------|
| Coffee Shop | 8M | 20M | 18 | 36 |
| Korean Restaurant | 15M | 40M | 24 | 30 |
| Fast Food | 12M | 30M | 20 | 42 |
| Bakery | 10M | 25M | 22 | 38 |

---

## File Structure Templates

### Option 1: Industry-First (Recommended for API)
```
data/processed/by_industry/
├── CS100010.json          # 1.2MB - All coffee districts
├── CS100001.json          # 1.5MB - All korean food districts
└── ...

Pros: Fast industry-wide queries, easy to cache
Cons: Slow for single-district multi-industry queries
```

### Option 2: District-First (Recommended for UI)
```
data/processed/by_district/
├── 3110002.json           # 15KB - All industries for district
├── 3110003.json
└── ...

Pros: Fast single-district queries, smaller files
Cons: Slow for industry-wide analysis
```

### Option 3: Hybrid (Recommended)
```
data/processed/
├── by_industry/           # For analytics, reports
│   ├── CS100010.json
│   └── ...
├── by_district/           # For UI, user queries
│   ├── 3110002.json
│   └── ...
└── summary/               # For dashboards
    ├── industry_summary.json
    └── district_summary.json
```

---

## API Endpoint Design

### Multi-Industry Endpoints

```typescript
// Get all industries for a district
GET /api/v1/districts/{district_code}
Response: {
  district_code: "3110002",
  industries: {
    "CS100010": { ... },
    "CS100001": { ... }
  }
}

// Get all districts for an industry
GET /api/v1/industries/{industry_code}
Response: {
  industry_code: "CS100010",
  districts: [ ... ]
}

// Get specific industry in specific district
GET /api/v1/districts/{district_code}/industries/{industry_code}
Response: { ... }

// Compare industries in a district
GET /api/v1/districts/{district_code}/compare?industries=CS100010,CS100001
Response: {
  comparison: [ ... ]
}
```

---

## Configuration File Template

```typescript
// config/industries/CS100010.ts
export default {
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
    avgCOGS: 0.30,
    avgLaborCost: 0.25,
    avgRentRatio: 0.15,
    avgUtilities: 0.05,
    avgMargin: 0.15
  },
  
  startup: {
    equipmentMin: 15_000_000,
    equipmentMax: 50_000_000,
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
};
```

---

## Data Collection Script Template

```python
# scripts/collect_multi_industry.py

INDUSTRY_CODES = [
    "CS100001",  # Korean Restaurant
    "CS100002",  # Chinese Restaurant
    # ... add more
    "CS100010",  # Coffee Shop
]

def collect_industry(industry_code: str, quarter: str):
    """Collect data for one industry"""
    sales_data = collect_quarter(
        "VwsmTrdarSelngQq", 
        quarter, 
        industry_code
    )
    stores_data = collect_quarter(
        "VwsmTrdarStorQq", 
        quarter, 
        industry_code
    )
    return sales_data, stores_data

def main():
    for industry_code in INDUSTRY_CODES:
        print(f"Collecting {industry_code}...")
        sales, stores = collect_industry(industry_code, "20253")
        
        # Save by industry
        save_json(
            f"data/seoul/{industry_code}_sales_20253.json",
            sales
        )
        save_json(
            f"data/seoul/{industry_code}_stores_20253.json",
            stores
        )
```

---

## Processing Script Template

```python
# scripts/process_multi_industry.py

def process_all_industries():
    """Process all industries and generate both views"""
    
    # Load all industry data
    all_data = {}
    for industry_code in INDUSTRY_CODES:
        all_data[industry_code] = load_industry_data(industry_code)
    
    # Generate by_industry files
    for industry_code, data in all_data.items():
        districts = process_industry(industry_code, data)
        save_json(
            f"data/processed/by_industry/{industry_code}.json",
            {
                "industry_code": industry_code,
                "districts": districts
            }
        )
    
    # Generate by_district files
    district_map = defaultdict(dict)
    for industry_code, data in all_data.items():
        for district in data['districts']:
            district_code = district['district_code']
            district_map[district_code][industry_code] = district
    
    for district_code, industries in district_map.items():
        save_json(
            f"data/processed/by_district/{district_code}.json",
            {
                "district_code": district_code,
                "industries": industries
            }
        )
```

---

## Next Steps Checklist

- [ ] Verify actual industry codes from Seoul API
- [ ] Create `config/industries/` directory
- [ ] Implement industry config files (CS100001-CS100010)
- [ ] Modify `collect_seoul_api.py` for multi-industry
- [ ] Create `process_multi_industry.py`
- [ ] Update API endpoints for multi-industry
- [ ] Add industry selector to frontend
- [ ] Implement industry comparison features
- [ ] Add industry-specific simulation parameters
- [ ] Update documentation

---

## Common Pitfalls to Avoid

1. **Don't duplicate shared data** (population, facilities) across industries
2. **Don't hardcode industry codes** - use config files
3. **Don't mix industry-specific and shared fields** in the same object
4. **Don't forget to normalize** financial ratios (0-1 vs 0-100)
5. **Don't assume all industries have data** for all districts
6. **Don't skip validation** of industry codes before API calls
7. **Don't forget to handle** missing/null values in calculations
8. **Don't ignore** API rate limits when collecting multiple industries

---

## Performance Optimization Tips

1. **Cache frequently accessed combinations** (popular districts × industries)
2. **Use lazy loading** for industry-specific details
3. **Implement pagination** for large district lists
4. **Pre-compute** common aggregations (averages, totals)
5. **Use CDN** for static industry config files
6. **Index by both** industry and district codes
7. **Compress** large JSON files (gzip)
8. **Implement** incremental updates (only changed data)

