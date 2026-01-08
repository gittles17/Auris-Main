"""
Data Loader - Loads and formats CSV data for the agent.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"


class DataLoader:
    """Loads business data from CSV files."""
    
    def __init__(self):
        self.revenue_goals: Optional[pd.DataFrame] = None
        self.weekly_pnl: Optional[pd.DataFrame] = None
        self.clients: Optional[pd.DataFrame] = None
    
    def load_revenue_goals(self) -> Optional[pd.DataFrame]:
        """Load creative director revenue goals."""
        filepath = DATA_DIR / "revenue_goals.csv"
        if filepath.exists():
            try:
                df = pd.read_csv(filepath, comment='#')
                if not df.empty:
                    self.revenue_goals = df
                    return df
            except Exception as e:
                print(f"Warning: Could not load revenue goals: {e}")
        return None
    
    def load_weekly_pnl(self) -> Optional[pd.DataFrame]:
        """Load weekly P&L data."""
        filepath = DATA_DIR / "weekly_pnl.csv"
        if filepath.exists():
            try:
                df = pd.read_csv(filepath, comment='#')
                if not df.empty:
                    self.weekly_pnl = df
                    return df
            except Exception as e:
                print(f"Warning: Could not load weekly P&L: {e}")
        return None
    
    def load_clients(self) -> Optional[pd.DataFrame]:
        """Load client data."""
        filepath = DATA_DIR / "clients.csv"
        if filepath.exists():
            try:
                df = pd.read_csv(filepath, comment='#')
                if not df.empty:
                    self.clients = df
                    return df
            except Exception as e:
                print(f"Warning: Could not load clients: {e}")
        return None
    
    def format_revenue_summary(self) -> str:
        """Format revenue goals for the AI context."""
        if self.revenue_goals is None or self.revenue_goals.empty:
            return "No revenue goal data available. Please upload revenue_goals.csv"
        
        lines = []
        for _, row in self.revenue_goals.iterrows():
            cd = row.get('creative_director', 'Unknown')
            target = row.get('annual_target_2026', 0)
            ytd = row.get('ytd_actual', 0)
            pct = (ytd / target * 100) if target > 0 else 0
            
            month = datetime.now().month
            expected_pct = (month / 12) * 100
            pace_status = "ahead" if pct > expected_pct else "behind"
            
            lines.append(
                f"- {cd}: ${target:,.0f} target | ${ytd:,.0f} YTD ({pct:.1f}%) | {pace_status} pace"
            )
        
        return "\n".join(lines)
    
    def format_pnl_summary(self) -> str:
        """Format P&L data for the AI context."""
        if self.weekly_pnl is None or self.weekly_pnl.empty:
            return "No P&L data available. Please upload weekly_pnl.csv"
        
        lines = []
        
        total_budget = self.weekly_pnl['budget'].sum()
        total_billed = self.weekly_pnl['billed'].sum()
        total_gp = self.weekly_pnl['gross_profit'].sum()
        avg_margin = self.weekly_pnl['margin_pct'].mean()
        
        lines.append(f"Total Active Budget: ${total_budget:,.0f}")
        lines.append(f"Total Billed: ${total_billed:,.0f}")
        lines.append(f"Total Gross Profit: ${total_gp:,.0f}")
        lines.append(f"Average Margin: {avg_margin:.1f}%")
        lines.append("")
        
        active = self.weekly_pnl[self.weekly_pnl['status'] == 'In Progress']
        if not active.empty:
            lines.append("Active Jobs:")
            for _, row in active.iterrows():
                job = row.get('job_name', 'Unknown')
                client = row.get('client', 'Unknown')
                cd = row.get('creative_director', 'Unknown')
                budget = row.get('budget', 0)
                actual = row.get('actual_cost', 0)
                margin = row.get('margin_pct', 0)
                
                status = "OVER BUDGET" if actual > budget else "on track"
                
                lines.append(
                    f"  - {job} ({client}) | CD: {cd} | Budget: ${budget:,.0f} | "
                    f"Spent: ${actual:,.0f} | Margin: {margin:.0f}% | {status}"
                )
        
        complete = self.weekly_pnl[self.weekly_pnl['status'] == 'Complete'].head(5)
        if not complete.empty:
            lines.append("\nRecently Completed:")
            for _, row in complete.iterrows():
                job = row.get('job_name', 'Unknown')
                client = row.get('client', 'Unknown')
                gp = row.get('gross_profit', 0)
                margin = row.get('margin_pct', 0)
                lines.append(f"  - {job} ({client}) | GP: ${gp:,.0f} | Margin: {margin:.0f}%")
        
        return "\n".join(lines)
    
    def format_client_summary(self) -> str:
        """Format client data for the AI context."""
        if self.clients is None or self.clients.empty:
            return "No client data available. Please upload clients.csv"
        
        lines = []
        
        sorted_clients = self.clients.sort_values('total_revenue_2025', ascending=False)
        
        for _, row in sorted_clients.head(10).iterrows():
            name = row.get('client_name', 'Unknown')
            ctype = row.get('client_type', 'Unknown')
            rev_2025 = row.get('total_revenue_2025', 0)
            gp_2025 = row.get('gross_profit_2025', 0)
            last_project = row.get('last_project', 'N/A')
            owner = row.get('relationship_owner', 'Unassigned')
            
            margin = (gp_2025 / rev_2025 * 100) if rev_2025 > 0 else 0
            
            lines.append(
                f"- {name} ({ctype}): ${rev_2025:,.0f} rev | ${gp_2025:,.0f} GP ({margin:.0f}%) | "
                f"Last: {last_project} | Owner: {owner}"
            )
        
        return "\n".join(lines)

