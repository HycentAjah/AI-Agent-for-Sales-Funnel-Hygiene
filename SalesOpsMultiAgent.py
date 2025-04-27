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
            'Leads Missing Email': 0.08,
            'Opportunities Without Close Date': 0.12,
            'Duplicate Records Detected': 0.15,
            'Opportunities Without Owner': 0.25,
            'Deals Without Stage': 0.08,
            'Stale Opportunities': 0.04,
            'Untouched Leads (14+ days)': 0.04,
            'Missing Industry/Company Size': 0.02,
            'Invalid Email or Phone': 0.06,
            'Contacts Without Accounts': 0.06,
            'Past-Due Close Dates': 0.08,
            'Normalization Fixes': 0.01
        }
        
        # Calculate weighted penalty with individual caps
        penalty = sum(
            min(insights[key], 5) * weights[key]  # Cap any single metric at 5 instances
            for key in weights 
            if insights.get(key, 0) > 0
        )
        
        # Apply non-linear scaling to achieve desired ranges
        if penalty == 0:
            return 100  # Perfect score
        elif penalty <= 0.5:
            return 95 + int((0.5 - penalty) * 10)  # 96-99 for very minor issues
        elif penalty <= 2:
            return 85 + int((2 - penalty) * 6.67)  # 75-94 for minor issues
        elif penalty <= 5:
            return 50 + int((5 - penalty) * 8.33)  # 50-74 for moderate issues
        else:
            return max(10, 50 - int((penalty - 5) * 4))  # <50 for serious problems

    def display_dashboard(self, insights: Dict[str, int], health_score: int):
        st.set_page_config(page_title="CRM Hygiene Dashboard", layout="wide")
        
        # Custom CSS for the dashboard
        st.markdown("""
        <style>
            .main-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid #e1e1e1;
            }
            .health-score {
                display: flex;
                flex-direction: column;
                align-items: center;
                background: #F0F8FF;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .metric-card {
                background: #F0FFF0;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .metric-title {
                font-size: 18px;
                font-weight: 600;
                color: #4a4a4a;
                margin-bottom: 10px;
            }
            .metric-value {
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 5px;
            }
            .metric-good {
                color: #2ecc71;
            }
            .metric-warning {
                color: #f39c12;
            }
            .metric-critical {
                color: #e74c3c;
            }
            .health-meter {
                width: 100%;
                height: 20px;
                background: #FFFFF0;
                border-radius: 10px;
                margin: 10px 0;
                overflow: hidden;
            }
            .health-meter-fill {
                height: 100%;
                background: linear-gradient(90deg, #e74c3c 0%, #f39c12 50%, #2ecc71 100%);
                border-radius: 10px;
                transition: width 0.5s ease;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 5px;
            }
            .status-good {
                background-color: #2ecc71;
            }
            .status-warning {
                background-color: #f39c12;
            }
            .status-critical {
                background-color: #e74c3c;
            }
            .tooltip {
                position: relative;
                display: inline-block;
                cursor: pointer;
            }
            .tooltip .tooltiptext {
                visibility: hidden;
                width: 200px;
                background-color: #555;
                color: #fff;
                text-align: center;
                border-radius: 6px;
                padding: 5px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                margin-left: -100px;
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 14px;
                font-weight: normal;
            }
            .tooltip:hover .tooltiptext {
                visibility: visible;
                opacity: 1;
            }
        </style>
        """, unsafe_allow_html=True)

        # Dashboard header
        st.markdown(f"""
        <div class="main-container">
            <div class="dashboard-header">
                <h1 style="color: #2c3e50; margin: 0;">CRM Data Hygiene Dashboard</h1>
                <div style="font-size: 16px; color: #7f8c8d;">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
            </div>
        """, unsafe_allow_html=True)

        # Health score section with adjusted ranges
        if health_score >= 90:
            health_color = "#2ecc71"
            health_status = "Excellent"
        elif health_score >= 75:
            health_color = "#2ecc71"
            health_status = "Good"
        elif health_score >= 50:
            health_color = "#f39c12"
            health_status = "Fair"
        else:
            health_color = "#e74c3c"
            health_status = "Poor"
        
        st.markdown(f"""
        <div class="health-score">
            <h2 style="margin: 0; color: #2c3e50;">CRM Health Score</h2>
            <div style="font-size: 48px; font-weight: 700; color: {health_color}; margin: 10px 0;">{health_score}/100</div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span class="status-indicator status-{'good' if health_score >= 75 else 'warning' if health_score >= 50 else 'critical'}"></span>
                <span style="font-size: 18px; font-weight: 600;">{health_status}</span>
            </div>
            <div class="health-meter">
                <div class="health-meter-fill" style="width: {health_score}%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; width: 100%; font-size: 12px; color: #7f8c8d;">
                <span>0 (Poor)</span>
                <span>50 (Fair)</span>
                <span>75 (Good)</span>
                <span>100 (Excellent)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics grid
        st.markdown("<h3 style='color: #2c3e50; margin-top: 30px;'>Data Quality Metrics</h3>", unsafe_allow_html=True)
        st.markdown("<div class='metrics-grid'>", unsafe_allow_html=True)
        
        severity_thresholds = {
            'Leads Missing Email': (5, 20),
            'Opportunities Without Close Date': (3, 10),
            'Duplicate Records Detected': (2, 5),
            'Opportunities Without Owner': (1, 3),
            'Deals Without Stage': (3, 8),
            'Stale Opportunities': (5, 15),
            'Untouched Leads (14+ days)': (10, 25),
            'Missing Industry/Company Size': (10, 30),
            'Invalid Email or Phone': (5, 15),
            'Contacts Without Accounts': (3, 10),
            'Past-Due Close Dates': (2, 5),
            'Normalization Fixes': (10, 30)
        }
        
        for key, value in insights.items():
            warning, critical = severity_thresholds.get(key, (5, 10))
            if value == 0:
                status_class = "metric-good"
                status_text = "✓ Good"
            elif value <= warning:
                status_class = "metric-good"
                status_text = "✓ Acceptable"
            elif value <= critical:
                status_class = "metric-warning"
                status_text = "⚠ Needs Attention"
            else:
                status_class = "metric-critical"
                status_text = "✗ Critical"
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">
                    <span class="tooltip">{key}
                        <span class="tooltiptext">This metric tracks {key.lower()}. Lower numbers indicate better data quality.</span>
                    </span>
                </div>
                <div class="metric-value {status_class}">{value}</div>
                <div style="display: flex; align-items: center;">
                    <span class="status-indicator status-{'good' if value == 0 else 'warning' if value <= critical else 'critical'}"></span>
                    <span style="font-size: 14px; color: {'#2ecc71' if value == 0 else '#f39c12' if value <= critical else '#e74c3c'}">{status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Add summary section
        critical_issues = sum(1 for key, value in insights.items() 
                            if value > severity_thresholds.get(key, (5, 10))[1])
        warning_issues = sum(1 for key, value in insights.items() 
                           if severity_thresholds.get(key, (5, 10))[0] < value <= severity_thresholds.get(key, (5, 10))[1])
        
        st.markdown(f"""
        <div style="margin-top: 40px; background: #f8f9fa; padding: 20px; border-radius: 8px;">
            <h3 style="color: #2c3e50; margin-top: 0;">Summary</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 14px; color: #7f8c8d;">Total Metrics</div>
                    <div style="font-size: 24px; font-weight: 700;">{len(insights)}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 14px; color: #7f8c8d;">Critical Issues</div>
                    <div style="font-size: 24px; font-weight: 700; color: #e74c3c;">{critical_issues}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 14px; color: #7f8c8d;">Warning Issues</div>
                    <div style="font-size: 24px; font-weight: 700; color: #f39c12;">{warning_issues}</div>
                </div>
            </div>
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

# Entry Point
if __name__ == '__main__':
    import pandas as pd
    df = pd.read_csv("synthetic_crm_data2.csv")
    records = df.to_dict(orient="records")
    agent = OrchestratorAgent()
    agent.run_pipeline(records, enrichment_source={})