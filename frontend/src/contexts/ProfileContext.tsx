import { createContext, useContext, useEffect, useState, useCallback } from "react"
import { listProfiles } from "@/api/profiles"
import type { Profile } from "@/api/types"

interface ProfileContextValue {
  profiles: Profile[]
  loading: boolean
  refresh: () => Promise<void>
}

const ProfileContext = createContext<ProfileContextValue>({
  profiles: [],
  loading: true,
  refresh: async () => {},
})

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const p = await listProfiles()
      setProfiles(p)
    } catch {
      // keep existing profiles on error
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <ProfileContext.Provider value={{ profiles, loading, refresh }}>
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfiles() {
  return useContext(ProfileContext)
}
