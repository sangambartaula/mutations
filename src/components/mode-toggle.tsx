"use client"

import * as React from "react"
import { Laptop, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

export function ModeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div
      className="inline-flex items-center gap-1 rounded-xl border border-neutral-200 bg-white p-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
      role="group"
      aria-label="Theme mode"
    >
      {[
        { value: "system", label: "System", icon: Laptop },
        { value: "dark", label: "Dark", icon: Moon },
        { value: "light", label: "Light", icon: Sun },
      ].map((option) => {
        const Icon = option.icon
        const isActive = mounted ? theme === option.value : option.value === "system"
        const isSystemAndResolved = mounted && option.value === "system"
          ? ` (${resolvedTheme === "dark" ? "Dark" : "Light"})`
          : ""

        return (
          <button
            key={option.value}
            onClick={() => setTheme(option.value)}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 font-medium transition-colors ${
              isActive
                ? "bg-emerald-500 text-white"
                : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            }`}
            aria-pressed={isActive}
            title={`Set theme: ${option.label}${isSystemAndResolved}`}
            type="button"
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}
