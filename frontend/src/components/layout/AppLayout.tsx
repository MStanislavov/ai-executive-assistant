import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { MobileNav } from "./MobileNav"
import { Toaster } from "@/components/ui/sonner"
import { ProfileProvider } from "@/contexts/ProfileContext"

export function AppLayout() {
  return (
    <ProfileProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <MobileNav />
          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </div>
        <Toaster />
      </div>
    </ProfileProvider>
  )
}
