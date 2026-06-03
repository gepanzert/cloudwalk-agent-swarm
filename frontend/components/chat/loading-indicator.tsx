import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bot } from "lucide-react"

export function LoadingIndicator() {
  return (
    <div className="flex gap-3 px-4">
      <Avatar className="h-8 w-8 shrink-0 bg-primary text-primary-foreground">
        <AvatarFallback className="bg-primary text-primary-foreground">
          <Bot className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex flex-col gap-1.5 items-start">
        <div className="bg-card text-card-foreground border border-border rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" />
            </div>
            <span className="text-sm text-muted-foreground">Agente pensando...</span>
          </div>
        </div>
      </div>
    </div>
  )
}
