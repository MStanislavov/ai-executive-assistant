import { useNavigate, useParams } from "react-router-dom"
import { Play, FileText, Briefcase, FileEdit, ChevronDown } from "lucide-react"
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useProfiles } from "@/contexts/ProfileContext"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

const profileNav = [
  { label: "Runs", suffix: "runs", icon: Play },
  { label: "Results", suffix: "results", icon: Briefcase },
  { label: "Cover Letters", suffix: "cover-letters", icon: FileEdit },
]

export function ProfileSwitcher() {
  const { profiles } = useProfiles()
  const { profileId } = useParams()
  const navigate = useNavigate()

  const active = profiles.find((p) => p.id === profileId)

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground px-3 mb-2 uppercase tracking-wider">
        Profile
      </p>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-full justify-between text-left font-normal">
            <span className="truncate">{active?.name ?? "Select profile..."}</span>
            <ChevronDown className="h-4 w-4 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {profiles.map((p) => (
            <DropdownMenuItem key={p.id} onClick={() => navigate(`/profiles/${p.id}`)}>
              <FileText className="h-4 w-4 mr-2" />
              {p.name}
            </DropdownMenuItem>
          ))}
          {profiles.length === 0 && (
            <DropdownMenuItem disabled>No profiles yet</DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {profileId && (
        <nav className="mt-3 flex flex-col gap-1">
          <NavLink
            to={`/profiles/${profileId}`}
            end
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent",
              )
            }
          >
            <FileText className="h-4 w-4" />
            Profile Details
          </NavLink>
          {profileNav.map((item) => (
            <NavLink
              key={item.suffix}
              to={`/profiles/${profileId}/${item.suffix}`}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
