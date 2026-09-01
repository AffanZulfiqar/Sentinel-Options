"""
setup.py – Package metadata for editable install.

    pip install -e .
"""
from setuptools import setup, find_packages

setup(
    name="news-sentiment-agent",
    version="1.0.0",
    description="Autonomous options trading agent using news sentiment and Claude AI",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.18.0",
        "python-dotenv>=1.0.0",
        "feedparser>=6.0.10",
        "requests>=2.31.0",
        "streamlit>=1.28.0",
        "schedule>=1.2.0",
        "pandas>=2.0.0",
        "plotly>=5.17.0",
        "alpaca-py>=0.22.0",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
    ],
    entry_points={
        "console_scripts": [
            "trading-agent=src.agent_controller:main",
        ]
    },
)
