#!/usr/bin/env python3
"""
Entry point for the Budget Dashboard application.
"""
from budget_dashboard.app import app

if __name__ == '__main__':
    app.run_server(debug=True) 