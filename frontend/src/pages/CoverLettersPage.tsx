import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { FileEdit, Plus, Loader2, ExternalLink, Trash2, Copy } from "lucide-react"
import { listCoverLetters, createCoverLetter, deleteCoverLetter } from "@/api/coverLetters"
import { listJobs } from "@/api/results"
import type { CoverLetter, JobOpportunity } from "@/api/types"
import { useSSE } from "@/hooks/useSSE"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { EmptyState } from "@/components/shared/EmptyState"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "sonner"

export default function CoverLettersPage() {
  const { profileId } = useParams()
  const [letters, setLetters] = useState<CoverLetter[]>([])
  const [jobs, setJobs] = useState<JobOpportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<string>("")
  const [jdText, setJdText] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [generatingRunId, setGeneratingRunId] = useState<string | undefined>(undefined)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [filterJob, setFilterJob] = useState<string>("all")

  const { done: sseDone } = useSSE(profileId, generatingRunId)

  function load() {
    if (!profileId) return
    Promise.all([listCoverLetters(profileId), listJobs(profileId)])
      .then(([cl, j]) => {
        setLetters(cl)
        setJobs(j)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [profileId])

  // Reload when SSE signals generation complete
  useEffect(() => {
    if (sseDone && generatingRunId) {
      setGeneratingRunId(undefined)
      load()
    }
  }, [sseDone, generatingRunId])

  // Polling fallback: if any letter is still generating, poll every 3s
  // (SSE may miss events if the run finishes before the client connects)
  useEffect(() => {
    const hasGenerating = letters.some((cl) => cl.content === "")
    if (!hasGenerating) return
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [letters])

  async function handleGenerate() {
    if (!profileId) return
    const cl = await createCoverLetter(profileId, {
      job_opportunity_id: selectedJob || undefined,
      jd_text: jdText || undefined,
    })
    toast.success("Cover letter generation started")
    setDialogOpen(false)
    setSelectedJob("")
    setJdText("")
    if (cl.run_id) {
      setGeneratingRunId(cl.run_id)
    }
    load()
  }

  function handleCopy(content: string) {
    navigator.clipboard.writeText(content)
    toast.success("Copied to clipboard")
  }

  async function handleDelete(letterId: string) {
    if (!profileId) return
    await deleteCoverLetter(profileId, letterId)
    toast.success("Cover letter deleted")
    if (expanded === letterId) setExpanded(null)
    setDeleteTarget(null)
    load()
  }

  async function handleBulkDelete() {
    if (!profileId) return
    await Promise.all([...selected].map((id) => deleteCoverLetter(profileId, id)))
    toast.success(`Deleted ${selected.size} cover letter${selected.size > 1 ? "s" : ""}`)
    setSelected(new Set())
    setBulkDeleteOpen(false)
    setExpanded(null)
    load()
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Build unique job options from cover letters
  const jobOptions = Array.from(
    new Map(
      letters
        .filter((cl) => cl.job_opportunity_id)
        .map((cl) => [
          cl.job_opportunity_id!,
          `${cl.job_title ?? "Unknown job"}${cl.job_company ? ` at ${cl.job_company}` : ""}`,
        ])
    ).entries()
  )

  const filtered = letters.filter((cl) => {
    if (filterJob === "all") return true
    if (filterJob === "none") return !cl.job_opportunity_id
    return cl.job_opportunity_id === filterJob
  })

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Cover Letters"
        description="Generated cover letters"
        actions={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" /> Generate
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col">
              <DialogHeader>
                <DialogTitle>Generate Cover Letter</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2 overflow-y-auto flex-1 min-h-0">
                <div>
                  <Label className="mb-2 block">Select Job</Label>
                  <Select value={selectedJob} onValueChange={setSelectedJob}>
                    <SelectTrigger className="truncate">
                      <SelectValue placeholder="Choose a job..." />
                    </SelectTrigger>
                    <SelectContent>
                      {jobs.map((j) => (
                        <SelectItem key={j.id} value={j.id}>
                          {j.title}{j.company ? ` at ${j.company}` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="mb-2 block">Or paste job description (optional)</Label>
                  <Textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Paste the job description here..."
                    className="max-h-[40vh] overflow-y-auto"
                    rows={6}
                  />
                </div>
                <Button onClick={handleGenerate} className="w-full">
                  Generate
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        }
      />

      {letters.length > 0 && (
        <div className="flex items-center gap-3 mb-4">
          <Select value={filterJob} onValueChange={setFilterJob}>
            <SelectTrigger className="w-72 truncate">
              <SelectValue placeholder="Filter by job..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All jobs</SelectItem>
              {jobOptions.map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
              {letters.some((cl) => !cl.job_opportunity_id) && (
                <SelectItem value="none">No job linked</SelectItem>
              )}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-2">
            <Checkbox
              checked={filtered.length > 0 && filtered.every((cl) => selected.has(cl.id))}
              onCheckedChange={(checked) => {
                if (checked) {
                  setSelected(new Set(filtered.map((cl) => cl.id)))
                } else {
                  setSelected(new Set())
                }
              }}
            />
            <span className="text-sm text-muted-foreground">Select all</span>
          </div>
          {selected.size > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setBulkDeleteOpen(true)}
            >
              <Trash2 className="h-4 w-4 mr-1" /> Delete ({selected.size})
            </Button>
          )}
        </div>
      )}

      {letters.length === 0 ? (
        <EmptyState
          icon={<FileEdit className="h-10 w-10" />}
          title="No cover letters yet"
          description="Generate a cover letter from a job or a raw job description."
          actionLabel="Generate"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          {filtered.map((cl) => {
            const isGenerating = cl.content === ""
            return (
              <Card
                key={cl.id}
                className={isGenerating ? "" : "cursor-pointer"}
                onClick={isGenerating ? undefined : () => setExpanded(expanded === cl.id ? null : cl.id)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        checked={selected.has(cl.id)}
                        onCheckedChange={() => toggleSelect(cl.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <CardTitle className="text-base">
                        Cover Letter, {new Date(cl.created_at).toLocaleDateString()}
                      </CardTitle>
                    </div>
                    <div className="flex gap-1">
                      {isGenerating && (
                        <Badge variant="outline" className="text-xs flex items-center gap-1">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Generating...
                        </Badge>
                      )}
                      {cl.job_title && (
                        <Badge variant="secondary" className="text-xs">
                          {cl.job_title}{cl.job_company ? ` at ${cl.job_company}` : ""}
                        </Badge>
                      )}
                      {cl.job_url && (
                        <a
                          href={cl.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                        >
                          View posting <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                      {cl.content && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-foreground"
                          onClick={(e) => { e.stopPropagation(); handleCopy(cl.content) }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        onClick={(e) => { e.stopPropagation(); setDeleteTarget(cl.id) }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                {isGenerating ? (
                  <CardContent>
                    <p className="text-sm text-muted-foreground">Cover letter is being generated. This may take a moment.</p>
                  </CardContent>
                ) : expanded === cl.id ? (
                  <CardContent>
                    <div className="bg-muted rounded-md p-4 text-sm whitespace-pre-wrap">
                      {cl.content}
                    </div>
                  </CardContent>
                ) : (
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2">{cl.content}</p>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}

      <AlertDialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {selected.size} cover letter{selected.size > 1 ? "s" : ""}?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The selected cover letters will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete cover letter?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The cover letter will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteTarget && handleDelete(deleteTarget)}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
