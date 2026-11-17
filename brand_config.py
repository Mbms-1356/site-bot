"""Central brand configuration used by every generated content package."""
import os

BRAND = {
    'name': 'Forexin Turkaslani',
    'free_channel': 'https://t.me/forexin_turkaslanifree',
    'base_channel': 'https://t.me/Forexin_Turkaslani_Base',
    'community': 'https://t.me/forexinturkaslanilitcommuniti',
    'youtube': 'https://www.youtube.com/@Forexin.turkaslani',
    'instagram': 'https://instagram.com/Forexin.turkaslani',
    'website': 'https://mbms-1356.github.io/forexin-site-/',
    'logo_url': (os.environ.get('BRAND_LOGO_URL', '').strip()
                 or 'https://mbms-1356.github.io/forexin-site-/logo.png'),
}


def brand_links():
    return ('📣 کانال رایگان و سیگنال: ' + BRAND['free_channel'] + '\n'
            '🎓 کانال آموزش Base: ' + BRAND['base_channel'] + '\n'
            '💬 گروه LIT Community: ' + BRAND['community'] + '\n'
            '▶️ یوتیوب: ' + BRAND['youtube'] + '\n'
            '📷 اینستاگرام: ' + BRAND['instagram'] + '\n'
            '🌐 سایت: ' + BRAND['website'])


def branded_cta():
    return ('برای آموزش‌های بیشتر، کانال Base و سایت Forexin را دنبال کنید.\n\n' + brand_links())
