import { useState, useEffect } from "react"
import { NavLink } from "react-router-dom"
import { LayoutDashboard, Shield, Moon, Sun, type LucideIcon } from "lucide-react"
import { useTheme } from "next-themes"
import { cn } from "@/lib/utils"
import { ProfileSwitcher } from "./ProfileSwitcher"

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  end?: boolean
}

const globalNav: NavItem[] = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
  { label: "Policies", to: "/policies", icon: Shield },
]

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        )
      }
    >
      <item.icon className="h-4 w-4" />
      {item.label}
    </NavLink>
  )
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  if (!mounted) return null

  const isDark = resolvedTheme === "dark"

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors w-full"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      {isDark ? "Light Mode" : "Dark Mode"}
    </button>
  )
}

/** Shared navigation content used by both desktop sidebar and mobile sheet. */
export function SidebarContent() {
  return (
    <div className="flex flex-col h-full bg-sidebar p-4">
      <div className="mb-6">
        <h2 className="text-lg font-bold tracking-tight px-3 text-primary">AI Assistant</h2>
        <p className="text-xs text-muted-foreground px-3">Executive Network</p>
      </div>

      <nav className="flex flex-col gap-1">
        {globalNav.map((item) => (
          <SidebarLink key={item.to} item={item} />
        ))}
      </nav>

      <div className="mt-6">
        <ProfileSwitcher />
      </div>

      <div className="mt-auto pt-4 border-t border-sidebar-border">
        <ThemeToggle />
      </div>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="hidden lg:flex lg:flex-col lg:w-64 border-r bg-sidebar min-h-screen">
      <SidebarContent />
    </aside>
  )
}
