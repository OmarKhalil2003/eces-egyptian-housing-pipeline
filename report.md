# Egyptian Housing Market Research Analysis: Empirical Pricing Premiums, Installment Structures, and Compound Valuation

**Scope**: 12 Governorates across Sale and Rental markets within the collected Bayut sample  
**Dataset Source**: Bayut Egypt ($N = 560$ residential records, $280$ for-sale, $280$ for-rent)  
**Analysis Sample**: Filtered for-sale properties with valid price and surface area ($n = 280$, $148$ compound, $132$ standalone)

---

## 1. Executive Summary & Core Research Questions

A central empirical question in Egyptian housing economics is:  
> *“What empirical price-per-square-meter premium is observed in master-planned compound units relative to standalone housing within this listing sample, and how are long-term developer installment schedules distributed across major markets?”*

Using the normalized dataset parsed from Bayut Egypt, this report tests empirical hypotheses regarding pricing premiums, geographical stratification, and financing distributions. All metrics are computed programmatically from `data/output/analysis_metrics.json`.

---

## 2. Empirical Findings

### Finding 1: The Master-Planned Compound Price Premium (+46.7%)
Does location inside a branded compound exhibit a measurable price-per-square-meter premium over adjacent standalone residential units within this sample?

* **Sample Distribution**: Among for-sale listings with verified price and surface area ($n = 280$):
  * **Inside Compound ($n = 148$)**: Median = **68,065 EGP/m²** (mean: **73,832 EGP/m²**, IQR: **49,659 – 91,194 EGP/m²**).
  * **Standalone / Non-Compound ($n = 132$)**: Median = **46,386 EGP/m²** (mean: **59,926 EGP/m²**, IQR: **30,480 – 81,417 EGP/m²**).
  * **Observed Median Premium**: **+46.7%** (+21,679 EGP/m²).
* **Statistical Significance**:
  * **Mann-Whitney U Test**: $U = 12,278.5$, $p = 0.000206$ ($p < 0.001$), confirming a statistically significant difference in rank distributions between compound and standalone listings.
  * **Bootstrap 95% Confidence Interval for Median Difference** (2,000 iterations): **[+6,291 EGP/m², +31,381 EGP/m²]**.

| Property Category | Sample ($n$) | Median Price/m² (EGP) | Mean Price/m² (EGP) | Interquartile Range (IQR) |
| :--- | :---: | :---: | :---: | :---: |
| **Inside Compound** | 148 | **68,065** | 73,832 | 49,659 – 91,194 |
| **Standalone / Non-Compound** | 132 | **46,386** | 59,926 | 30,480 – 81,417 |
| **Difference / Premium** | — | **+46.7%** | **+23.2%** | **p = 0.000206** |

---

### Finding 2: Cross-Governorate Listing Price Dispersion
How does listing price per square meter vary across major Egyptian markets within this sample?

* **Primary Regional Markets ($n \ge 10$)**:
  1. **Matruh / North Coast ($n = 89$)**: Median of **88,539 EGP/m²** (mean: **94,714 EGP/m²**), associated with the luxury coastal resort inventory represented in this sample (Ras El Hikma, Sidi Abdel Rahman).
  2. **Suez / Ain Sukhna ($n = 10$)**: Median of **54,948 EGP/m²** (mean: **67,152 EGP/m²**).
  3. **Cairo ($n = 134$)**: Median of **50,000 EGP/m²** (mean: **57,091 EGP/m²**), representing New Cairo, Madinaty, and Shorouk.
  4. **Giza ($n = 31$)**: Median of **41,758 EGP/m²** (mean: **42,022 EGP/m²**), centered in 6th of October and Sheikh Zayed.
* **Low-Sample Governorates ($n < 10$, descriptive only — cannot be generalized)**:
  * *Red Sea ($n=6$)*: Sample median **81,469 EGP/m²**.
  * *Alexandria ($n=5$)*: Sample median **27,500 EGP/m²**.
  * *Sinai ($n=1$)*: **57,732 EGP/m²** | *Dakahlia ($n=1$)*: **24,558 EGP/m²** | *Sharqia ($n=1$)*: **21,177 EGP/m²** | *Qalyubia ($n=1$)*: **6,500 EGP/m²** | *Kafr al-Sheikh ($n=1$)*: **1,294 EGP/m²**.

---

### Finding 3: Financing Structures & Installment Horizons
How are listings advertising long-term installment schedules within this sample?

* **Installment Horizon Concentration**: Among listings with explicit installment durations ($n = 35$), **10-year and 12-year payment plans account for 57.1% of all financing offerings** (20 listings).
* **Cash Discount Distribution**: Across listings explicitly advertising cash discounts ($n = 24$), the mean advertised discount is **36.6%** (ranging from **24.0%** to **54.0%**), reflecting the substantial spread between immediate cash settlements and multi-year deferred payment plans.

| Installment Duration | Listing Count ($n$) | Share of Financing Listings (%) | Common Down Payment Range |
| :--- | :---: | :---: | :---: |
| **10 – 12 Years** | 20 | **57.1%** | 5.0% – 10.0% |
| **7 – 9 Years** | 5 | **14.3%** | 5.0% – 10.0% |
| **4 – 6 Years** | 6 | **17.1%** | 10.0% – 20.0% |
| **> 12 Years** | 4 | **11.4%** | 5.0% – 10.0% |

---

### Finding 4: Finishing Level Price Dispersion (For-Sale Segment)
* **Furnished Units ($n = 36$)**: Median price of **74,008 EGP/m²** (mean: **78,530 EGP/m²**).
* **Super Lux ($n = 70$)**: Median price of **71,017 EGP/m²** (mean: **75,246 EGP/m²**).
* **Fully Finished ($n = 30$)**: Median price of **51,094 EGP/m²** (mean: **63,199 EGP/m²**).
* *Rental Note*: In the rental segment, median monthly rent per square meter for furnished units is **342.7 EGP/m²/month** compared to **384.6 EGP/m²/month** for unfurnished units within this specific sampled subset.

---

## 3. Methodological Integrity & Limitations

1. **Deterministic Null Handling**: Fields not explicitly stated in the listing text or structured payload were retained strictly as `null`. No synthetic data imputation was performed.
2. **Sample Specificity**: All reported statistics describe this cross-section of 560 Bayut listings. Small-sample governorates ($n < 10$) are highlighted to prevent unwarranted generalization.
3. **Unified Metric Source**: All reported statistics are generated reproducibly by `python -m src.generate_report_data` and exported to `data/output/analysis_metrics.json`.
4. **Extraction Quality Audit**: Extraction accuracy was benchmarked on 25 hand-labeled ground-truth records (62.5% accuracy, 8.9% hallucination rate). False positives were audited and traced to spatial taxonomy granularity and gold set edge cases rather than ungrounded fabrication (documented in `README.md` § 5).
