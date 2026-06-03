export type AgentType = 'knowledge' | 'support' | 'handoff' | 'guardrail'
export type SentimentType = 'urgent' | 'critical' | null

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  agentType?: AgentType
  sentiment?: SentimentType
}

export interface Conversation {
  threadId: string
  messages: Message[]
  isLoading: boolean
}

export interface ExampleQuery {
  text: string
  userId?: string
}
