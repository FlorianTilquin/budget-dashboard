# Personal Budget Dashboard

A comprehensive budget dashboard built with Python and Plotly Dash that helps you visualize and analyze your personal finances.

## Features

- **File Upload**: Easily upload your bank's OFX or OFC files through the user interface
- **Account Balance Visualization**: View your account balance trend over time
- **Spending Categories**: Analyze where your money is going with pie charts and bar graphs
- **Transaction History**: Browse through your transaction history with filtering capabilities
- **Time Period Selection**: Filter data by predefined periods or custom date ranges

## Screenshots

(Screenshots of the dashboard will appear here once you run the application)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd budget-dashboard
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the dashboard:
   ```
   python app.py
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

## Automatic Categorization

The dashboard automatically categorizes your transactions based on common patterns in the transaction descriptions. The categories include:

- Groceries
- Dining
- Transportation
- Shopping
- Entertainment
- Health
- Utilities
- Housing
- Income
- Transfer
- Other

The categorization is not perfect but provides a good starting point for analyzing your spending patterns.

## Privacy & Security

This dashboard runs locally on your machine. Your financial data is processed within your browser and is not sent to any external servers.

## License

MIT License 