class I18nManager {
  #translations = {};
  #currentLanguage = 'ru';
  #supportedLanguages = ['ru', 'en'];
  #defaultLanguage = 'ru';
  #observer = null;

  constructor() {
    this.DEBUG = typeof window !== 'undefined' && window.I18N_DEBUG === true;
  }

  /**
   * Логирование информационных сообщений (только в режиме отладки)
   * @param {...any} args 
   */
  #logInfo(...args) {
    if (this.DEBUG) {
      // eslint-disable-next-line no-console
      console.info('[i18n]', ...args);
    }
  }

  /**
   * Логирование ошибок (всегда включено)
   * @param {...any} args 
   */
  #logError(...args) {
    // eslint-disable-next-line no-console
    console.error('[i18n]', ...args);
  }

  /**
   * Текущий выбранный язык
   * @returns {string}
   */
  get currentLanguage() {
    return this.#currentLanguage;
  }

  /**
   * Инициализация локализации при загрузке страницы
   */
  async init() {
    const savedLang = localStorage.getItem('language');
    const browserLang = navigator.language.slice(0, 2);
    const langToSet = savedLang || browserLang || this.#defaultLanguage;

    await this.setLanguage(langToSet);
    this.#startMutationObserver();
  }

  /**
   * Устанавливает язык и применяет переводы
   * @param {string} lang 
   */
  async setLanguage(lang) {
    if (!this.#supportedLanguages.includes(lang)) {
      lang = this.#defaultLanguage;
    }

    if (!this.#translations[lang]) {
      const isLoaded = await this.#loadTranslations(lang);
      if (!isLoaded && lang !== this.#defaultLanguage) {
        lang = this.#defaultLanguage; // Fallback
      }
    }

    this.#currentLanguage = lang;
    this.#applyTranslations(lang);
    localStorage.setItem('language', lang);
  }

  /**
   * Загружает JSON-файл с переводами с сервера
   * @param {string} lang 
   * @returns {Promise<boolean>} Успешна ли загрузка
   */
  async #loadTranslations(lang) {
    try {
      const response = await fetch(`/locales/${lang}.json?v=${new Date().getTime()}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} - Could not load ${lang}.json`);
      }
      this.#translations[lang] = await response.json();
      this.#logInfo(`Translations for ${lang} loaded.`);
      return true;
    } catch (error) {
      this.#logError(`Failed to load translations for ${lang}:`, error);

      // Fallback механизм
      if (lang !== this.#defaultLanguage && !this.#translations[this.#defaultLanguage]) {
        this.#logInfo(`Attempting fallback to ${this.#defaultLanguage}...`);
        try {
          const fallbackResp = await fetch(`/locales/${this.#defaultLanguage}.json?v=${new Date().getTime()}`);
          if (!fallbackResp.ok) throw new Error(`Could not load ${this.#defaultLanguage}.json`);
          this.#translations[this.#defaultLanguage] = await fallbackResp.json();
          this.#logInfo(`Fallback to ${this.#defaultLanguage} applied.`);
        } catch (fallbackError) {
          this.#logError(`Fallback to ${this.#defaultLanguage} failed:`, fallbackError);
        }
      }
      return false;
    }
  }

  /**
   * Применяет загруженные переводы к текущему DOM
   * @param {string} lang 
   */
  #applyTranslations(lang) {
    if (!this.#translations[lang]) return;

    this.translateNode(document);
    this.#updateNetworkButtonsTooltipsAria();
    document.documentElement.lang = lang;
  }

  /**
   * Переводит все элементы внутри переданного узла
   * @param {HTMLElement|Document} node 
   */
  translateNode(node) {
    if (!node || !node.querySelectorAll) return;
    const trans = this.#translations[this.#currentLanguage];
    if (!trans) return;

    node.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      if (trans[key]) {
        element.innerHTML = trans[key];
      }
    });

    node.querySelectorAll('[data-i18n-attr]').forEach(element => {
      const attrString = element.getAttribute('data-i18n-attr');
      if (attrString) {
        attrString.split(';').forEach(attrPair => {
          const[attr, key] = attrPair.split(':');
          if (attr && key && trans[key]) {
            element.setAttribute(attr.trim(), trans[key]);
          }
        });
      }
    });
  }

  /**
   * Возвращает переведенную строку по ключу
   * @param {string} key 
   * @returns {string}
   */
  getTranslation(key) {
    const trans = this.#translations[this.#currentLanguage];
    if (trans && Object.prototype.hasOwnProperty.call(trans, key)) {
      return trans[key];
    }
    return key;
  }

  /**
   * Запускает MutationObserver для перевода динамически добавляемых элементов (замена setTimeout)
   */
  #startMutationObserver() {
    if (typeof MutationObserver === 'undefined') return;

    this.#observer = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Если сам узел имеет атрибуты перевода
            if (node.hasAttribute('data-i18n') || node.hasAttribute('data-i18n-attr')) {
              this.translateNode(node.parentElement || node);
            } else {
              // Ищем дочерние элементы
              this.translateNode(node);
            }
          }
        });
      });
    });

    this.#observer.observe(document.body, { childList: true, subtree: true });
  }

  /**
   * Адаптер для обновления тултипов Bootstrap 
   */
  #updateNetworkButtonsTooltipsAria() {
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
      const text = this.getTranslation(key);
      if (!text || text === key) return;

      // Безопасная работа с jQuery и Bootstrap
      try {
        if (typeof jQuery !== 'undefined' && typeof jQuery(el).tooltip === 'function') {
          if (jQuery(el).data('bs.tooltip')) {
            jQuery(el).attr('data-original-title', text).tooltip('fixTitle');
          } else {
            jQuery(el).attr('title', text);
            jQuery(el).tooltip('dispose');
            jQuery(el).tooltip({ trigger: 'hover', title: text });
          }
        }
      } catch (err) {
        this.#logError(`Tooltip update failed for #${id}`, err);
      }

      // Обновление aria-describedby
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
}

// Создаем глобальный инстанс для работы приложения
const i18nManager = new I18nManager();

// Обратная совместимость для существующего кода
if (typeof window !== 'undefined') {
  window.i18n = i18nManager;
  // Оставляем глобальные функции, чтобы не сломать другие скрипты, которые их вызывают
  window.setLanguage = (lang) => i18nManager.setLanguage(lang);
  window.getTranslation = (key) => i18nManager.getTranslation(key);
  // Заменяем старую функцию на надежный метод класса (хотя Observer сделает все сам)
  window.translateDynamicContent = (el) => i18nManager.translateNode(el);
}

document.addEventListener('DOMContentLoaded', () => {
  i18nManager.init();
});