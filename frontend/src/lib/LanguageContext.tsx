'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

type Language = 'en' | 'ar' | 'de';
type Direction = 'ltr' | 'rtl';

interface Translations {
    [key: string]: {
        en: string;
        ar: string;
        de: string;
    };
}

/**
 * Dictionary of all static UI text strings for supported languages.
 * Add new keys here to support more UI elements.
 */
const translations: Translations = {
    // Sidebar
    'new_chat': { en: 'New Chat', ar: 'محادثة جديدة', de: 'Neuer Chat' },
    'search_placeholder': { en: 'Search conversations...', ar: 'بحث في المحادثات...', de: 'Gespräche durchsuchen...' },
    'no_conversations': { en: 'No conversations yet', ar: 'لا توجد محادثات حتى الآن', de: 'Noch keine Gespräche' },
    'start_new_chat': { en: 'Start a new chat to begin', ar: 'ابدأ محادثة جديدة للبدء', de: 'Starten Sie einen neuen Chat' },
    'today': { en: 'Today', ar: 'اليوم', de: 'Heute' },
    'yesterday': { en: 'Yesterday', ar: 'أمس', de: 'Gestern' },
    'days_ago': { en: 'days ago', ar: 'أيام مضت', de: 'Tage vor' },

    // Chat Interface
    'welcome_title': { en: 'Kaso AI Assistant', ar: 'مساعد كاسو الذكي', de: 'Kaso KI-Assistent' },
    'welcome_desc': {
        en: 'Ask me anything about Kaso - company information, services, funding, team, and more.',
        ar: 'اسألني أي شيء عن كاسو فودتك - معلومات الشركة، الخدمات، التمويل، الفريق، والمزيد.',
        de: 'Fragen Sie mich alles über Kaso - Unternehmensinformationen, Dienstleistungen, Finanzierung, Team und mehr.'
    },
    'input_placeholder': { en: 'Ask about Kaso...', ar: 'اسأل عن كاسو...', de: 'Fragen Sie nach Kaso...' },
    'error_msg': { en: 'Sorry, an error occurred. Please try again.', ar: 'عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.', de: 'Entschuldigung, ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.' },
    'sources': { en: 'Sources:', ar: 'المصادر:', de: 'Quellen:' },

    // Settings
    'settings': { en: 'Settings', ar: 'الإعدادات', de: 'Einstellungen' },
    'theme': { en: 'Theme', ar: 'المظهر', de: 'Thema' },
    'language': { en: 'Language', ar: 'اللغة', de: 'Sprache' },
    'dark_mode': { en: 'Dark Mode', ar: 'الوضع الداكن', de: 'Dunkelmodus' },
    'light_mode': { en: 'Light Mode', ar: 'الوضع الفاتح', de: 'Heller Modus' },

    // Examples
    'ex_what_is': { en: 'What is Kaso?', ar: 'ما هي كاسو؟', de: 'Was ist Kaso?' },
    'ex_who_founded': { en: 'Who founded Kaso?', ar: 'من أسس كاسو؟', de: 'Wer hat Kaso gegründet?' },
    'ex_services': { en: 'What are Kaso services?', ar: 'ما هي خدمات كاسو؟', de: 'Was sind Kaso-Dienstleistungen?' },
    'ex_funding': { en: 'How much funding has Kaso raised?', ar: 'كم حجم التمويل الذي جمعته كاسو؟', de: 'Wie viel Geld hat Kaso gesammelt?' },
};

interface LanguageContextType {
    language: Language;
    direction: Direction;
    setLanguage: (lang: Language) => void;
    t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

/**
 * LanguageProvider Component
 * 
 * Manages global language state, persistent storage, and RTL/LTR directionality.
 * Wrapping the app in this provider ensures all components have access to:
 * - Current language (en/ar/de)
 * - Text direction
 * - Translation helper function t()
 */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguageState] = useState<Language>('en');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        const savedLang = localStorage.getItem('language') as Language;
    
        if (savedLang && ['en', 'ar', 'de'].includes(savedLang)) {
            setLanguageState(savedLang);
        } else {
            // Detect browser language and default to English if unsupported
            const browserLang = navigator.language.split('-')[0].toLowerCase();
            if (browserLang === 'ar') {
                setLanguageState('ar');
            } else if (browserLang === 'de') {
                setLanguageState('de');
            } else {
                setLanguageState('en');
            }
        }
    }, []);

    const setLanguage = (lang: Language) => {
        setLanguageState(lang);
        localStorage.setItem('language', lang);
        // Update HTML lang/dir to support RTL/LTR and accessibility
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    };

    useEffect(() => {
        if (mounted) {
            // Keep document attributes in sync when language changes
            document.documentElement.lang = language;
            document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
        }
    }, [language, mounted]);

    const t = (key: string) => {
        return translations[key]?.[language] || key;
    };

    return (
        <LanguageContext.Provider value={{ language, direction: language === 'ar' ? 'rtl' : 'ltr', setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (context === undefined) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return context;
}
