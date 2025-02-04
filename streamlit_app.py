import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import shutil

# Set page config
st.set_page_config(
    page_title="Core Web Vitals Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Define the base directory (where your script is located)
BASE_DIR = '.'  # or os.path.dirname(__file__)
HISTORY_DIR = os.path.join(BASE_DIR, 'history')
css_path = os.path.join(BASE_DIR, 'style.css')



# Load custom CSS
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def process_consolidated_file():
    consolidated_df = pd.read_csv(os.path.join(BASE_DIR, 'cwv_report.txt'), sep='\t')
    consolidated_df['Date'] = consolidated_df['Date'].apply(lambda x: x.split('GMT')[0].strip())
    consolidated_df['Date'] = pd.to_datetime(consolidated_df['Date']).dt.strftime('%Y-%m-%d')
    
    for date in consolidated_df['Date'].unique():
        date_df = consolidated_df[consolidated_df['Date'] == date]
        history_file = os.path.join(HISTORY_DIR, f"{date}_cwv_report.txt")
        if not os.path.exists(history_file):
            date_df.to_csv(history_file, sep='\t', index=False)
    
    return consolidated_df

def load_historical_data():
    process_consolidated_file()
    all_data = []
    for file in os.listdir(HISTORY_DIR):
        if file.endswith('_cwv_report.txt'):
            df = pd.read_csv(os.path.join(HISTORY_DIR, file), sep='\t')
            all_data.append(df)
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None

def load_current_data():
    process_consolidated_file()
    history_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('_cwv_report.txt')]
    latest_file = max(history_files)
    df = pd.read_csv(os.path.join(HISTORY_DIR, latest_file), sep='\t')
    df['all_green'] = (df['INP'] >= 75) & (df['CLS'] >= 75) & (df['LCP'] >= 75)
    return df

