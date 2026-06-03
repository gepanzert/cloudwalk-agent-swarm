import { Badge } from "@/components/ui/badge"
import { AgentType, SentimentType } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Brain, Headphones, ArrowRightLeft, ShieldAlert } from "lucide-react"

const agentConfig: Record<AgentType, { label: string; className: string; icon: React.ElementType }> = {
  knowledge: {
    label: "Knowledge Agent",
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    icon: Brain
  },
  support: {
    label: "Support Agent",
    className: "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20",
    icon: Headphones
  },
  handoff: {
    label: "Handoff Agent",
    className: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
    icon: ArrowRightLeft
  },
  guardrail: {
    label: "Guardrail",
    className: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    icon: ShieldAlert
  }
}

const sentimentConfig: Record<NonNullable<SentimentType>, { label: string; className: string }> = {
  urgent: {
    label: "Urgente",
    className: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20"
  },
  critical: {
    label: "Crítico",
    className: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 animate-pulse"
  }
}

interface AgentBadgeProps {
  agentType: AgentType
}

export function AgentBadge({ agentType }: AgentBadgeProps) {
  const config = agentConfig[agentType]
  const Icon = config.icon

  return (
    <Badge variant="outline" className={cn("gap-1 text-xs font-medium", config.className)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

interface SentimentBadgeProps {
  sentiment: NonNullable<SentimentType>
}

export function SentimentBadge({ sentiment }: SentimentBadgeProps) {
  const config = sentimentConfig[sentiment]

  return (
    <Badge variant="outline" className={cn("text-xs font-medium", config.className)}>
      {config.label}
    </Badge>
  )
}
