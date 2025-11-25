# Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

# Nifty 50 Real-Time Greeks Engine 🚀

## Overview
A high-frequency **ELT (Extract, Load, Transform)** pipeline that captures real-time derivatives data from the National Stock Exchange (NSE), calculates quantitative metrics (The Greeks, IV), and visualizes Dealer Gamma Exposure in real-time.

Designed to overcome NSE's anti-bot protections, this system provides institutional-grade analytics (Volatility Smiles, Max Pain) for retail traders.

![Status](https://img.shields.io/badge/Status-Production-green)
![Python](https://img.shields.io/badge/Python-3.9-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)

## ⚠️ Disclaimer: Educational Project Only
This project is a **Proof of Concept (PoC)** designed for educational and research purposes to demonstrate modern Data Engineering architecture (ELT, Vectorization, Containerization).

It interacts with public endpoints. It is **not intended for commercial use**, trading advice, or large-scale data redistribution. In a production enterprise environment, the ingestion layer would be replaced with an authorized API vendor (e.g., Bloomberg, Refinitiv, or NSE Official API).

## 🏗 Architecture
The system follows a decoupled **Microservices Architecture** containerized via Docker:

1.  **Ingestion Service (Python):** * Mimics human browser behavior (Session rotation, User-Agent spoofing) to bypass NSE 403 blocks.
    * Performs **Vectorized Calculations** (NumPy) to compute Black-Scholes Greeks for 150+ option contracts in <200ms.
2.  **Storage Layer (PostgreSQL):** * Stores historical snapshots of the Option Chain.
    * Optimized for time-series queries to track Open Interest change.
3.  **Visualization Layer (Streamlit):**
    * Connects to the Data Warehouse to render "Gamma Exposure" heatmaps and Volatility Skew charts.

## 🛠 Tech Stack
* **Language:** Python 3.11 (Pandas, NumPy, Requests, SQLAlchemy)
* **Quant Libs:** `py_vollib_vectorized` (for high-speed Black-Scholes pricing)
* **Database:** PostgreSQL 15 (Dockerized)
* **Visualization:** Streamlit, Plotly Express
* **Infrastructure:** Docker, Docker Compose

## ⚡ Key Features & Engineering Challenges

### 1. Fault Tolerance & Reliability
* **Self-Healing Containers:** Implemented `restart: always` policies in Docker to ensure the pipeline automatically recovers from network disconnects or API timeouts.
* **Data Integrity:** The ETL script validates JSON schema structure before ingestion. "Below Intrinsic" warnings from illiquid strikes are logged but filtered to prevent pipeline crashes.

### 2. The "Stealth" Ingestion
NSE aggressively blocks non-browser traffic. I engineered a session management logic that:
* Initializes a valid session by visiting the homepage first (Cookie Hydration).
* Rotates Request Headers to mimic a Chrome browser on Windows.
* Implements randomized jitter (wait times) to avoid pattern detection.

### 3. Quantitative Performance
* **Vectorization over Loops:** Instead of iterating through 150 strikes using Python loops (O(n)), I used `numpy` vectorization to calculate Delta/Gamma for the entire chain in a single CPU operation, reducing processing time by ~90%.

## 🚀 How to Run

### Prerequisites
* Docker Desktop installed.

### Steps
1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/yourusername/nifty-greeks-engine.git](https://github.com/yourusername/nifty-greeks-engine.git)
    cd nifty-greeks-engine
    ```

2.  **Start the Infrastructure**
    ```bash
    docker-compose up -d
    ```

3.  **Run the ETL (Data Ingestion)**
    *Currently running as a standalone script for demonstration:*
    ```bash
    python etl.py
    ```

4.  **Launch the Dashboard**
    ```bash
    streamlit run dashboard.py
    ```
    *Access the dashboard at `http://localhost:8501`*

 ## Architecture Diagram
   <img width="1197" height="526" alt="architecture diagram" src="https://github.com/user-attachments/assets/bb480786-8b85-40a7-ac33-6b803d67ac1f" />



## 📊 Sample Visuals

### 1. Net Gamma Exposure (Market Maker Positioning)
*Visualizes where Dealers a<img width="1877" height="810" alt="GEX SS" src="https://github.com/user-attachments/assets/5a8faaeb-e779-4c97-b9be-bacd8e1071b5" />
re Long/Short Gamma, predicting market volatility.*



### 2. Volatility Smile
*Real-time skew of Implied Volatility across strike prices.*
<img width="1878" height="822" alt="IV SS" src="https://github.com/user-attachments/assets/dd022cb4-d53b-4253-aca0-e2e45bac8271" />



### 3. Open Interest
* Open interest indicates the total number of outstanding or active futures and options contracts for a given asset
<img width="1877" height="848" alt="OI SS" src="https://github.com/user-attachments/assets/0c38c8b2-c8e4-476a-9a59-f8b77b78cf3f" />


