import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { FileEdit, Plus, Loader2 } from "lucide-react"
import { listCoverLetters, createCoverLetter } from "@/api/coverLetters"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Generate Cover Letter</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div>
                  <Label className="mb-2 block">Select Job (optional)</Label>
                  <Select value={selectedJob} onValueChange={setSelectedJob}>
                    <SelectTrigger>
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
                  <Label className="mb-2 block">Or paste job description</Label>
                  <Textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Paste the job description here..."
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
          {letters.map((cl) => {
            const isGenerating = cl.content === ""
            return (
              <Card
                key={cl.id}
                className={isGenerating ? "" : "cursor-pointer"}
                onClick={isGenerating ? undefined : () => setExpanded(expanded === cl.id ? null : cl.id)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      Cover Letter, {new Date(cl.created_at).toLocaleDateString()}
                    </CardTitle>
                    <div className="flex gap-1">
                      {isGenerating && (
                        <Badge variant="outline" className="text-xs flex items-center gap-1">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Generating...
                        </Badge>
                      )}
                      {cl.job_opportunity_id && (
                        <Badge variant="secondary" className="text-xs">
                          Job linked
                        </Badge>
                      )}
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
    </div>
  )
}
