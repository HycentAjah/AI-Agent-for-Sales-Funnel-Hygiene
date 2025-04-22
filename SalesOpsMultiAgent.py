# Comprehensive Python Classes for Data Hygiene Agents with Dashboard Output

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
from fuzzywuzzy import fuzz

# 1. MissingFieldsAgent
class MissingFieldsAgent:
    def check(self, record: Dict[str, Any], required_fields: List[str]) -> List[str]:
        return [field for field in required_fields if not record.get(field)]

# 2. ValidationAgent
class ValidationAgent:
    def validate(self, record: Dict[str, Any]) -> List[str]:
        errors = []
        if 'email' in record:
            if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(record.get('email', ''))):
                errors.append("Invalid email")
        if 'phone' in record:
            if not re.match(r"^\+?\d{7,15}$", str(record.get('phone', ''))):
                errors.append("Invalid phone number")
        if 'amount' in record:
            try:
                if float(record['amount']) < 0:
                    errors.append("Negative amount")
            except:
                errors.append("Invalid amount")
        return errors

# 3. DeduplicationAgent
class DeduplicationAgent:
    def find_duplicates(self, records: List[Dict[str, Any]], key_field: str) -> List[tuple]:
        duplicates = []
        seen = set()
        for i, record in enumerate(records):
            for j, other in enumerate(records):
                if i != j and (j, i) not in seen:
                    score = fuzz.ratio(str(record.get(key_field, '')), str(other.get(key_field, '')))
                    if score > 90:
                        duplicates.append((i, j))
                        seen.add((i, j))
        return duplicates

# 4. StalenessAgent
class StalenessAgent:
    def detect_stale(self, record: Dict[str, Any], days_threshold: int = 30) -> bool:
        last_active = record.get("last_activity")
        if isinstance(last_active, str):
            try:
                last_date = datetime.strptime(last_active, "%Y-%m-%d")
                return (datetime.now() - last_date).days > days_threshold
            except ValueError:
                return True
        return True

# 5. NormalizationAgent
class NormalizationAgent:
    def normalize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = record.copy()
        if 'first_name' in normalized and normalized['first_name']:
            normalized['first_name'] = normalized['first_name'].title()
        if 'last_name' in normalized and normalized['last_name']:
            normalized['last_name'] = normalized['last_name'].title()
        if 'phone' in normalized and normalized['phone']:
            normalized['phone'] = re.sub(r'\D', '', str(normalized['phone']))
        return normalized

