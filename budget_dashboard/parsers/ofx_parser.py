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
                'amount': transaction.amount,
                'description': transaction.memo if transaction.memo else transaction.payee,
                'type': transaction.type,
                'category': categorize_transaction(transaction.memo if transaction.memo else transaction.payee)
            })
        
        # Create a DataFrame
        df = pd.DataFrame(transactions)
        
        # Add account information
        df['account_id'] = account.account_id
        df['account_type'] = account.account_type
        df['balance'] = account.statement.balance
        df['currency'] = account.statement.currency
        
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
    except:
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
        'Courses': ['carrefour', 'lidl', 'aldi', 'monoprix', 'leclerc', 'intermarche', 'super u', 'casino', 'franprix', 'marche', 'epicerie', 'boulangerie', 'alimentation'],
        'Restaurants': ['restaurant', 'cafe', 'bar', 'bistrot', 'brasserie', 'uber eats', 'deliveroo', 'just eat', 'frichti', 'traiteur'],
        'Transport': ['uber', 'taxi', 'transport', 'metro', 'ratp', 'sncf', 'bus', 'train', 'essence', 'carburant', 'parking', 'peage', 'autoroute'],
        'Shopping': ['amazon', 'fnac', 'darty', 'galeries lafayette', 'printemps', 'zara', 'h&m', 'uniqlo', 'decathlon', 'vetement', 'achat'],
        'Loisirs': ['cinema', 'film', 'theatre', 'billet', 'concert', 'netflix', 'spotify', 'deezy', 'canal+', 'abonnement'],
        'Sante': ['pharmacie', 'medecin', 'docteur', 'medical', 'sante', 'dentiste', 'hopital', 'mutuelle'],
        'Services': ['electricite', 'edf', 'engie', 'eau', 'veolia', 'internet', 'orange', 'sfr', 'free', 'bouygues', 'facture'],
        'Logement': ['loyer', 'credit', 'appartement', 'maison', 'assurance', 'habitation', 'charges'],
        'Revenus': ['salaire', 'virement', 'revenu', 'paiement recu', 'remboursement'],
        'Virements': ['virement', 'retrait', 'depot', 'dab', 'guichet']
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
    if not dfs or all(df.empty for df in dfs):
        return pd.DataFrame(columns=['date', 'balance'])
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    if combined_df.empty:
        return pd.DataFrame(columns=['date', 'balance'])
    
    # Sort transactions by date
    combined_df = combined_df.sort_values('date')
    
    # If manual balance is provided, use it instead of calculating from the file
    if manual_balance != 0:
        starting_balance = manual_balance - combined_df['amount'].sum()
    else:
        # Get the starting balance from the first file
        # This assumes the balance in the file represents the end balance after all transactions
        starting_balance = dfs[0]['balance'].iloc[0] - dfs[0]['amount'].sum()
    
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
    
    # Merge the daily transactions with the date range
    balance_df = pd.merge(balance_df, daily_transactions, on='date', how='left')
    balance_df['amount'] = balance_df['amount'].fillna(0)
    
    # Calculate the cumulative balance
    balance_df['balance'] = starting_balance + balance_df['amount'].cumsum()
    
    return balance_df[['date', 'balance']]

def get_spending_by_category(dfs):
    """
    Calculate spending by category from a list of transaction DataFrames.
    
    Args:
        dfs (list): List of pandas DataFrames with transaction data
        
    Returns:
        pandas.DataFrame: DataFrame with spending by category
    """
    if not dfs or all(df.empty for df in dfs):
        return pd.DataFrame(columns=['category', 'amount'])
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    if combined_df.empty:
        return pd.DataFrame(columns=['category', 'amount'])
    
    # Filter for expenses (negative amounts)
    expenses_df = combined_df[combined_df['amount'] < 0].copy()
    
    # Take the absolute value of the amount
    expenses_df['amount'] = expenses_df['amount'].abs()
    
    # Group by category and sum the amounts
    category_spending = expenses_df.groupby('category')['amount'].sum().reset_index()
    
    # Sort by amount in descending order
    category_spending = category_spending.sort_values('amount', ascending=False)
    
    return category_spending 