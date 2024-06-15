var cacheName = 'Equinox1.0';
var filesToCache = [
    '../templates/card_activation.html',
    '../templates/cards.html',
    '../templates/contact.html',
    '../templates/error.html',
    '../templates/exchange.html',
    '../templates/help-center.html',
    '../templates/landing.html',
    '../templates/index.html',
    '../templates/markets.html',
    '../templates/notifications.html',
    '../templates/order-successful.html',
    '../templates/profile.html',
    '../templates/register.html',
    '../templates/settings.html',
    '../templates/terms.html',
    '../templates/tradingview.html',
    '../templates/wallet.html',
    '../templates/withdraw.html',


    // Styles
    './css/bootstrap.min.css',
    '/css/font-awesome.min.css',
    './css/main.css',
    './css/style.css',
    './css/jquery.jConveyorTicker.min.css',
    './css/jquerysctipttop.css',
    './css/main.css',
    './css/owl.carousel.min.css',
    './css/style.css',
    './css/util.css',


    // javascript
    './js/apexcharts.js',
    './js/bootstrap.bundle.min.js',
    '.js/candlestick.js',
    './js/chart-custom.js',
    './js/chart.min.js',
    './js/chart.peity.js',
    './js/clipboard.min.js',
    './js/jquery.jConveyorTicker.js',
    './js/jquery.min.js',
    './js/jquery.peity.min.js',
    './js/owl.carousel.min.js',
    './js/pwa.js',
    './js/script.js',
];

/* Start the service worker and cache all of the app's content */
self.addEventListener('install', function (e) {
    e.waitUntil(
        caches.open(cacheName).then(function (cache) {
            return cache.addAll(filesToCache);
        })
    );
});

/* Activate Event */
self.addEventListener('activate', function (e) {
    e.waitUntil(
        caches.keys().then(function (keyList) {
            return Promise.all(keyList.map(function (key) {
                if (key !== cacheName) {
                    return caches.delete(key);
                }
            }));
        })
    );
});

/* Serve cached content when offline */
self.addEventListener('fetch', function (e) {
    e.respondWith(
        caches.match(e.request).then(function (response) {
            return response || fetch(e.request);
        })
    );
});
