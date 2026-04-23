ProcureLink
ProcureLink is a campus procurement intelligence tool designed for University. It automates price benchmarking for office supplies and IT hardware by scraping Geizhals.de, providing procurement teams with data-driven insights through an interactive dashboard.

🚀 Quick Start
Bash
# Install dependencies
pip install -r requirements.txt

# Run the crawler to update price data
python crawler.py

# Launch the local preview server
python serve.py
📂 File Structure
Plaintext
procurelink/

├── .github/workflows/
│   └── crawl.yml          # GitHub Actions: Automated weekly price updates
│
├── crawler.py             # Core Scraper: Python logic for data acquisition
│
├── data.json              # Data Store: Structured results in JSON format
│
├── index.html             # Dashboard: Chart.js visualization interface
│
├── serve.py               # Utility: Local development server
│
└── requirements.txt       # Dependencies: List of required Python packages
⚙️ Automation & Deployment
GitHub Actions: The workflow is configured to run every Monday at 08:00 (Berlin Time). It scrapes the latest prices and automatically commits changes back to the repository.

GitHub Pages: The project is designed to be hosted directly via GitHub Pages. Since it uses a "Git-as-a-DB" architecture, no external database or backend server is required.
