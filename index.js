const menuBtn = document.querySelector("#menu-btn");
const themeToggler = document.querySelector(".theme-toggler");

// Function to apply the theme based on localStorage value
function applyTheme() {
    const isDarkTheme = localStorage.getItem('dark-theme');
    if (isDarkTheme === 'true') {
        document.body.classList.add('dark-theme-variables');
        themeToggler.querySelector('span:nth-child(1)').classList.remove('active');
        themeToggler.querySelector('span:nth-child(2)').classList.add('active');
        updateTradingViewTheme('dark');
    } else {
        document.body.classList.remove('dark-theme-variables');
        themeToggler.querySelector('span:nth-child(1)').classList.add('active');
        themeToggler.querySelector('span:nth-child(2)').classList.remove('active');
        updateTradingViewTheme('light');
    }
}

// Apply theme on page load
applyTheme();

themeToggler.addEventListener('click', () => {
    document.body.classList.toggle('dark-theme-variables');
    const isDarkTheme = document.body.classList.contains('dark-theme-variables');
    localStorage.setItem('dark-theme', isDarkTheme);
    updateTradingViewTheme(isDarkTheme ? 'dark' : 'light');

    themeToggler.querySelector('span:nth-child(1)').classList.toggle('active');
    themeToggler.querySelector('span:nth-child(2)').classList.toggle('active');
});

function updateTradingViewTheme(theme) {
    const tradingViewContainer = document.getElementById('tradingview_79df7');
    tradingViewContainer.innerHTML = ''; // Clear the container

    new TradingView.widget({
        "width": "100%",
        "height": 532,
        "symbol": "BINANCE:BTCUSDT",
        "timezone": "Asia/Kolkata",
        "theme": theme,
        "interval": "D",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_side_toolbar": true,
        "allow_symbol_change": true,
        "container_id": "tradingview_79df7"
    });
}
