/**
 * useTheme.js — Dark/Light theme composable with localStorage persistence
 */
import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'vtd-theme'

// Read saved theme or default to 'dark'
const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
const isDark = ref(saved ? saved === 'dark' : true)

function applyTheme() {
    const root = document.documentElement
    if (isDark.value) {
        root.setAttribute('data-theme', 'dark')
    } else {
        root.setAttribute('data-theme', 'light')
    }
    localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
}

// Apply on load
if (typeof document !== 'undefined') {
    applyTheme()
}

watchEffect(() => {
    applyTheme()
})

export function useTheme() {
    function toggleTheme() {
        isDark.value = !isDark.value
    }

    function setTheme(dark) {
        isDark.value = dark
    }

    return {
        isDark,
        toggleTheme,
        setTheme,
    }
}
