

const translations = {};
// Делаем объект переводов доступным через window, чтобы getTranslation работал корректно
if (typeof window !== 'undefined') {
  window.translations = translations;
}
let currentLanguage = navigator.language.slice(0, 2) || 'ru';


async function loadTranslations(lang) {
  try {
    
    const response = await fetch(`/locales/${lang}.json?v=${new Date().getTime()}`);
    if (!response.ok) throw new Error(`Could not load ${lang}.json`);
    translations[lang] = await response.json();
    if (typeof window !== 'undefined') {
      window.translations = translations;
    }
    console.log(`Translations for ${lang} loaded.`);
  } catch (error) {
    console.error(error);
  }
}


function applyTranslations(lang) {
  if (!translations[lang]) return;
  const trans = translations[lang];


  document.querySelectorAll('[data-i18n]').forEach(element => {
    const key = element.getAttribute('data-i18n');
    if (trans[key]) {
      element.innerHTML = trans[key]; 
    }
  });


  document.querySelectorAll('[data-i18n-attr]').forEach(element => {
    const [attr, key] = element.getAttribute('data-i18n-attr').split(':');
    if (trans[key]) {
      element.setAttribute(attr, trans[key]);
    }
  });

  // Обновляем aria-describedby / tooltip‑тексты для специальных кнопок сети
  updateNetworkButtonsTooltipsAria();

  document.documentElement.lang = lang;
}

async function setLanguage(lang) {
  if (!['ru', 'en'].includes(lang)) {
      lang = 'ru'; 
  }

  if (!translations[lang]) {
    await loadTranslations(lang);
  }
  
  currentLanguage = lang;
  applyTranslations(lang);
  localStorage.setItem('language', lang);
}

async function detectLanguageByIP() {
  try {
    const response = await fetch('https://ipapi.co/json/');
    if (!response.ok) throw new Error('Could not fetch IP geolocation data');
    const data = await response.json();
    const country = data.country_code;

    await setLanguage(country !== 'RU' ? 'en' : 'ru');
  } catch (error) {
    console.error('IP detection failed, defaulting to browser language:', error);
    await setLanguage(currentLanguage);
  }
}


document.addEventListener('DOMContentLoaded', async () => {
  const savedLang = localStorage.getItem('language');

  if (savedLang) {
    await setLanguage(savedLang); 
  } else {
    await detectLanguageByIP(); 
  }
});
function translateDynamicContent(parentElement) {
  if (!parentElement) return;
  if (!translations[currentLanguage]) {
      setTimeout(() => translateDynamicContent(parentElement), 100);
      return;
  }
  const trans = translations[currentLanguage];

  parentElement.querySelectorAll('[data-i18n]').forEach(element => {
    const key = element.getAttribute('data-i18n');
    if (trans[key]) {
      element.innerHTML = trans[key];
    }
  });

  parentElement.querySelectorAll('[data-i18n-attr]').forEach(element => {
    const attrString = element.getAttribute('data-i18n-attr');
    attrString.split(';').forEach(attrPair => {
        const [attr, key] = attrPair.split(':');
        if (trans[key]) {
            element.setAttribute(attr.trim(), trans[key]);
        }
    });
  });
}

// Обновляет текст элементов, на которые ссылается aria-describedby для кнопок share/copy/settings
function updateNetworkButtonsTooltipsAria() {
  if (typeof document === 'undefined') return;

  const map = {
    'share-network': 'tooltipUrlAvailable',
    'copy-network': 'tooltipSaveChanges',
    'net-settings': 'tooltipNetSettings',
  };

  Object.keys(map).forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    const key = map[id];
    const text = getTranslation(key);
    
    if (!text || text === key) return;

    if (typeof $ !== 'undefined' && $(el).data('bs.tooltip')) {
      $(el).attr('data-original-title', text).tooltip('fixTitle');
    } else if (typeof $ !== 'undefined') {
      $(el).attr('title', text);
      $(el).tooltip('dispose');
      $(el).tooltip({trigger: 'hover', title: text});
    }

    const describedById = el.getAttribute('aria-describedby');
    if (describedById) {
      const tooltipEl = document.getElementById(describedById);
      if (tooltipEl) {
        const inner = tooltipEl.querySelector('.tooltip-inner') || tooltipEl;
        inner.textContent = text;
      }
    }
  });
}

function getTranslation(key) {
    if (window.translations && window.translations[currentLanguage] && window.translations[currentLanguage][key]) {
        return window.translations[currentLanguage][key];
    }
    if (translations[currentLanguage] && translations[currentLanguage][key]) {
        return translations[currentLanguage][key];
    }
    return key; 
}