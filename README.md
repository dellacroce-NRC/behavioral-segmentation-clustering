# Behavioral-Driven Product Strategy  
### Flywheel Optimization via K-Means Clustering

## 🚀 Executive Summary

In the PropTech industry, **retention is the engine of profitability**.  
This project documents the strategic transition of **BauData (Chile)** from a traditional sales funnel to a **Flywheel Model**, integrating **Behavioral Science** and **Machine Learning** to operationalize growth.

The central objective was to diagnose why **67.92% of user sessions** ended in *friction zones* despite a robust data offering, and to propose a strategy based on aligning **User Intent** with **Product Value**.

## 📈 Strategic Business Impact

- **Growth Evolution:**  
  Reframed the product strategy toward the *Delight* phase, positioning existing user commitment as the primary driver of organic acquisition.

- **Retention Roadmap:**  
  Identified precise drop-off points across the user journey, enabling the prioritization of UX iterations with direct impact on **LTV (Lifetime Value)** and churn reduction.

- **Evidence-Based Decisions:**  
  Shifted development from intuition-led choices to telemetry-driven strategy, reducing the risk of investing in low-impact features.

## 🧠 Behavioral Science & UX Audit (External Analysis)

From a behavioral analysis perspective, I identified critical psychological gaps in the user's *First Mile* experience:

- **Intent Misalignment:**  
  The landing experience functioned as a monolithic funnel, failing to distinguish between technical users seeking raw data and commercial users seeking demonstrations.

- **Cognitive Overload:**  
  High information density induced decision paralysis. I proposed a **modular information architecture** aligned with search intent (Informational vs. Transactional).

- **Anchor Bias:**  
  Analyzed how initial search exposure conditioned users’ perceived value of the platform.

## 🛠️ Technical Implementation: Telemetry & Machine Learning

The project transformed raw telemetry from **PostHog** into actionable behavioral segments through a structured data pipeline.

### 1. Data Wrangling & QA (The “80%” of the Work)

- **Real-World Cleaning:**  
  Resolved critical inconsistencies in time formats (ISO8601 vs UTC) and implemented precise event-to-session matching logic.

- **Integrity Check:**  
  Validated **1,623 unique events** to ensure that *real duration* reflected active interaction rather than idle background time.

- **Feature Engineering:**  
  Defined five behavioral markers:  
  `marker_select_count`, `search_filter_select_count`, `page_view_count`, `download_flag`, and `real_duration`.

### 2. Machine Learning (K-Means Clustering)

- **Session Modeling:**  
  Implemented a clustering model *(k = 3)* to separate behavioral noise from genuine intent, analyzing **106 real user sessions**.

- **The “Open Tab” Problem:**  
  Designed a heuristic to detect long-duration sessions with low interaction, revealing navigation friction or *tab abandonment* rather than authentic engagement.

### 3. Intelligence Layer (Power BI & DAX)

- **Behavioral Segmentation:**  
  Visualized cluster behavior and session archetypes to support product and UX decision-making.

- **Exploratory Metrics:**  
  Enabled dynamic slicing by session type, interaction depth, and duration to surface friction patterns.

## 📊 Session Archetypes (Model Results)

- **Power Users (14.15%)**  
  High-value core users who overcome initial barriers and extract deep insights.

- **Targeted Searchers (16.98%)**  
  High-efficiency transactional users who enter for a specific data point and exit quickly.

- **Friction Zone (67.92%)**  
  Long-duration, low-interaction sessions indicating users effectively *trapped* in an interface that does not immediately facilitate their intent.

## 📂 Project Assets

- **Full Case Study (PDF):** `Optimizing_Product-Led_Growth_BauData.pdf`  
- **Interactive Dashboard:** `BauData_Behavioral_Strategy.pbix`  
- **Modeling Notebook:** Full pipeline from raw JSON telemetry to cluster assignment.

## 🧑‍💼 Role & Tooling

**Role:** Product & Behavioral Data Analyst  
**Tools:** Python (scikit-learn, pandas), PostHog Telemetry, SQL, Power BI (DAX)
