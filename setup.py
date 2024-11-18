from setuptools import setup, find_packages

setup(
    name="dao-governance-scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.12.2",
        "requests>=2.31.0",
        "lxml>=4.9.3",
        "numpy>=1.26.0",
        "pandas>=2.1.1",
        "SQLAlchemy>=2.0.21",
        "alembic>=1.12.1",
        "PyYAML>=6.0.1",
        "python-dotenv>=1.0.0",
        "tqdm>=4.66.1",
        "colorlog>=6.7.0",
        "PyQt6>=6.5.0",  # Added for GUI support
    ],
)