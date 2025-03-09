import pandas as pd
import numpy as np
from ofxparse import OfxParser
from io import BytesIO
import datetime
import re

def parse_ofx(contents, filename):
    """
    Parse an OFX file and return a DataFrame with transaction data.
    
    Args:
        contents (bytes): The contents of the OFX file
        filename (str): The name of the file
        
    Returns:
        pandas.DataFrame: DataFrame containing transaction data
    """
    try:
        # Parse the OFX file
        ofx = OfxParser.parse(BytesIO(contents))
        
        # Get the account
        account = ofx.accounts[0]
        
        # Extract transactions
        transactions = []
        for transaction in account.statement.transactions:
            transactions.append({
                'date': transaction.date,
                'amount': float(transaction.amount),  # Convert to float
                'description': transaction.memo if transaction.memo else transaction.payee,
                'type': transaction.type,
                'category': categorize_transaction(transaction.memo if transaction.memo else transaction.payee)
            })
        
        # Create a DataFrame
        df = pd.DataFrame(transactions)
        
        # Add account information
        df['account_id'] = account.account_id
        df['account_type'] = account.account_type
        df['balance'] = float(account.statement.balance)  # Convert to float
        df['currency'] = account.statement.currency if hasattr(account.statement, 'currency') else 'EUR'
        
        return df
    
    except Exception as e:
        print(f"Error parsing OFX file: {e}")
        return pd.DataFrame()

def parse_ofc(contents, filename):
    """
    Parse an OFC file and return a DataFrame with transaction data.
    
    Args:
        contents (bytes): The contents of the OFC file
        filename (str): The name of the file
        
    Returns:
        pandas.DataFrame: DataFrame containing transaction data
    """
    # OFC is similar to OFX, attempt to parse with OFX parser first
    try:
        return parse_ofx(contents, filename)
    except Exception as e:
        print(f"Error parsing OFC file using OFX parser: {e}")
        # If OFX parser fails, implement custom OFC parsing logic here
        # This is a placeholder - actual implementation would depend on the OFC format
        print("OFC format not fully supported yet")
        return pd.DataFrame()

def categorize_transaction(description):
    """
    Automatically categorize a transaction based on its description.
    
    Args:
        description (str): The transaction description or memo
        
    Returns:
        str: The category of the transaction
    """
    description = description.lower()
    
    # Define category patterns
    categories = {
        'Courses': ['carrefour', 'carreefour', 'lidl', 'aldi', 'monoprix', 'leclerc', 'intermarche', 'super u', 'casino', 'franprix', 'marche', 'epicerie', 'boulangerie', 'alimentation', 'picard'],
        'Restaurants': ['restaurant', 'cafe', 'bar', 'bistrot', 'brasserie', 'uber eats', 'deliveroo', 'just eat', 'frichti', 'traiteur'],
        'Transport': ['uber', 'taxi', 'transport', 'metro', 'ratp', 'sncf', 'bus', 'train', 'essence', 'carburant', 'parking', 'peage', 'autoroute'],
        'Shopping': ['amazon', 'fnac', 'darty', 'galeries lafayette', 'printemps', 'zara', 'h&m', 'uniqlo', 'decathlon', 'vetement', 'achat', 'buisson','mathon', 'verbaudet'],
        'Seconde Main': ['vinted', 'leboncoin'],
        'Loisirs': ['cinema', 'film', 'theatre', 'billet', 'concert', 'netflix', 'deezer', 'abonnement', 'cubicle', 'steam', 'epic games',],
        'Sante': ['pharmacie', 'medecin', 'docteur', 'medical', 'sante', 'dentiste', 'hopital', 'mutuelle', 'delignieres', 'pharma', 'dafniet', 'klouche', 'cadeau'],
        'Services': ['electricite', 'edf', 'engie', 'eau', 'veolia', 'internet', 'orange', 'sfr', 'free', 'bouygues', 'facture', 'gimmick'],
        'Logement': ['loyer', 'credit', 'appartement', 'maison', 'assurance', 'habitation', 'charges', 'immobilier'],
        'Revenus': ['salaire', 'virement', 'revenu', 'paiement recu', 'remboursement'],
        'Virements': ['virement', 'retrait', 'depot', 'dab', 'guichet'],
        'Voiture': ['essence', 'carburant', 'parking', 'peage', 'autoroute', 'asf', 'bain de'],
        'Banque': ['LCL', 'cotisation', 'assurance', 'CACI'],
        'Maison': ['leroy']
    }
    
    # Try to match the description to a category
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in description:
                return category
    
    # Default category
    return 'Autre'

