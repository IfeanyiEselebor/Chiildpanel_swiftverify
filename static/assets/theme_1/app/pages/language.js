const I18nextDirect = function() {


    //
    // Setup module components
    //

    // Change language without page reload
    const _componentI18nextDirect = function() {
        if (typeof i18next == 'undefined') {
            console.warn('Warning - i18next.min.js is not loaded.');
            return;
        }


        // Configuration
        // -------------------------

        // Define main elements
        const elements = document.querySelectorAll('.language-switch .dropdown-item'),
            selector = document.querySelectorAll('[data-i18n]'),
            englishLangClass = 'en',
            russianLangClass = 'ru';
            chineseLangClass = 'zh';
            arabicLangClass = 'ar';
            dutchLangClass = 'nl';
            spanishLangClass = 'es';
            vietnameseLangClass = 'vn';

        // Add options
        i18next.use(i18nextHttpBackend).use(i18nextBrowserLanguageDetector).init({
            backend: {
                loadPath: '/assets/locales/{{lng}}.json'
            },
            debug: false,
            fallbackLng: 'en'
        },
        
        function (err, t) {
            selector.forEach(function(item) {
                item.innerHTML = i18next.t(item.getAttribute("data-i18n"));
            });
        });


        // Change languages in dropdown
        // -------------------------

        // Do stuff when i18Next is initialized
        i18next.on('initialized', function() {

            // English
            if(i18next.language == "en") {
                document.querySelector('.' + englishLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + englishLangClass).innerHTML;
            }

            if(i18next.language == "ar") {
                document.querySelector('.' + arabicLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + arabicLangClass).innerHTML;
            } else {
                if (localStorage.getItem("direction") !== null) {
                    document.getElementById("stylesheet").setAttribute('href', '/assets/css/ltr/all.min.css');
                    document.documentElement.setAttribute("dir", "ltr");
                    localStorage.removeItem("direction");
                }
            }

            // Russian
            if(i18next.language == "ru") {
                document.querySelector('.' + russianLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + russianLangClass).innerHTML;
            }

            // Chinese
            if(i18next.language == "zh") {
                document.querySelector('.' + chineseLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + chineseLangClass).innerHTML;
            }

            // Dutch
            if(i18next.language == "nl") {
                document.querySelector('.' + dutchLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + dutchLangClass).innerHTML;
            }

            // Dutch
            if(i18next.language == "es") {
                document.querySelector('.' + spanishLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + spanishLangClass).innerHTML;
            }

            if(i18next.language == "vn") {
                document.querySelector('.' + spanishLangClass).classList.add('active');
                document.querySelector('.language-switch .navbar-nav-link').innerHTML = document.querySelector('.' + vietnameseLangClass).innerHTML;
            }


            // Add responsive classes if toggler is not hidden on mobile
            document.querySelector('.language-switch .navbar-nav-link span').classList.add('d-none', 'd-lg-inline-block', 'me-1');
        });


        // Change languages in navbar
        // -------------------------

        elements.forEach(function(toggler) {
            toggler.addEventListener('click', function(e) {

                // Toggle active class
                elements.forEach(function(link) {
                    link.classList.remove('active');
                });
                toggler.classList.add('active');

                // Display selected languate text and flag
                toggler.closest('.language-switch').querySelector('.navbar-nav-link').innerHTML = toggler.innerHTML;
                toggler.closest('.language-switch').querySelector('.navbar-nav-link span').classList.add('d-none', 'd-lg-inline-block', 'me-1');

                // Re-init translation service
                i18next.on('languageChanged', function() {
                    selector.forEach(function(item) {
                        item.innerHTML = i18next.t(item.getAttribute("data-i18n"));
                    });
                });

                // Switch language
                toggler.classList.contains(englishLangClass) && i18next.changeLanguage('en');
                toggler.classList.contains(russianLangClass) && i18next.changeLanguage('ru');
                toggler.classList.contains(chineseLangClass) && i18next.changeLanguage('zh');
                toggler.classList.contains(dutchLangClass) && i18next.changeLanguage('nl');
                toggler.classList.contains(spanishLangClass) && i18next.changeLanguage('es');
                toggler.classList.contains(vietnameseLangClass) && i18next.changeLanguage('vn');

                if (toggler.classList.contains(arabicLangClass)) {
                    document.getElementById("stylesheet").setAttribute('href', '/assets/css/rtl/all.min.css');
                    document.documentElement.setAttribute("dir", "rtl");
                    localStorage.setItem("direction", "rtl");
                    i18next.changeLanguage('ar');
                } else {
                    document.getElementById("stylesheet").setAttribute('href', '/assets/css/ltr/all.min.css');
                    document.documentElement.setAttribute("dir", "ltr");
                    localStorage.removeItem("direction");
                }

            });
        });
    };


    //
    // Return objects assigned to module
    //

    return {
        init: function() {
            _componentI18nextDirect();
        }
    }
}();


// Initialize module
// ------------------------------

document.addEventListener('DOMContentLoaded', function() {
    I18nextDirect.init();
});