def create_metric_card(label, value, delta=None):
    with st.container():
        st.markdown(f'<div class="metric-container">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
        
        # Create a container for the value and delta
        st.markdown('<div class="metric-value-container">', unsafe_allow_html=True)
        
        if delta:
            # Use st.metric inside the value container
            st.metric(label="", value=value, delta=delta)
        else:
            # Use markdown for simple value display
            st.markdown(f'<div class="metric-value">{value}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Load data
df = load_current_data()
historical_df = load_historical_data()

# Main title
st.markdown('<p class="main-title">📊 Core Web Vitals Dashboard</p>', unsafe_allow_html=True)

# Create tabs
tab1, tab2, tab3 = st.tabs(["Current Status", "Trend Analysis", "Domain Analysis"])


################################################################################################################
##################################                 TAB 1               #########################################
################################################################################################################
with tab1:
    # Date display
    st.markdown(f'<p class="date-display">Last Update: {df["Date"].iloc[0]}</p>', unsafe_allow_html=True)
    
    # Top-level metrics in cards
    col1, col2, col3 = st.columns(3)
    with col1:
        create_metric_card("Total Domains", df['URL'].nunique())
    with col2:
        create_metric_card("All Green Domains", df[df['all_green']]['URL'].nunique())
    with col3:
        green_percentage = (df[df['all_green']]['URL'].nunique() / df['URL'].nunique() * 100)
        create_metric_card("Success Rate", f"{green_percentage:.1f}%")

    # Performance charts
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="subheader">Performance by Device</p>', unsafe_allow_html=True)
        device_metrics = df.groupby('Device').agg({
            'INP': 'mean',
            'CLS': 'mean',
            'LCP': 'mean'
        }).round(2)
        
        fig = go.Figure()
        metrics = ['INP', 'CLS', 'LCP']
        colors = ['#4CAF50', '#2196F3', '#FFC107']
        
        for metric, color in zip(metrics, colors):
            fig.add_trace(go.Bar(
                name=metric,
                x=device_metrics.index,
                y=device_metrics[metric],
                marker_color=color
            ))
        
        fig.update_layout(
            barmode='group',
            height=400,
            template='plotly_white',
            margin=dict(t=30, b=30, l=30, r=30)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown('<p class="subheader">Success Rate by Metric</p>', unsafe_allow_html=True)
        metrics_data = pd.DataFrame({
            'Metric': ['INP', 'CLS', 'LCP'],
            'Pass Rate': [
                (df['INP'] >= 75).mean() * 100,
                (df['CLS'] >= 75).mean() * 100,
                (df['LCP'] >= 75).mean() * 100
            ]
        })
        
        fig = go.Figure([
            go.Bar(
                x=metrics_data['Metric'],
                y=metrics_data['Pass Rate'],
                text=metrics_data['Pass Rate'].round(1).astype(str) + '%',
                textposition='outside',
                marker_color='#4CAF50'
            )
        ])
        
        fig.update_layout(
            height=400,
            template='plotly_white',
            margin=dict(t=30, b=30, l=30, r=30),
            yaxis_title="Pass Rate (%)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Detailed table section
    st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Detailed Performance by Domain</p>', unsafe_allow_html=True)

    # Filters in sidebar
    st.sidebar.markdown('<p class="subheader">Filters</p>', unsafe_allow_html=True)

    # Add Status filter
    selected_status = st.sidebar.multiselect(
        "Status",
        options=["All Green", "Needs Improvement"],
        default=["All Green", "Needs Improvement"]
    )

    # Get latest date
    latest_date = df['Date'].max()

    # Prepare the data
    desktop_data = df[
        (df['Date'] == latest_date) & 
        (df['Device'] == 'desktop')
    ].set_index('URL')[['INP', 'CLS', 'LCP']]
    desktop_data.columns = ['Desktop_INP', 'Desktop_CLS', 'Desktop_LCP']

    mobile_data = df[
        (df['Date'] == latest_date) & 
        (df['Device'] == 'mobile')
    ].set_index('URL')[['INP', 'CLS', 'LCP']]
    mobile_data.columns = ['Mobile_INP', 'Mobile_CLS', 'Mobile_LCP']

    # Merge desktop and mobile data
    merged_df = pd.merge(desktop_data, mobile_data, left_index=True, right_index=True, how='outer').reset_index()

    # Calculate all_green status based on all metrics
    merged_df['all_green'] = (
        (merged_df['Desktop_INP'] >= 75) & 
        (merged_df['Desktop_CLS'] >= 75) & 
        (merged_df['Desktop_LCP'] >= 75) &
        (merged_df['Mobile_INP'] >= 75) & 
        (merged_df['Mobile_CLS'] >= 75) & 
        (merged_df['Mobile_LCP'] >= 75)
    )

    # Add status column
    merged_df['Status'] = merged_df['all_green'].map({
        True: '<span class="status-green">✅ All Green</span>',
        False: '<span class="status-red">❌ Needs Improvement</span>'
    })

    # Apply status filter
    if len(selected_status) < 2:  # If not both are selected
        if "All Green" in selected_status:
            merged_df = merged_df[merged_df['all_green'] == True]
        elif "Needs Improvement" in selected_status:
            merged_df = merged_df[merged_df['all_green'] == False]

    # Sort the dataframe
    merged_df = merged_df.sort_values(['all_green', 'URL'], ascending=[False, True])

    # Style the dataframe
    styled_df = merged_df[['URL', 
                        'Desktop_INP', 'Desktop_CLS', 'Desktop_LCP',
                        'Mobile_INP', 'Mobile_CLS', 'Mobile_LCP',
                        'Status']].style\
        .format({
            'Desktop_INP': '{:.2f}',
            'Desktop_CLS': '{:.2f}',
            'Desktop_LCP': '{:.2f}',
            'Mobile_INP': '{:.2f}',
            'Mobile_CLS': '{:.2f}',
            'Mobile_LCP': '{:.2f}',
            'Status': lambda x: x  # Allow HTML in status
        })\
        .set_properties(**{
            'background-color': '#ffffff',
            'color': '#2c3e50',
            'border': '1px solid #eee',
            'text-align': 'left',
            'padding': '12px'
        })\
        .set_table_styles([
            {'selector': '', 'props': [('border-collapse', 'collapse')]},
            {'selector': 'th', 'props': [
                ('position', 'sticky'),
                ('top', '0'),
                ('background-color', '#f8f9fa'),
                ('color', '#2c3e50'),
                ('font-weight', 'bold'),
                ('text-align', 'left'),
                ('padding', '12px'),
                ('border', '1px solid #dee2e6'),
                ('z-index', '1')
            ]},
            {'selector': 'td', 'props': [
                ('border', '1px solid #dee2e6'),
                ('padding', '12px')
            ]},
            {'selector': 'tbody tr:hover', 'props': [
                ('background-color', '#f5f5f5')
            ]}
        ])

    # Define styling function for metrics
    def style_metric(val):
        try:
            val = float(val)
            color = '#28a745' if val >= 75 else '#dc3545'
            return f'color: {color}; font-weight: 500;'
        except:
            return ''

    # Apply styling to all metric columns
    metric_columns = [
        'Desktop_INP', 'Desktop_CLS', 'Desktop_LCP',
        'Mobile_INP', 'Mobile_CLS', 'Mobile_LCP'
    ]
    for col in metric_columns:
        styled_df = styled_df.map(style_metric, subset=[col])

    # Display table with row count
    st.markdown(f'<p>Showing {len(merged_df)} entries</p>', unsafe_allow_html=True)
    st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

################################################################################################################
##################################                 TAB 2               #########################################
################################################################################################################

with tab2:
    if historical_df is not None:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<p class="subheader">Performance Trends</p>', unsafe_allow_html=True)
        
        # Calculate metrics
        daily_metrics = historical_df.groupby('Date').agg({
            'all_green': lambda x: sum(x) / len(x) * 100,
            'INP': 'mean',
            'CLS': 'mean',
            'LCP': 'mean'
        }).reset_index()
        
        # Overall success rate trend
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_metrics['Date'],
            y=daily_metrics['all_green'],
            mode='lines+markers',
            name='Success Rate',
            line=dict(color='#4CAF50', width=2)
        ))
        
        fig.update_layout(
            title="Overall Success Rate Trend",
            height=400,
            template='plotly_white',
            margin=dict(t=50, b=30, l=30, r=30),
            yaxis_title="Success Rate (%)",
            yaxis=dict(range=[0, 100])  # Force y-axis to start at 0
        )
        st.plotly_chart(fig, use_container_width=True)
                
        # Individual metrics trend
        fig = go.Figure()
        colors = ['#4CAF50', '#2196F3', '#FFC107']
        
        for metric, color in zip(['INP', 'CLS', 'LCP'], colors):
            fig.add_trace(go.Scatter(
                x=daily_metrics['Date'],
                y=daily_metrics[metric],
                mode='lines+markers',
                name=metric,
                line=dict(color=color, width=2)
            ))

        fig.update_layout(
            title="Core Web Vitals Metrics Over Time",
            height=400,
            template='plotly_white',
            margin=dict(t=50, b=30, l=30, r=30),
            yaxis_title="Score",
            yaxis=dict(range=[0, max(daily_metrics[['INP', 'CLS', 'LCP']].max()) * 1.1])
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Device-specific trends
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<p class="subheader">Device Performance</p>', unsafe_allow_html=True)
        
        device_daily = historical_df.groupby(['Date', 'Device']).agg({
            'all_green': lambda x: sum(x) / len(x) * 100
        }).reset_index()
        
        fig = px.line(
            device_daily,
            x='Date',
            y='all_green',
            color='Device',
            title="Success Rate by Device Type",
            labels={'all_green': 'Success Rate (%)', 'Date': 'Date'}
        )
        
        fig.update_layout(
            height=400,
            template='plotly_white',
            margin=dict(t=50, b=30, l=30, r=30)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


################################################################################################################
##################################                 TAB 3              #########################################
################################################################################################################

with tab3:
    st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Domain Analysis</p>', unsafe_allow_html=True)
    
    # Domain selector with search
    selected_domain = st.selectbox(
        "Select Domain",
        options=sorted(df['URL'].unique()),
        key="domain_selector"
    )
    
    if selected_domain:
        domain_data = df[df['URL'] == selected_domain]
        
        # Current metrics comparison in smaller columns
        col1, col2 = st.columns([1, 1])
        
        with col1:
            desktop_data = domain_data[domain_data['Device'] == 'desktop'].iloc[0] if not domain_data[domain_data['Device'] == 'desktop'].empty else None
            st.markdown('<p class="subheader">Desktop Metrics</p>', unsafe_allow_html=True)
            if desktop_data is not None:
                for metric in ['INP', 'CLS', 'LCP']:
                    value = desktop_data[metric]
                    status = '✅' if value >= 75 else '❌'
                    st.markdown(f"**{metric}:** {value:.2f} {status}", unsafe_allow_html=True)
        
        with col2:
            mobile_data = domain_data[domain_data['Device'] == 'mobile'].iloc[0] if not domain_data[domain_data['Device'] == 'mobile'].empty else None
            st.markdown('<p class="subheader">Mobile Metrics</p>', unsafe_allow_html=True)
            if mobile_data is not None:
                for metric in ['INP', 'CLS', 'LCP']:
                    value = mobile_data[metric]
                    status = '✅' if value >= 75 else '❌'
                    st.markdown(f"**{metric}:** {value:.2f} {status}", unsafe_allow_html=True)

        # Historical performance in full width
        if historical_df is not None:
            st.markdown('<div class="chart-container full-width">', unsafe_allow_html=True)
            st.markdown('<p class="subheader">Historical Performance</p>', unsafe_allow_html=True)
            
            domain_history = historical_df[historical_df['URL'] == selected_domain]
            
            fig = go.Figure()
            colors = {'desktop': ['#4CAF50', '#2196F3', '#FFC107'],
                     'mobile': ['#45a049', '#1976D2', '#FFA000']}
            
            for device in ['desktop', 'mobile']:
                device_data = domain_history[domain_history['Device'] == device]
                for metric, color in zip(['INP', 'CLS', 'LCP'], colors[device]):
                    fig.add_trace(go.Scatter(
                        x=device_data['Date'],
                        y=device_data[metric],
                        name=f"{device} {metric}",
                        mode='lines+markers',
                        line=dict(color=color, width=2)
                    ))
            
            fig.add_hline(y=75, line_dash="dash", line_color="red", 
                        annotation_text="Threshold (75)")
            
            fig.update_layout(
                title="Metric History",
                height=500,  # Increased height
                template='plotly_white',
                margin=dict(t=50, b=30, l=30, r=30),
                xaxis_title="Date",
                yaxis_title="Score",
                yaxis=dict(range=[0, 100]),  # Force y-axis to start at 0
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Use full width for the chart
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



################################################################################################################
##################################                 SideBar              #########################################
################################################################################################################

# Add download buttons at the bottom
st.sidebar.markdown("### Export Data")
current_csv = df.to_csv(index=False).encode('utf-8')
historical_csv = historical_df.to_csv(index=False).encode('utf-8') if historical_df is not None else None

st.sidebar.download_button(
    label="Download Current Data",
    data=current_csv,
    file_name=f"cwv_data_{df['Date'].iloc[0]}.csv",
    mime="text/csv"
)

if historical_csv:
    st.sidebar.download_button(
        label="Download Historical Data",
        data=historical_csv,
        file_name="cwv_historical_data.csv",
        mime="text/csv"
    )

# About section in sidebar
st.sidebar.markdown("### About")
st.sidebar.info("Core Web Vitals Dashboard v1.0")