# 6. EnrichmentAgent
class EnrichmentAgent:
    def enrich(self, record: Dict[str, Any], enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        enriched = record.copy()
        for key, value in enrichment_data.items():
            if not enriched.get(key):
                enriched[key] = value
        return enriched

# 7. InsightsAgent
class InsightsAgent:
    def generate_insights(self, records: List[Dict[str, Any]], duplicates: List[tuple]) -> Dict[str, int]:
        df = pd.DataFrame(records)
        insights = {
            'Leads Missing Email': df['email'].isnull().sum(),
            'Opportunities Without Close Date': df['close_date'].isnull().sum(),
            'Duplicate Records Detected': len(duplicates),
            'Opportunities Without Owner': df['owner'].isnull().sum() if 'owner' in df else 0,
            'Deals Without Stage': df['stage'].isnull().sum() if 'stage' in df else 0,
            'Stale Opportunities': df['last_activity'].apply(lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days > 30 if isinstance(x, str) else True).sum(),
            'Untouched Leads (14+ days)': df['last_activity'].apply(lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days > 14 if isinstance(x, str) else True).sum(),
            'Missing Industry/Company Size': df[['industry', 'company_size']].isnull().any(axis=1).sum() if 'industry' in df and 'company_size' in df else 0,
            'Invalid Email or Phone': df.apply(lambda x: not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(x.get('email', ''))) or not re.match(r"^\+?\d{7,15}$", str(x.get('phone', ''))), axis=1).sum(),
            'Contacts Without Accounts': df['account_id'].isnull().sum() if 'account_id' in df else 0,
            'Past-Due Close Dates': df['close_date'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d") < datetime.now() if isinstance(x, str) else False).sum(),
            'Normalization Fixes': df['normalized'].sum() if 'normalized' in df else 0
        }
        return insights

    def calculate_health_score(self, insights: Dict[str, int]) -> int:
        weights = {
            'Leads Missing Email': 0.2,
            'Opportunities Without Close Date': 0.3,
            'Duplicate Records Detected': 0.5,
            'Opportunities Without Owner': 1.0,
            'Deals Without Stage': 0.3,
            'Stale Opportunities': 0.2,
            'Untouched Leads (14+ days)': 0.15,
            'Missing Industry/Company Size': 0.1,
            'Invalid Email or Phone': 0.2,
            'Contacts Without Accounts': 0.2,
            'Past-Due Close Dates': 0.25,
            'Normalization Fixes': 0.05
        }
        penalty = sum(insights[key] * weights.get(key, 0) for key in insights)
        return max(0, int(100 - penalty))

    def display_dashboard(self, insights: Dict[str, int], health_score: int):
        st.set_page_config(page_title="CRM Hygiene Dashboard", layout="wide")
        st.markdown("""
            <style>
            .grid-container {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                padding: 20px;
            }
            .grid-item {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: center;
            }
            .metric-title {
                font-size: 12px;
                color: black;
                margin-bottom: 8px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 6px;
            }
            .metric-link {
                font-size: 12px;
                color: #1f77b4;
                text-decoration: underline;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("<h1 style='color:#0066CC;'>CRM Data Hygiene Dashboard</h1>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='color:#00B140;'>CRM Health Score: {health_score}/100</h2>", unsafe_allow_html=True)

        st.markdown("<div class='grid-container'>", unsafe_allow_html=True)
        for key, value in insights.items():
            value_color = "#1f77b4" if value == 0 else "#E74C3C"
            st.markdown(f"""
                <div class='grid-item'>
                    <div class='metric-title'>{key}</div>
                    <div class='metric-value' style='color:{value_color};'>{value}</div>
                    <div class='metric-link'>View</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# 8. AlertAgent
class AlertAgent:
    def send_alert(self, user: str, message: str):
        print(f"[ALERT to {user}] {message}")

# 9. OrchestratorAgent
class OrchestratorAgent:
    def __init__(self):
        self.missing_agent = MissingFieldsAgent()
        self.validation_agent = ValidationAgent()
        self.dedupe_agent = DeduplicationAgent()
        self.stale_agent = StalenessAgent()
        self.normalize_agent = NormalizationAgent()
        self.enrich_agent = EnrichmentAgent()
        self.insight_agent = InsightsAgent()
        self.alert_agent = AlertAgent()

    def run_pipeline(self, records: List[Dict[str, Any]], enrichment_source: Dict[str, Any]):
        for i, record in enumerate(records):
            missing = self.missing_agent.check(record, ['email', 'lead_source', 'close_date'])
            if missing:
                self.alert_agent.send_alert("owner@example.com", f"Record {i} missing fields: {missing}")
            validation_errors = self.validation_agent.validate(record)
            if validation_errors:
                self.alert_agent.send_alert("owner@example.com", f"Record {i} validation errors: {validation_errors}")
            if self.stale_agent.detect_stale(record):
                self.alert_agent.send_alert("owner@example.com", f"Record {i} is stale")
            records[i] = self.normalize_agent.normalize(records[i])
            records[i]['normalized'] = True
            records[i] = self.enrich_agent.enrich(records[i], enrichment_source)

        duplicates = self.dedupe_agent.find_duplicates(records, 'email')
        insights = self.insight_agent.generate_insights(records, duplicates)
        health_score = self.insight_agent.calculate_health_score(insights)
        self.insight_agent.display_dashboard(insights, health_score)

# Entry Point for Running the Script with CSV Data
if __name__ == '__main__':
    import pandas as pd
    df = pd.read_csv("synthetic_crm_data.csv")
    records = df.to_dict(orient="records")
    agent = OrchestratorAgent()
    agent.run_pipeline(records, enrichment_source={})