def get_balance_over_time(dfs, manual_balance=0):
    """
    Calculate the balance over time from a list of transaction DataFrames.
    
    Args:
        dfs (list): List of pandas DataFrames with transaction data
        manual_balance (float): Manually entered current account balance
        
    Returns:
        pandas.DataFrame: DataFrame with daily balance data
    """
    try:
        if not dfs or all(df.empty for df in dfs):
            return pd.DataFrame(columns=['date', 'balance'])
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        if combined_df.empty:
            return pd.DataFrame(columns=['date', 'balance'])
        
        # Sort transactions by date
        combined_df = combined_df.sort_values('date')
        
        # Convert amount column to float type to ensure consistency
        combined_df['amount'] = combined_df['amount'].astype(float)
        
        # If manual balance is provided, use it instead of calculating from the file
        if manual_balance != 0:
            try:
                # Ensure data types are compatible for calculation
                starting_balance = float(manual_balance) - float(combined_df['amount'].sum())
            except (ValueError, TypeError) as e:
                print(f"Error converting manual balance: {e}")
                starting_balance = float(manual_balance)
        else:
            try:
                # Get the starting balance from the first file
                # This assumes the balance in the file represents the end balance after all transactions
                # Ensure data types are compatible for calculation
                starting_balance = float(dfs[0]['balance'].iloc[0]) - float(dfs[0]['amount'].sum())
            except (ValueError, TypeError) as e:
                print(f"Error calculating starting balance: {e}")
                # Fallback to a default starting balance of 0
                starting_balance = 0.0
        
        # Create a date range from the earliest to latest transaction
        date_range = pd.date_range(
            start=combined_df['date'].min(),
            end=combined_df['date'].max(),
            freq='D'
        )
        
        # Create a DataFrame with the date range
        balance_df = pd.DataFrame({'date': date_range})
        
        # Add the daily transactions to the DataFrame
        daily_transactions = combined_df.groupby(combined_df['date'].dt.date)['amount'].sum().reset_index()
        daily_transactions['date'] = pd.to_datetime(daily_transactions['date'])
        daily_transactions['amount'] = daily_transactions['amount'].astype(float)
        
        # Merge the daily transactions with the date range
        balance_df = pd.merge(balance_df, daily_transactions, on='date', how='left')
        balance_df['amount'] = balance_df['amount'].fillna(0).astype(float)
        
        # Calculate the cumulative balance
        balance_df['balance'] = starting_balance + balance_df['amount'].cumsum()
        
        return balance_df[['date', 'balance']]
    except Exception as e:
        print(f"Error in get_balance_over_time: {e}")
        # Return an empty DataFrame if anything goes wrong
        return pd.DataFrame(columns=['date', 'balance'])

def get_spending_by_category(dfs):
    """
    Calculate spending by category from a list of transaction DataFrames.
    
    Args:
        dfs (list): List of pandas DataFrames with transaction data
        
    Returns:
        pandas.DataFrame: DataFrame with spending by category
    """
    try:
        if not dfs or all(df.empty for df in dfs):
            return pd.DataFrame(columns=['category', 'amount'])
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        if combined_df.empty:
            return pd.DataFrame(columns=['category', 'amount'])
        
        # Convert amount to float to ensure consistency
        combined_df['amount'] = combined_df['amount'].astype(float)
        
        # Filter for expenses (negative amounts)
        expenses_df = combined_df[combined_df['amount'] < 0].copy()
        
        # Take the absolute value of the amount
        expenses_df['amount'] = expenses_df['amount'].abs()
        
        # Group by category and sum the amounts
        category_spending = expenses_df.groupby('category')['amount'].sum().reset_index()
        
        # Convert to float to ensure consistency
        category_spending['amount'] = category_spending['amount'].astype(float)
        
        # Sort by amount in descending order
        category_spending = category_spending.sort_values('amount', ascending=False)
        
        return category_spending
    except Exception as e:
        print(f"Error in get_spending_by_category: {e}")
        # Return an empty DataFrame if anything goes wrong
        return pd.DataFrame(columns=['category', 'amount'])

def save_transactions_to_parquet(dfs, filepath):
    """
    Save transaction DataFrames to a parquet file.
    
    Args:
        dfs (list): List of pandas DataFrames with transaction data
        filepath (str): Path where to save the parquet file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not dfs or all(df.empty for df in dfs):
            print("No transactions to save")
            return False
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        if combined_df.empty:
            print("No transactions to save")
            return False
        
        # Convert all numeric columns to float for consistency
        for col in combined_df.select_dtypes(include=['number']).columns:
            combined_df[col] = combined_df[col].astype(float)
        
        # Save to parquet
        combined_df.to_parquet(filepath, index=False)
        print(f"Saved {len(combined_df)} transactions to {filepath}")
        return True
    
    except Exception as e:
        print(f"Error saving transactions to parquet: {e}")
        return False

def load_transactions_from_parquet(contents, filename):
    """
    Load transaction data from a parquet file.
    
    Args:
        contents (bytes): The contents of the parquet file
        filename (str): The name of the file
        
    Returns:
        pandas.DataFrame: DataFrame containing transaction data
    """
    try:
        # Parse the parquet file
        df = pd.read_parquet(BytesIO(contents))
        
        # Ensure required columns exist
        required_columns = ['date', 'amount', 'description', 'category']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"Missing required columns in parquet file: {missing}")
            return pd.DataFrame()
        
        # Convert date column to datetime if it's not
        if not pd.api.types.is_datetime64_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
        
        # Ensure amount is float
        df['amount'] = df['amount'].astype(float)
        
        # Add balance column if missing (use 0 as placeholder)
        if 'balance' not in df.columns:
            df['balance'] = 0.0
        
        # Add account info if missing
        if 'account_id' not in df.columns:
            df['account_id'] = 'parquet-import'
        
        if 'account_type' not in df.columns:
            df['account_type'] = 'checking'
        
        if 'currency' not in df.columns:
            df['currency'] = 'EUR'
        
        print(f"Loaded {len(df)} transactions from {filename}")
        return df
    
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        return pd.DataFrame() 