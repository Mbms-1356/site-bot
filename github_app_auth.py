"""Read-only readiness checks for migrating from PAT to GitHub App."""
import os


def readiness():
    checks = {
        'GITHUB_APP_ID': bool(os.environ.get('GITHUB_APP_ID')),
        'GITHUB_APP_PRIVATE_KEY': bool(os.environ.get('GITHUB_APP_PRIVATE_KEY')),
        'GITHUB_APP_INSTALLATION_ID': bool(os.environ.get('GITHUB_APP_INSTALLATION_ID')),
    }
    return {'ready': all(checks.values()), 'checks': checks,
            'mode': 'pat-current' if not all(checks.values()) else 'github-app-ready',
            'note': 'تا زمان تکمیل هر سه Secret، توکن فعلی GH_PAT دست‌نخورده باقی می‌ماند.'}
