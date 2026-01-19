# behavioral-segmentation-clustering
User behavioral segmentation using K-Means clustering and PostHog telemetry to drive product retention strategies.
Data-Driven Product Strategy: Implementing the Flywheel Model at BauData

🚀 Executive Summary
This project outlines a strategic transition from a traditional sales funnel to a Flywheel Model for BauData, a leading PropTech platform in Chile. By integrating Behavioral Science and Machine Learning, I developed a system to reduce user friction, optimize retention, and drive organic growth through data-backed insights.

🧠 Behavioral Analysis & UX Optimization
Beyond the code, this project involved a deep dive into user psychology:

Cognitive Bias Audit: Identified friction points in the onboarding flow related to Choice Overload and Anchor Bias.

Conversion Optimization: Proposed a redesign of the landing page's Information Architecture to align with user search intent (Informational, Commercial, and Transactional).

🛠️ Technical Implementation (The "Deleite" Phase)
Using telemetry data from PostHog, I built a clustering model to segment users based on their actual platform interaction:

Scale: Analyzed 106 sessions from 30 unique users (averaging 3.5 sessions per user).

Depth: Average session duration was recorded at 30:24 minutes, indicating high information value but potential navigation complexity.

Modeling: Applied K-Means Clustering to separate "noise" from intent.

📈 Business Insights: User Archetypes
The model identified three critical segments for the product roadmap:

Power Users (14.15%): Highly engaged users with deep interaction across all modules (avg. 409 seconds in high-value sessions).

Buscador Puntual (16.98%): Efficient users who interact only with necessary filters. Target for feature discovery.

Rebote / Fricción (67.92%): Users with high duration but low interaction, likely due to "open tabs" or cognitive friction in the UI.
