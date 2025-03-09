# Personal Budget Dashboard

A comprehensive budget dashboard built with Python and Plotly Dash that helps you visualize and analyze your personal finances.

## Features

- **File Upload**: Easily upload your bank's OFX or OFC files through the user interface
- **Account Balance Visualization**: View your account balance trend over time
- **Spending Categories**: Analyze where your money is going with pie charts and bar graphs
- **Transaction Management**: Browse through your transaction history with filtering capabilities and manual category editing
- **Time Period Selection**: Filter data by predefined periods or custom date ranges
- **Data Persistence**: Save your transactions with custom categories as parquet files and reload them later

## Project Structure

```
budget-dashboard/
├── budget_dashboard/        # Main Python package
│   ├── __init__.py
│   ├── app.py               # Dash application
│   ├── static/              # Static files (CSS, JS, images)
│   ├── templates/           # HTML templates
│   └── parsers/             # File parsers
│       ├── __init__.py
│       └── ofx_parser.py    # OFX/OFC and parquet file parser
├── run.py                   # Entry point script
├── setup.sh                 # Setup script
├── requirements.lock
├── pyproject.toml
└── README.md
```

## Screenshots

(Screenshots of the dashboard will appear here once you run the application)

## Installation

### Quick Setup

For Unix/macOS users, you can use the provided setup script which will:
1. Install uv if not already installed
2. Create a virtual environment
3. Install the dependencies
4. Run the application

```bash
# Make the script executable if needed
chmod +x setup.sh

# Run the setup script
./setup.sh
```

### Manual Setup

#### Prerequisites

This project uses `uv`, a fast Python package installer and resolver. If you don't have it installed:

```bash
# Install uv using pip
pip install uv

# Or install with pipx for isolated installation
pipx install uv
```

#### Setting up the project

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd budget-dashboard
   ```

2. Create a virtual environment and install dependencies with uv:
   ```bash
   # Create a virtual environment
   uv venv

   # Activate the environment
   # On Unix/macOS:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate

   # Install dependencies
   uv pip install -e .
   ```

   Or, to install in one step:
   ```bash
   uv pip sync
   ```

3. For development, install development dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

## Usage

1. Run the dashboard:
   ```bash
   ./run.py
   ```
   
   Or alternatively:
   ```bash
   python run.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8050/
   ```

3. Upload your bank's OFX or OFC files using the upload area in the dashboard.

4. Use the time period selector to filter the data by date range.

5. Navigate between the different tabs to view various visualizations and reports.

## About Financial Data Files

### OFX (Open Financial Exchange)
OFX is a data-stream format for exchanging financial information. Many banks allow you to download your transaction data in OFX format. Check your bank's website for this option, usually found in the account statement or transaction history section.

### OFC (Open Financial Connectivity)
OFC is an older format similar to OFX, used by some financial institutions. The dashboard supports both formats.

### Parquet Files
Parquet is a columnar storage format that is highly efficient for analytics workloads. The dashboard allows you to:
- Save your transactions (including your manual category adjustments) as parquet files
- Load these parquet files later, preserving all your customizations
- Share your categorized transaction data across devices or with others

## Automatic and Manual Categorization

The dashboard provides two ways to categorize your transactions:

1. **Automatic Categorization**: Transactions are automatically categorized based on common patterns in the transaction descriptions.

2. **Manual Categorization**: You can manually override the automatic categories using dropdown menus in the Transactions tab.

The categories include:

- Courses
- Restaurants
- Transport
- Shopping
- Seconde Main
- Loisirs
- Sante
- Services
- Logement
- Revenus
- Virements
- Voiture
- Banque
- Maison
- Autre

After changing categories, click the "Refresh Charts" button to update the visualizations.

## Privacy & Security

This dashboard runs locally on your machine. Your financial data is processed within your browser and is not sent to any external servers.

## License

MIT License 